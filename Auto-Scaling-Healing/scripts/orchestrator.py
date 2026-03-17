import subprocess
import json
import time
from prometheus_client import start_http_server, Gauge

# --- 1. PROMETHEUS METRICS ---
HEALTHY_INSTANCES = Gauge('podflow_healthy_containers', 'Number of healthy pods')
UNHEALTHY_INSTANCES = Gauge('podflow_unhealthy_containers', 'Number of unhealthy pods')
CPU_USAGE_GAUGE = Gauge('podflow_cpu_usage', 'Average CPU usage of the cluster')
DESIRED_STATE_GAUGE = Gauge('podflow_desired_count', 'Target number of containers')

# --- 2. UTILITY FUNCTIONS ---

def get_average_cpu(label):
    """Safely calculates CPU usage without crashing during transitions."""
    try:
        check = subprocess.run(["podman", "ps", "-q", "--filter", f"label={label}"], capture_output=True, text=True)
        if not check.stdout.strip():
            return 0.0

        cmd = ["podman", "stats", "--no-stream", "--format", "json", "--filter", f"label={label}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Podman stats can return Multiple JSON objects; we wrap them into a list
        raw_output = result.stdout.strip().replace('\n', ',')
        if not raw_output: return 0.0
        
        stats = json.loads(f"[{raw_output}]")
        cpu_values = [float(s['CPUPerc'].replace('%', '')) for s in stats if 'CPUPerc' in s]
        
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
        CPU_USAGE_GAUGE.set(avg_cpu)
        return avg_cpu
    except Exception:
        return 0.0

def repair_and_scale(label, image, desired_count):
    """The 'Brain' of the system: Fixes broken pods and adjusts cluster size."""
    print(f"\n--- Reconciliation Cycle | Target: {desired_count} ---")

    # A. ANALYZE STATE
    cmd = ["podman", "ps", "-a", "--filter", f"label={label}", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    containers = []
    if result.stdout.strip():
        try:
            containers = json.loads(result.stdout)
        except json.JSONDecodeError:
            print(" [!] Warning: Could not parse Podman JSON output.")

    unhealthy_count = 0
    
    # B. AUTO-HEALING (With Safety Checks)
    for c in containers:
        container_id = c.get("ID")
        status = c.get("Status", "").lower()
        
        # CRITICAL FIX: If ID is None or empty, skip this entry to avoid TypeError
        if not container_id:
            continue

        if "unhealthy" in status:
            short_id = str(container_id)[:12]
            print(f" [!] Healing: Removing unhealthy container {short_id}")
            subprocess.run(["podman", "rm", "-f", container_id])
            unhealthy_count += 1
        elif "exited" in status or "dead" in status:
            short_id = str(container_id)[:12]
            print(f" [!] Cleanup: Removing dead container {short_id}")
            subprocess.run(["podman", "rm", "-f", container_id])

    # C. SYNC COUNT
    active_cmd = ["podman", "ps", "--filter", f"label={label}", "-q"]
    active_result = subprocess.run(active_cmd, capture_output=True, text=True)
    active_ids = active_result.stdout.split()
    current_count = len(active_ids)
    
    HEALTHY_INSTANCES.set(current_count)
    UNHEALTHY_INSTANCES.set(unhealthy_count)
    DESIRED_STATE_GAUGE.set(desired_count)

    print(f" [i] Current Active: {current_count} | Unhealthy Found: {unhealthy_count}")

    # D. ACTION: SCALE UP
    if current_count < desired_count:
        diff = desired_count - current_count
        print(f" [+] Scaling UP: Adding {diff} instances.")
        for _ in range(diff):
            subprocess.run([
                "podman", "run", "-d",
                "--label", label,
                "--network", "podflow-net",
                "--health-cmd", "/usr/src/app/healthcheck.sh",
                "--health-interval", "10s",
                "--health-retries", "3",
                "--health-start-period", "20s",
                image
            ])

    # E. ACTION: SCALE DOWN
    elif current_count > desired_count:
        diff = current_count - desired_count
        print(f" [-] Scaling DOWN: Removing {diff} extra instances.")
        for _ in range(diff):
            oldest_id_cmd = ["podman", "ps", "-q", "--filter", f"label={label}", "--sort", "created"]
            oldest_result = subprocess.run(oldest_id_cmd, capture_output=True, text=True)
            if oldest_result.stdout.strip():
                oldest_id = oldest_result.stdout.split()[0]
                subprocess.run(["podman", "rm", "-f", oldest_id])

# --- 3. MAIN CONTROL LOOP ---

def main():
    try:
        start_http_server(8000)
        print("✓ Prometheus Metrics Exporter started on port 8000")
    except Exception as e:
        print(f" [!] Metrics Port Error: {e}")

    APP_LABEL = "app=podflow-node"
    IMAGE = "localhost/podflow-node:latest"
    DESIRED_COUNT = 3 

    while True:
        avg_cpu = get_average_cpu(APP_LABEL)
        
        # Simple Scaling Thresholds
        if avg_cpu > 70.0 and DESIRED_COUNT < 10:
            DESIRED_COUNT += 1
            print(f"!!! High Load Detected ({avg_cpu}%). Scaling Up.")
        elif avg_cpu < 20.0 and DESIRED_COUNT > 3:
            DESIRED_COUNT -= 1
            print(f"--- System Idle ({avg_cpu}%). Scaling Down.")

        repair_and_scale(APP_LABEL, IMAGE, DESIRED_COUNT)
        time.sleep(15)

if __name__ == "__main__":
    main()
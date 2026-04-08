#!/usr/bin/env python3

import subprocess
import json
import time
from prometheus_client import start_http_server, Gauge

# =========================
# CONFIG
# =========================

PROJECT_PREFIX = "podflow-project"   # your folder name in lowercase
SERVICE_NAME   = "api-gateway"       # the service the orchestrator manages
IMAGE          = f"localhost/{PROJECT_PREFIX}_{SERVICE_NAME}"
NETWORK        = f"{PROJECT_PREFIX}_public_net"

# The label we put on every container we launch so we can find them later
LABEL_KEY   = "managed-by"
LABEL_VALUE = "podflow-orchestrator"
LABEL       = f"{LABEL_KEY}={LABEL_VALUE}"

DESIRED_COUNT   = 3     # starting target replica count
MIN_DESIRED     = 3
MAX_DESIRED     = 10
CHECK_INTERVAL  = 15    # seconds between reconciliation cycles

# =========================
# PROMETHEUS METRICS
# =========================

HEALTHY_INSTANCES   = Gauge('podflow_healthy_containers',  'Number of healthy containers')
UNHEALTHY_INSTANCES = Gauge('podflow_unhealthy_containers','Number of unhealthy containers')
CPU_USAGE_GAUGE     = Gauge('podflow_cpu_usage',           'Average CPU usage of the cluster')
DESIRED_STATE_GAUGE = Gauge('podflow_desired_count',       'Target number of containers')

# =========================
# UTILITY FUNCTIONS
# =========================

def get_average_cpu():
    """
    Get average CPU across all containers we manage (identified by label).
    Returns 0.0 safely if nothing is running or stats are unavailable.
    """
    try:
        # First check if any containers with our label are running
        check = subprocess.run(
            ["podman", "ps", "-q", "--filter", f"label={LABEL}"],
            capture_output=True, text=True
        )
        if not check.stdout.strip():
            return 0.0

        result = subprocess.run(
            ["podman", "stats", "--no-stream", "--format", "json",
             "--filter", f"label={LABEL}"],
            capture_output=True, text=True
        )
        if not result.stdout.strip():
            return 0.0

        stats = json.loads(result.stdout)
        cpu_values = []
        for s in stats:
            raw = s.get("cpu_percent", "0%")
            try:
                cpu_values.append(float(str(raw).replace("%", "").strip()))
            except ValueError:
                pass

        avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0.0
        CPU_USAGE_GAUGE.set(avg)
        return avg

    except Exception as e:
        print(f"   [!] CPU stats error: {e}")
        return 0.0

def reconcile(desired_count):
    """
    The core control loop — compares actual state to desired state and acts.
    Step A: Inspect all containers with our label (running AND stopped).
    Step B: Remove unhealthy/dead ones (auto-healing).
    Step C: Count what's actually running now.
    Step D: Launch or remove containers to match desired_count.
    """
    print(f"\n--- Reconciliation | Target: {desired_count} ---", flush=True)

    # ── A: Get all containers with our label ──────────────────────────────
    result = subprocess.run(
        ["podman", "ps", "-a", "--filter", f"label={LABEL}", "--format", "json"],
        capture_output=True, text=True
    )

    containers = []
    if result.stdout.strip():
        try:
            containers = json.loads(result.stdout)
        except json.JSONDecodeError:
            print("   [!] Could not parse Podman JSON — skipping cycle")
            return

    # ── B: Auto-heal — remove unhealthy and exited containers ─────────────
    unhealthy_count = 0
    for c in containers:
        cid    = c.get("Id") or c.get("ID", "")
        status = c.get("Status", "").lower()

        if not cid:
            continue

        short = cid[:12]

        if "unhealthy" in status:
            print(f"   [!] Healing unhealthy container {short}")
            subprocess.run(["podman", "rm", "-f", cid], capture_output=True)
            unhealthy_count += 1

        elif "exited" in status or "dead" in status:
            print(f"   [!] Removing dead container {short}")
            subprocess.run(["podman", "rm", "-f", cid], capture_output=True)

    # ── C: Count currently running containers with our label ──────────────
    active_result = subprocess.run(
        ["podman", "ps", "-q", "--filter", f"label={LABEL}"],
        capture_output=True, text=True
    )
    current_count = len([
        x for x in active_result.stdout.strip().split("\n")
        if x.strip()
    ]) if active_result.stdout.strip() else 0

    HEALTHY_INSTANCES.set(current_count)
    UNHEALTHY_INSTANCES.set(unhealthy_count)
    DESIRED_STATE_GAUGE.set(desired_count)

    print(f"   Running: {current_count} | Unhealthy removed: {unhealthy_count} | Target: {desired_count}")

    # ── D: Scale UP ───────────────────────────────────────────────────────
    if current_count < desired_count:
        to_add = desired_count - current_count
        print(f"   [+] Scaling UP: adding {to_add} instance(s)")
        for _ in range(to_add):
            result = subprocess.run([
                "podman", "run", "-d",
                "--label", LABEL,           # tag so we can find it next cycle
                "--network", NETWORK,
                "--health-cmd", "curl -f http://localhost:8080/health || exit 1",
                "--health-interval", "10s",
                "--health-retries", "3",
                "--health-start-period", "20s",
                IMAGE
            ], capture_output=True, text=True)

            if result.returncode == 0:
                print(f"      ✅ New instance started: {result.stdout.strip()[:12]}")
            else:
                print(f"      ❌ Failed to start instance: {result.stderr.strip()}")

    # ── E: Scale DOWN ─────────────────────────────────────────────────────
    elif current_count > desired_count:
        to_remove = current_count - desired_count
        print(f"   [-] Scaling DOWN: removing {to_remove} instance(s)")

        # Remove oldest instances first (sort by creation time)
        oldest_result = subprocess.run(
            ["podman", "ps", "-q",
             "--filter", f"label={LABEL}",
             "--sort", "created"],
            capture_output=True, text=True
        )
        ids = [x for x in oldest_result.stdout.strip().split("\n") if x.strip()]

        for cid in ids[:to_remove]:
            result = subprocess.run(
                ["podman", "rm", "-f", cid],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"      ✅ Removed {cid[:12]}")
            else:
                print(f"      ❌ Failed to remove {cid[:12]}: {result.stderr.strip()}")
    else:
        print("   [=] Cluster is at desired state — no action needed")

# =========================
# MAIN CONTROL LOOP
# =========================

def main():
    global DESIRED_COUNT

    # Start Prometheus metrics server on port 8000
    try:
        start_http_server(8000)
        print("✅ Prometheus metrics exporter started on port 8000", flush=True)
    except Exception as e:
        print(f"   [!] Could not start metrics server: {e}", flush=True)

    print(f"🧠 PodFlow Orchestrator started", flush=True)
    print(f"   Image:   {IMAGE}", flush=True)
    print(f"   Network: {NETWORK}", flush=True)
    print(f"   Label:   {LABEL}", flush=True)
    print(f"   Target:  {DESIRED_COUNT} replicas", flush=True)
    print("=" * 60, flush=True)

    while True:
        avg_cpu = get_average_cpu()

        # Adjust desired count based on load
        if avg_cpu > 70.0 and DESIRED_COUNT < MAX_DESIRED:
            DESIRED_COUNT += 1
            print(f"!!! High load ({avg_cpu:.1f}%) — increasing target to {DESIRED_COUNT}")

        elif avg_cpu < 20.0 and DESIRED_COUNT > MIN_DESIRED:
            DESIRED_COUNT -= 1
            print(f"--- Low load ({avg_cpu:.1f}%) — decreasing target to {DESIRED_COUNT}")

        reconcile(DESIRED_COUNT)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
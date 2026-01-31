import subprocess
import time

CPU_THRESHOLD = 70
MAX_REPLICAS = 3
MIN_REPLICAS = 1

def get_cpu(container):
    stats = subprocess.check_output(
        ["podman", "stats", "--no-stream", "--format", "{{.CPUPerc}}", container]
    )
    return float(stats.decode().strip().replace("%", ""))

while True:
    cpu = get_cpu("backend")

    if cpu > CPU_THRESHOLD:
        print(f"[SCALER] High CPU {cpu}% → scale up (manual logic here)")
    else:
        print(f"[SCALER] CPU {cpu}% → stable")

    time.sleep(10)

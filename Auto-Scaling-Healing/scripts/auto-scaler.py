#!/usr/bin/env python3

import subprocess
import json
import time
from datetime import datetime

# =========================
# CONFIG
# =========================

APP_IMAGE = "podflow-app:1.2"
BASE_NAME = "podflow-demo"
NETWORK = "bridge"

MIN_REPLICAS = 1
MAX_REPLICAS = 5

SCALE_UP_CPU = 70.0
SCALE_DOWN_CPU = 30.0

CHECK_INTERVAL = 10       # seconds
COOLDOWN = 30             # seconds

last_scale_time = 0

# =========================
# UTILS
# =========================

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_containers():
    result = subprocess.run(
        ["podman", "ps", "--format", "json"],
        capture_output=True,
        text=True
    )
    containers = json.loads(result.stdout)
    return [
        c["Names"][0]
        for c in containers
        if c["Names"][0].startswith(BASE_NAME)
    ]

def get_cpu_usage(containers):
    result = subprocess.run(
        ["podman", "stats", "--no-stream", "--format", "json"],
        capture_output=True,
        text=True
    )

    stats = json.loads(result.stdout)
    cpu_values = []

    for stat in stats:
        name = stat.get("name")   # 👈 Podman uses lowercase "name"

        if name in containers:
            cpu_raw = stat.get("cpu_percent", "0%")
            cpu = float(cpu_raw.replace("%", ""))
            cpu_values.append(cpu)

    if not cpu_values:
        return 0.0

    return sum(cpu_values) / len(cpu_values)

def scale_up(current):
    name = f"{BASE_NAME}-{current + 1}"
    log(f"⬆️ Scaling UP → starting {name}")

    subprocess.run([
        "podman", "run", "-d",
        "--name", name,
        "--network", NETWORK,
        APP_IMAGE
    ])

def scale_down(containers):
    name = containers[-1]
    log(f"⬇️ Scaling DOWN → removing {name}")

    subprocess.run(["podman", "rm", "-f", name])

# =========================
# MAIN LOOP
# =========================

log("📈 PodFlow Auto-Scaler started")

while True:
    containers = get_containers()
    replica_count = len(containers)

    cpu = get_cpu_usage(containers)
    log(f"Replicas={replica_count} | Avg CPU={cpu:.2f}%")

    now = time.time()
    if now - last_scale_time < COOLDOWN:
        time.sleep(CHECK_INTERVAL)
        continue

    # Scale UP
    if cpu > SCALE_UP_CPU and replica_count < MAX_REPLICAS:
        scale_up(replica_count)
        last_scale_time = now

    # Scale DOWN
    elif cpu < SCALE_DOWN_CPU and replica_count > MIN_REPLICAS:
        scale_down(containers)
        last_scale_time = now

    time.sleep(CHECK_INTERVAL)

#!/usr/bin/env python3

import subprocess
import json
import time
from datetime import datetime

# =========================
# CONFIG
# =========================

# The service we want to scale — must match your podman-compose service name
SERVICE_NAME = "api-gateway"
PROJECT_PREFIX = "podflow-project"    # your folder name in lowercase

# The image name podman-compose built — found with: podman images
# Format is usually: localhost/<project>_<service>
APP_IMAGE = f"localhost/{PROJECT_PREFIX}_{SERVICE_NAME}"

# The network your compose stack uses — found with: podman network ls
NETWORK = f"{PROJECT_PREFIX}_public_net"

# Scaling limits
MIN_REPLICAS  = 1
MAX_REPLICAS  = 5
SCALE_UP_CPU  = 70.0    # scale up when avg CPU exceeds this %
SCALE_DOWN_CPU = 30.0   # scale down when avg CPU drops below this %

CHECK_INTERVAL = 10     # seconds between checks
COOLDOWN       = 30     # seconds between scale events

last_scale_time = 0

# =========================
# UTILS
# =========================

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

def get_scaled_containers():
    """
    Returns names of all running containers that belong to our scaled service.
    This includes the original compose container AND any extras we launched.
    We identify extras by the naming pattern: <prefix>_<service>_scale_<n>
    """
    result = subprocess.run(
        ["podman", "ps", "--format", "json"],
        capture_output=True, text=True
    )
    if result.returncode != 0 or not result.stdout.strip():
        return []

    try:
        containers = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    # Match both the original compose container and our scaled extras
    base = f"{PROJECT_PREFIX}_{SERVICE_NAME}"
    return [
        c["Names"][0]
        for c in containers
        if c["Names"][0].startswith(base)
    ]

def get_cpu_usage(container_names):
    """
    Get average CPU usage across all containers in the list.
    Podman stats --no-stream returns a snapshot without streaming.
    Returns 0.0 if no data is available.
    """
    if not container_names:
        return 0.0

    result = subprocess.run(
        ["podman", "stats", "--no-stream", "--format", "json"] + container_names,
        capture_output=True, text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        return 0.0

    try:
        stats = json.loads(result.stdout)
    except json.JSONDecodeError:
        return 0.0

    cpu_values = []
    for stat in stats:
        # Podman stats JSON uses lowercase keys: "cpu_percent"
        raw = stat.get("cpu_percent", "0%")
        try:
            cpu_values.append(float(str(raw).replace("%", "").strip()))
        except ValueError:
            pass

    return sum(cpu_values) / len(cpu_values) if cpu_values else 0.0

def scale_up(current_count):
    """
    Launch one extra container instance named <base>_scale_<n>.
    We attach it to the same network as the compose stack.
    """
    new_name = f"{PROJECT_PREFIX}_{SERVICE_NAME}_scale_{current_count}"
    log(f"⬆️  Scaling UP → launching {new_name}")

    result = subprocess.run([
        "podman", "run", "-d",
        "--name", new_name,
        "--network", NETWORK,
        APP_IMAGE
    ], capture_output=True, text=True)

    if result.returncode == 0:
        log(f"   ✅ {new_name} started")
    else:
        log(f"   ❌ Failed: {result.stderr.strip()}")

def scale_down(containers):
    """
    Remove the most recently added extra instance.
    We never remove the original compose container (no '_scale_' in name).
    """
    # Only remove scaled extras, not the original compose container
    extras = [c for c in containers if "_scale_" in c]
    if not extras:
        log("   No extra instances to remove")
        return

    name = extras[-1]
    log(f"⬇️  Scaling DOWN → removing {name}")
    result = subprocess.run(
        ["podman", "rm", "-f", name],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log(f"   ✅ {name} removed")
    else:
        log(f"   ❌ Failed: {result.stderr.strip()}")

# =========================
# MAIN LOOP
# =========================

log("📈 PodFlow Auto-Scaler started")
log(f"   Watching service: {SERVICE_NAME}")
log(f"   Scale UP  at CPU > {SCALE_UP_CPU}%  |  Scale DOWN at CPU < {SCALE_DOWN_CPU}%")
log(f"   Replicas: min={MIN_REPLICAS}  max={MAX_REPLICAS}  cooldown={COOLDOWN}s")
print("-" * 60, flush=True)

while True:
    containers = get_scaled_containers()
    replica_count = len(containers)
    cpu = get_cpu_usage(containers)

    log(f"Replicas={replica_count} | Avg CPU={cpu:.2f}%")

    now = time.time()
    in_cooldown = (now - last_scale_time) < COOLDOWN

    if in_cooldown:
        remaining = int(COOLDOWN - (now - last_scale_time))
        log(f"   ⏳ Cooldown active — {remaining}s remaining")
    elif cpu > SCALE_UP_CPU and replica_count < MAX_REPLICAS:
        scale_up(replica_count)
        last_scale_time = now
    elif cpu < SCALE_DOWN_CPU and replica_count > MIN_REPLICAS:
        scale_down(containers)
        last_scale_time = now
    else:
        log("   → Load normal, no action needed")

    print("-" * 60, flush=True)
    time.sleep(CHECK_INTERVAL)
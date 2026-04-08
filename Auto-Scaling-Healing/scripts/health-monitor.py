#!/usr/bin/env python3

import subprocess
import time
import requests
from datetime import datetime

# =========================
# CONFIGURATION
# =========================

# The prefix podman-compose uses to name containers.
# It is: <folder-name>_<service-name>_1
# Change "podflow-project" below if your folder name is different.
PROJECT_PREFIX = "podflow-project"

# Map each service to its health check URL and port
SERVICES = {
    f"{PROJECT_PREFIX}_api-gateway_1":  "http://localhost:8080/health",
    f"{PROJECT_PREFIX}_backend_1":      "http://localhost:5000/health",
    f"{PROJECT_PREFIX}_honeypot_1":     "http://localhost:8888/health",
}

CHECK_INTERVAL    = 10   # seconds between full check cycles
FAILURE_THRESHOLD = 3    # consecutive failures before restart
REQUEST_TIMEOUT   = 3    # seconds for HTTP timeout

# Track failure counts per container
failure_counts = {name: 0 for name in SERVICES}

# =========================
# UTILITY FUNCTIONS
# =========================

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def is_container_running(name):
    """
    Ask Podman if the container exists and is in 'running' state.
    Returns True only if the container is actively running.
    """
    try:
        result = subprocess.run(
            ["podman", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            text=True
        )
        # If the container doesn't exist, returncode will be non-zero
        if result.returncode != 0:
            return False
        return result.stdout.strip() == "true"
    except Exception as e:
        log(f"    inspect error for {name}: {e}")
        return False

def is_app_healthy(url):
    """
    HTTP GET to the service's /health endpoint.
    Returns True if we get HTTP 200 back within the timeout.
    """
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False

def restart_container(name):
    """
    Use 'podman restart' to restart the named container.
    This is gentler than rm+run — it keeps the same config.
    """
    log(f"    Restarting container: {name}")
    result = subprocess.run(
        ["podman", "restart", name],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        log(f"    ✅ {name} restarted successfully")
    else:
        log(f"    ❌ Failed to restart {name}: {result.stderr.strip()}")

# =========================
# MAIN SELF-HEALING LOOP
# =========================

def monitor():
    log("🟢 PodFlow Self-Healing Monitor Started")
    log(f"   Watching {len(SERVICES)} services every {CHECK_INTERVAL}s")
    log(f"   Restart after {FAILURE_THRESHOLD} consecutive failures")
    print("-" * 60, flush=True)

    while True:
        for container_name, health_url in SERVICES.items():
            # Shorten name for cleaner logs
            short = container_name.split("_")[1]  # e.g. "api-gateway"

            # ── Case 1: Container doesn't exist or isn't running ──────
            if not is_container_running(container_name):
                log(f"❌ [{short}] Container not running")
                restart_container(container_name)
                failure_counts[container_name] = 0
                continue

            # ── Case 2: Container running but HTTP health check fails ──
            if not is_app_healthy(health_url):
                failure_counts[container_name] += 1
                log(f"⚠️  [{short}] Health check failed "
                    f"({failure_counts[container_name]}/{FAILURE_THRESHOLD})")

                if failure_counts[container_name] >= FAILURE_THRESHOLD:
                    log(f"🚨 [{short}] Threshold reached — restarting")
                    restart_container(container_name)
                    failure_counts[container_name] = 0

            # ── Case 3: Everything is fine ────────────────────────────
            else:
                log(f"✅ [{short}] Healthy")
                failure_counts[container_name] = 0

        print("-" * 60, flush=True)
        time.sleep(CHECK_INTERVAL)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    monitor()
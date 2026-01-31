#!/usr/bin/env python3

import subprocess
import time
import requests
from datetime import datetime

# =========================
# CONFIGURATION
# =========================

CONTAINER_NAME = "podflow-demo"
HEALTH_URL = "http://localhost:3000/health"

CHECK_INTERVAL = 10        # seconds between checks
FAILURE_THRESHOLD = 3     # failures before restart
REQUEST_TIMEOUT = 2       # seconds for HTTP timeout

# =========================
# UTILITY FUNCTIONS
# =========================

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def is_container_running(name):
    """
    Check if the Podman container is running.
    """
    try:
        result = subprocess.run(
            ["podman", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True,
            text=True
        )
        return result.stdout.strip() == "true"
    except Exception:
        return False

def is_app_healthy(url):
    """
    Perform HTTP health check on the application.
    """
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        return response.status_code == 200
    except requests.RequestException:
        return False

def restart_container(name):
    """
    Restart the container using Podman.
    """
    subprocess.run(["podman", "restart", name])
    log(f"🔁 Container '{name}' restarted")

# =========================
# MAIN SELF-HEALING LOOP
# =========================

def monitor():
    log("🟢 PodFlow Self-Healing Monitor Started")
    failure_count = 0

    while True:
        # Case 1: Container is not running
        if not is_container_running(CONTAINER_NAME):
            log("❌ Container not running")
            restart_container(CONTAINER_NAME)
            failure_count = 0

        # Case 2: Container running but app unhealthy
        elif not is_app_healthy(HEALTH_URL):
            failure_count += 1
            log(f"⚠️ Health check failed ({failure_count}/{FAILURE_THRESHOLD})")

            if failure_count >= FAILURE_THRESHOLD:
                log("🚨 Failure threshold reached")
                restart_container(CONTAINER_NAME)
                failure_count = 0

        # Case 3: Everything is healthy
        else:
            log("✅ Application healthy")
            failure_count = 0

        time.sleep(CHECK_INTERVAL)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    monitor()

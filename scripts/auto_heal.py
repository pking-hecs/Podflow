import subprocess
import time

CONTAINER = "backend"

while True:
    result = subprocess.run(
        ["podman", "inspect", "-f", "{{.State.Running}}", CONTAINER],
        capture_output=True,
        text=True
    )

    if result.stdout.strip() != "true":
        print(f"[AUTO-HEAL] Backend down. Restarting...")
        subprocess.run(["podman", "restart", CONTAINER])

    time.sleep(5)

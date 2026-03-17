#!/bin/bash

echo "Starting PodFlow Microservices Platform..."

# 1. Start the Brain (etcd)
echo "Starting etcd Datastore..."
systemctl --user start etcd
sleep 5 # Give etcd time to initialize the database

# 2. Launch Prometheus and Grafana (The Eyes)
echo "Starting Monitoring Stack..."
systemctl --user start prometheus grafana

# 3. Build the Latest Node.js Image
echo "Building Node.js Worker Image..."
cd ~/Desktop/Podflow-Project/app && podman build -t localhost/podflow-node:latest .

# 4. Start the Orchestrator (The Intelligence)
echo "Launching Python Orchestrator..."
python3 ~/Desktop/Podflow-Project/scripts/orchestrator.py
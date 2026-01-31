# PodFlow – Advanced Containerized Microservices Platform

PodFlow is a production-style microservices platform built using Podman.
It demonstrates container orchestration, service isolation, monitoring,
auto-healing, auto-scaling, and security using a honeypot.

## Architecture Overview
- API Gateway (entry point)
- User Service
- Data Service
- Prometheus + Grafana monitoring
- Network isolation (frontend, backend, monitoring)
- Security honeypot

## Tech Stack
- Python (Flask)
- Podman & podman-compose
- Prometheus & Grafana
- Linux networking
- Bash scripting

## Status
🚧 Under active development

## Architecture

- API Gateway is the single public entry point (port 8080)
- Backend service is isolated and not exposed to host
- All traffic flows through the gateway
- Auto-healing restarts backend on failure
- Auto-scaling adjusts replicas based on CPU load
- podman-compose manages service lifecycle

#!/bin/sh
# Try to hit the local port. If it fails, exit with error 1.
curl -f http://localhost:3000/ || exit 1
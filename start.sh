#!/bin/bash
cd "$(dirname "$0")"

# Activate venv
source .venv/bin/activate

# Start server
# Using exec so the process replaces shell (better for systemd)
exec python -m app.main

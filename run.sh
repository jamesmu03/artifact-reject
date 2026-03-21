#!/bin/bash
# run.sh — start the artifact-reject demo
#
# Usage:
#   ./run.sh            → live visualization, no artifacts
#   ./run.sh --inject   → live visualization with injected artifacts
#   ./run.sh --cli      → terminal output only (no plot window)

set -e

PYTHON=/opt/anaconda3/envs/synapse/bin/python3
CLIENT_DIR="$(cd "$(dirname "$0")/client" && pwd)"

# Parse flags
INJECT=""
MODE="viz"
for arg in "$@"; do
  case $arg in
    --inject) INJECT="--inject" ;;
    --cli)    MODE="cli" ;;
  esac
done

# Start simulator if not already running
if ! pgrep -x synapse-sim > /dev/null; then
  echo "Starting Synapse simulator..."
  /opt/anaconda3/envs/synapse/bin/synapse-sim --iface-ip 127.0.0.1 > /tmp/synapse-sim.log 2>&1 &
  sleep 2
  echo "Simulator running."
else
  echo "Simulator already running."
fi

# Run
if [ "$MODE" = "viz" ]; then
  echo "Launching visualization... (close window to stop)"
  $PYTHON "$CLIENT_DIR/visualize.py" --device-ip 127.0.0.1 $INJECT
else
  echo "Running CLI mode for 30s... (Ctrl-C to stop early)"
  $PYTHON "$CLIENT_DIR/artifact_reject.py" --device-ip 127.0.0.1 --duration 30 $INJECT
fi

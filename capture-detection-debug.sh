#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVICE_DIR="$ROOT/apps/ai-detection-service"
VENV="$SERVICE_DIR/.venv"
LOG_FILE="$ROOT/datasets/detect-result.log"
FRAMES_DIR="$ROOT/datasets/detected_frames"
PORT=8001

# Kill existing process on port
EXISTING_PID=$(lsof -ti:$PORT 2>/dev/null || true)
if [ -n "$EXISTING_PID" ]; then
    echo "Killing existing process on port $PORT (PID $EXISTING_PID)..."
    kill "$EXISTING_PID" 2>/dev/null || true
    sleep 1
fi

# Clean old log and frames
rm -f "$LOG_FILE"
rm -rf "$FRAMES_DIR"
touch "$LOG_FILE"
echo "Cleaned old log and frames."

# Start service in background
cd "$SERVICE_DIR"
"$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port $PORT >> "$LOG_FILE" 2>&1 &
SERVICE_PID=$!
echo "AI Detection Service started (PID $SERVICE_PID) — log: $LOG_FILE"
echo "Waiting for 56 detections to complete..."

# Wait until MAX_DETECTIONS message appears in log
tail -f "$LOG_FILE" | grep -m 1 "MAX_DETECTIONS" > /dev/null

# Kill service and report done
kill $SERVICE_PID 2>/dev/null || true
echo "✓ Done — log: $LOG_FILE | frames: $FRAMES_DIR"

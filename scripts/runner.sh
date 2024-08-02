#!/bin/bash

# ===========================================================================
# Configuration
# ===========================================================================
LOG_FILE="bluetracker.log"       # Main log file
LOG_ROTATE_COUNT=14              # Maximum number of rotated log files to keep
PID_FILE="bluetracker.pid"       # File to store the process ID (PID)
ERROR_EXIT_CODE=1                # Exit code for error conditions
STOPPING=false                   # Flag to indicate if shutdown is in progress

# ===========================================================================
# Function: check_and_start_bluetracker
#   Starts the BlueTracker process, handles errors, and saves the PID.
# ===========================================================================
function check_and_start_bluetracker {
  # Check if BlueTracker is already running
  if ! ps aux | grep -v grep | grep "bluetracker" > /dev/null; then

    echo "Setting up BlueTracker..."

    # Change to the 'bluetracker' directory if not already there
    if [[ $PWD != *"bluetracker"* ]]; then
      cd ~/bluetracker || {
        echo "ERROR: Could not find 'bluetracker' directory." >> "$LOG_FILE"
        exit "$ERROR_EXIT_CODE"
      }
    fi

    # Activate the virtual environment (for Python dependencies)
    echo "Activating virtual environment..."
    if ! source .env/bin/activate; then
      echo "ERROR: Failed to activate virtual environment." >> "$LOG_FILE"
      exit "$ERROR_EXIT_CODE"
    fi

    # Create the log file if it doesn't exist
    if [ ! -f "$LOG_FILE" ]; then
      touch "$LOG_FILE"
    fi

    echo "Starting BlueTracker..."

    # Start BlueTracker as a background process, redirecting output to the log file
    nohup bluetracker >> "$LOG_FILE" 2>&1 &
    PID=$!  # Store the Process ID (PID)

    # Wait briefly to ensure BlueTracker has started
    sleep 5

    # Check if BlueTracker started successfully
    if ! ps -p "$PID" > /dev/null 2>&1; then
      echo "ERROR: Failed to start BlueTracker." >> "$LOG_FILE"
      exit "$ERROR_EXIT_CODE"
    fi

    # Store the PID in the PID_FILE
    echo "$PID" > "$PID_FILE"
    echo "BlueTracker started with PID: $PID"

  else
    echo "$(date) - BlueTracker is already running." >> "$LOG_FILE"
  fi
}

# ===========================================================================
# Function: stop_bluetracker
#   Stops the BlueTracker process gracefully or forcefully.
# ===========================================================================
function stop_bluetracker {
  if [ "$STOPPING" = true ]; then
    echo "Shutdown already in progress..."
    return
  fi

  STOPPING=true

  if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "Stopping BlueTracker (PID $PID)..."

    kill -SIGINT "$PID"

    # Wait for a maximum of 60 seconds, checking every 5 seconds
    for i in {1..12}; do
      sleep 5
      if ! kill -0 "$PID" 2> /dev/null; then  # Check if still running
        break  # Exit the loop if the process is gone
      fi
    done

    if kill -0 "$PID" 2> /dev/null; then  # Final check if still running
      echo "WARNING: BlueTracker didn't stop gracefully after 60 seconds. Force killing." >> "$LOG_FILE"
      kill -9 "$PID"
    fi

    rm "$PID_FILE"
  else
    echo "BlueTracker is not running (PID file not found)."
  fi

  STOPPING=false  # Reset the STOPPING flag
}

# ===========================================================================
# Function: rotate_logs
#   Rotates the log files to prevent them from growing too large.
# ===========================================================================
function rotate_logs {
  for LOG_FILE in "bluetracker.log" "cron.log"; do
    if [ -f "$LOG_FILE" ]; then
      log_count=$(ls -t "$LOG_FILE".* 2>/dev/null | wc -l)

      if [ "$log_count" -gt 0 ]; then
          while [ "$log_count" -ge "$LOG_ROTATE_COUNT" ]; do
              rm -f "$(ls -t "$LOG_FILE".* | tail -1)" || { echo "Error deleting log file" >&2; exit 1; }
              log_count=$((log_count - 1))
          done

          timestamp=$(date +%Y-%m-%d_%H-%M-%S)
          echo "$(date) - Rotating logs: $LOG_FILE.$timestamp" >&2
          mv "$LOG_FILE" "$LOG_FILE.$timestamp" || { echo "Error moving log file" >&2; exit 1; }
      fi
    fi
  done
}

# ===========================================================================
# Main Program Loop
#   Continuously monitors BlueTracker and restarts if it stops.
# ===========================================================================

# Trap signals (e.g., Ctrl+C) to gracefully stop BlueTracker
trap 'echo "Exiting due to signal..."; stop_bluetracker; exit 0' SIGINT SIGTERM

# Start BlueTracker
check_and_start_bluetracker  # Initial check and start at boot

# Main Loop
while true; do
  # If shutdown is in progress, exit the loop
  if $STOPPING; then
      break
  fi

  # Check if the process is running
  if ps -p "$(cat "$PID_FILE" 2> /dev/null)" > /dev/null 2>&1; then
    echo "BlueTracker is running. Checking again in 5 minutes..."
    rotate_logs  # Rotate logs before the sleep interval
    sleep 300     # Sleep for 5 minutes
  else
    echo "BlueTracker has stopped. Restarting..." >> "$LOG_FILE"
    check_and_start_bluetracker
  fi
done

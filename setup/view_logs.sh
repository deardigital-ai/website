#!/bin/bash
# Script to view and analyze discussion bot logs

set -e

# Get the repository root directory
REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
LOG_FILE="$REPO_DIR/discussion_bot.log"

# Function to display usage
function show_usage {
  echo "Discussion Bot Log Viewer"
  echo "Usage: $0 [options]"
  echo ""
  echo "Options:"
  echo "  -h, --help           Show this help message"
  echo "  -f, --follow         Follow the log file (like tail -f)"
  echo "  -e, --errors         Show only error messages"
  echo "  -d, --debug          Show debug messages"
  echo "  -i, --info           Show info messages"
  echo "  -p, --placeholders   Show placeholder creation messages"
  echo "  -g, --github         Show GitHub API interactions"
  echo "  -c, --commands       Show command executions"
  echo "  -l, --last N         Show last N lines (default: 50)"
  echo ""
  echo "Examples:"
  echo "  $0 -f                Follow the log file in real-time"
  echo "  $0 -e                Show only error messages"
  echo "  $0 -g -p             Show GitHub API and placeholder creation messages"
  echo "  $0 -l 100            Show last 100 lines"
}

# Default values
FOLLOW=false
FILTER=""
LAST_LINES=50

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      show_usage
      exit 0
      ;;
    -f|--follow)
      FOLLOW=true
      shift
      ;;
    -e|--errors)
      if [ -z "$FILTER" ]; then
        FILTER="ERROR"
      else
        FILTER="$FILTER|ERROR"
      fi
      shift
      ;;
    -d|--debug)
      if [ -z "$FILTER" ]; then
        FILTER="DEBUG"
      else
        FILTER="$FILTER|DEBUG"
      fi
      shift
      ;;
    -i|--info)
      if [ -z "$FILTER" ]; then
        FILTER="INFO"
      else
        FILTER="$FILTER|INFO"
      fi
      shift
      ;;
    -p|--placeholders)
      if [ -z "$FILTER" ]; then
        FILTER="placeholder"
      else
        FILTER="$FILTER|placeholder"
      fi
      shift
      ;;
    -g|--github)
      if [ -z "$FILTER" ]; then
        FILTER="GitHub API|GraphQL"
      else
        FILTER="$FILTER|GitHub API|GraphQL"
      fi
      shift
      ;;
    -c|--commands)
      if [ -z "$FILTER" ]; then
        FILTER="Running command|Command stdout|Command stderr"
      else
        FILTER="$FILTER|Running command|Command stdout|Command stderr"
      fi
      shift
      ;;
    -l|--last)
      shift
      if [[ $# -gt 0 && "$1" =~ ^[0-9]+$ ]]; then
        LAST_LINES=$1
        shift
      else
        echo "Error: --last requires a numeric argument"
        exit 1
      fi
      ;;
    *)
      echo "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
  echo "Error: Log file not found at $LOG_FILE"
  exit 1
fi

echo "Viewing log file: $LOG_FILE"

# Apply filters and display logs
if [ -z "$FILTER" ]; then
  # No filter specified, show all logs
  if [ "$FOLLOW" = true ]; then
    tail -n $LAST_LINES -f "$LOG_FILE" | grep --color=auto -E "ERROR|WARN|$"
  else
    tail -n $LAST_LINES "$LOG_FILE" | grep --color=auto -E "ERROR|WARN|$"
  fi
else
  # Apply filter
  if [ "$FOLLOW" = true ]; then
    tail -n $LAST_LINES -f "$LOG_FILE" | grep --color=auto -E "$FILTER|$"
  else
    tail -n $LAST_LINES "$LOG_FILE" | grep --color=auto -E "$FILTER|$"
  fi
fi 
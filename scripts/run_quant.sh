#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
RUN_MODULE="apps.trading.main"

PYTHON_BIN="${PYTHON:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') Python executable not found: ${PYTHON_BIN}" >&2
    exit 1
fi
MAX_RESTARTS=3
RESTART_DELAY=10

cd "$PROJECT_DIR" || exit 1

# require two positional args (no defaults)
ARG1="$1"
ARG2="$2"
if [ -z "$ARG1" ] || [ -z "$ARG2" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') usage: $0 <arg1> <arg2> [condition_profile] (e.g. kiwoom quant private_condition)" >&2
    exit 1
fi
CONDITION_PROFILE="${3:-${QUANT_PROFILE:-private_condition}}"

LOG_DIR="$PROJECT_DIR/output/log/trading"
mkdir -p "$LOG_DIR"
LOGFILE="$LOG_DIR/${ARG1}_${ARG2}.txt"

restart_count=0
echo "$(date '+%Y-%m-%d %H:%M:%S') run_quant.sh watchdog started (args: $ARG1 $ARG2, profile: $CONDITION_PROFILE)" > "$LOGFILE"

while true; do
    echo "$(date '+%Y-%m-%d %H:%M:%S') launching QUANT_PROFILE=$CONDITION_PROFILE $PYTHON_BIN -m $RUN_MODULE $ARG1 $ARG2 (attempt $((restart_count+1)))" >> "$LOGFILE"
    QUANT_PROFILE="$CONDITION_PROFILE" "$PYTHON_BIN" -m "$RUN_MODULE" "$ARG1" "$ARG2" >> "$LOGFILE" 2>&1
    rc=$?
    echo "$(date '+%Y-%m-%d %H:%M:%S') process exited with code $rc" >> "$LOGFILE"

    if [ "$rc" -eq 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') normal exit -> stopping watchdog" >> "$LOGFILE"
        exit 0
    fi

    restart_count=$((restart_count+1))
    if [ "$restart_count" -ge "$MAX_RESTARTS" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') reached max restarts ($MAX_RESTARTS) -> aborting" >> "$LOGFILE"
        exit $rc
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') abnormal exit -> sleeping ${RESTART_DELAY}s before restart" >> "$LOGFILE"
    sleep "$RESTART_DELAY"
done

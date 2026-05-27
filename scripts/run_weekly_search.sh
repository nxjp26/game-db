#!/bin/bash
SCRIPT_DIR="/Users/hyungdochoi/기업DB"
LOG_FILE="$SCRIPT_DIR/scripts/weekly_search.log"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 주간 서칭 시작 ===" >> "$LOG_FILE"

if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

cd "$SCRIPT_DIR"
"$PYTHON" scripts/weekly_search.py >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') 완료 (성공) ===" >> "$LOG_FILE"
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') 완료 (오류: $EXIT_CODE) ===" >> "$LOG_FILE"
fi

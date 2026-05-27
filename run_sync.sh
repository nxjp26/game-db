#!/bin/bash
# 기업DB 자동 동기화 스크립트
# launchd에 의해 매일 자동 실행됨

SCRIPT_DIR="/Users/hyungdochoi/기업DB"
LOG_FILE="$SCRIPT_DIR/sync.log"
PYTHON="/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"

echo "=== $(date '+%Y-%m-%d %H:%M:%S') 동기화 시작 ===" >> "$LOG_FILE"

# .env 로드
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
fi

# sync.py 실행
cd "$SCRIPT_DIR"
"$PYTHON" sync.py --push >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') 완료 (성공) ===" >> "$LOG_FILE"
else
    echo "=== $(date '+%Y-%m-%d %H:%M:%S') 완료 (오류 코드: $EXIT_CODE) ===" >> "$LOG_FILE"
fi

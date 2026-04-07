#!/bin/bash
# YouTube Channel Analyzer - Cron Job Runner
# Usage: ./run.sh
# Cron example (daily at 9am): 0 9 * * * /path/to/yt-analyzer/run.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting YouTube data collection..."

# Run data collection
python3 collect.py
if [ $? -ne 0 ]; then
    echo "ERROR: collect.py failed" >&2
    exit 1
fi

# Run analysis
python3 analyze.py
if [ $? -ne 0 ]; then
    echo "ERROR: analyze.py failed" >&2
    exit 1
fi

# Copy analysis to docs for GitHub Pages
cp data/analysis.json docs/data.json
echo "Copied analysis.json to docs/data.json"

# Git commit and push (if in a git repo)
if [ -d .git ]; then
    git add -A
    git commit -m "📊 데이터 업데이트 $(date '+%Y-%m-%d %H:%M')" || echo "Nothing to commit"
    git push origin main || git push origin master || echo "Push failed - check remote"
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - Done!"

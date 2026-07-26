#!/bin/bash
# Claude Code PreToolUse hook: take an APFS local snapshot before Bash
# commands run, debounced so busy sessions don't snapshot constantly.
#
# This hook must never block the agent, so it always exits 0.
#
# Configure the debounce window (seconds) with SNAPSHOT_DEBOUNCE_SECONDS
# in the hook command; default is 300 (5 minutes).
set -u

DEBOUNCE_SECONDS="${SNAPSHOT_DEBOUNCE_SECONDS:-300}"
STAMP="$HOME/.cache/mbp-backups/last-snapshot"
mkdir -p "$(dirname "$STAMP")" 2>/dev/null || exit 0

now=$(date +%s)
if [[ -f "$STAMP" ]]; then
  last=$(cat "$STAMP" 2>/dev/null || echo 0)
  if (( now - last < DEBOUNCE_SECONDS )); then
    exit 0
  fi
fi

# Record the attempt first so a slow/failing tmutil can't cause a
# snapshot storm across parallel tool calls.
echo "$now" >"$STAMP"

tmutil localsnapshot >/dev/null 2>&1 || true
exit 0

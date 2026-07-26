#!/bin/bash
# Install a launchd agent that takes an APFS local snapshot on a schedule.
#
# Usage:
#   ./install.sh                                # snapshot every 20 minutes
#   SNAPSHOT_INTERVAL_SECONDS=600 ./install.sh  # snapshot every 10 minutes
#
# Runs entirely as your user — no sudo required. Re-run any time to change
# the interval or after moving this repo; it replaces the existing agent.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
INTERVAL="${SNAPSHOT_INTERVAL_SECONDS:-1200}"
LABEL="com.mbp-backups.snapshot"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

chmod +x "$REPO_DIR/bin/"*

mkdir -p "$HOME/Library/LaunchAgents" "$HOME/Library/Logs/mbp-backups"

cat >"$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$REPO_DIR/bin/take-snapshot</string>
  </array>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/mbp-backups/launchd.err</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"

echo "Installed: APFS local snapshot every $((INTERVAL / 60)) minutes."
echo "  Agent:     $PLIST"
echo "  Log:       ~/Library/Logs/mbp-backups/snapshots.log"
echo "  Snapshots: $REPO_DIR/bin/list-snapshots"

#!/bin/bash
# Remove the launchd snapshot agent installed by install.sh.
# Existing snapshots are untouched (they expire on their own within ~24h).
set -euo pipefail

LABEL="com.mbp-backups.snapshot"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
rm -f "$PLIST"

echo "Uninstalled $LABEL."

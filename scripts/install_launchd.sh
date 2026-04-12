#!/bin/zsh
set -euo pipefail

PROJECT_DIR="/Users/prasadhegde/Documents/MorningBriefs"
PLIST_NAME="com.prasad.morningbriefs.plist"
SOURCE_PLIST="$PROJECT_DIR/launchd/$PLIST_NAME"
TARGET_DIR="$HOME/Library/LaunchAgents"
TARGET_PLIST="$TARGET_DIR/$PLIST_NAME"

mkdir -p "$TARGET_DIR"
cp "$SOURCE_PLIST" "$TARGET_PLIST"
chmod 644 "$TARGET_PLIST"

launchctl unload "$TARGET_PLIST" 2>/dev/null || true
launchctl load "$TARGET_PLIST"

echo "Installed $TARGET_PLIST"
echo "Morning Briefs will run every day at 8:00 a.m. local Mac time."

#!/bin/bash
# Script to properly handle HTML email viewing in mutt
# Usage: view_html.sh <html_file>

set -e

# Check if a filename was provided
if [ $# -eq 0 ]; then
  echo "No file specified."
  exit 1
fi

FILE="$1"
TMPFILE=$(mktemp /tmp/mutt-html-XXXXXXXXXX.html)
trap "rm -f $TMPFILE" EXIT

# Copy the HTML file to make it accessible to browsers
cat "$FILE" > "$TMPFILE"

# Always default to browser - most reliable rendering
open -a Safari "$TMPFILE"

# Wait for the user to press a key after viewing (prevents terminal from continuing)
read -n 1 -s -r -p "Press any key to continue..."
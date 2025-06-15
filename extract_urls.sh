#!/bin/bash
# Simple script to extract URLs from input and let user select one to open
# For use with mutt

# Create a temporary file
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

# Extract URLs using grep
grep -E 'https?://[^ >,;]+' | sed 's/[<>]//g' | sort -u > "$TMPFILE"

# Check if any URLs were found
if [ ! -s "$TMPFILE" ]; then
  echo "No URLs found in message." >&2
  exit 1
fi

# Number each URL
nl -w3 -s': ' "$TMPFILE" >&2

# Prompt user to choose a URL
echo -n "Enter URL number to open (q to quit): " >&2
read choice

# Open the chosen URL
if [[ "$choice" =~ ^[0-9]+$ ]]; then
  url=$(sed -n "${choice}p" "$TMPFILE")
  if [ -n "$url" ]; then
    open "$url"
  else
    echo "Invalid selection." >&2
    exit 1
  fi
fi
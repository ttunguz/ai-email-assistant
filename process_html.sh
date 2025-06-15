#!/bin/bash
# Script to improve HTML rendering in mutt for text mode view
# This script handles HTML files passed as parameters to it

# Check if file parameter was provided
if [ $# -eq 1 ]; then
  # File provided as argument
  INPUT="$1"
else
  # No file provided, exit with error message
  echo "Error: HTML file not provided"
  exit 1
fi

# Function to handle common HTML entities
handle_entities() {
  sed -e 's/&nbsp;/ /g' \
      -e 's/&lt;/</g' \
      -e 's/&gt;/>/g' \
      -e 's/&amp;/\&/g' \
      -e 's/&quot;/"/g' \
      -e 's/&apos;/'\''/g' \
      -e 's/&mdash;/—/g' \
      -e 's/&ndash;/–/g' \
      -e 's/&hellip;/.../g' \
      -e 's/&bull;/•/g' \
      -e 's/&copy;/©/g' \
      -e 's/&reg;/®/g' \
      -e 's/&trade;/™/g'
}

# Try lynx first (best for HTML to text conversion)
if command -v lynx &> /dev/null; then
  lynx -dump -nolist -width=80 "$INPUT" | handle_entities
  exit 0
fi

# Try w3m next
if command -v w3m &> /dev/null; then
  w3m -dump -T text/html -cols 80 "$INPUT" | handle_entities
  exit 0
fi

# Try textutil (macOS built-in)
if command -v textutil &> /dev/null; then
  textutil -convert txt -stdout "$INPUT" | handle_entities | sed -e '/^$/d' -e 's/^[ \t]*//'
  exit 0
fi

# Ultimate fallback - basic stripping of HTML tags
sed -e 's/<[^>]*>//g' "$INPUT" | handle_entities | grep -v '^$' | sed 's/^[ \t]*//'
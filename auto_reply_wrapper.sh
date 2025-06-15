#!/bin/bash
# Wrapper script for auto_reply_single.py to ensure virtual environment is used

# Suppress tokenizers parallelism warning
export TOKENIZERS_PARALLELISM=false

# Set the script directory to the absolute path
SCRIPT_DIR="/Users/tomasztunguz/.mutt"

# Add debugging - log to a file to see what's happening
echo "$(date): Wrapper called with args: $@" >> "${SCRIPT_DIR}/debug.log"
echo "$(date): Current working directory: $(pwd)" >> "${SCRIPT_DIR}/debug.log"
echo "$(date): Script dir: ${SCRIPT_DIR}" >> "${SCRIPT_DIR}/debug.log"

# Change to the script directory to ensure relative paths work
cd "${SCRIPT_DIR}"

# Check if the virtual environment Python exists
if [ ! -f "${SCRIPT_DIR}/.venv/bin/python3" ]; then
    echo "$(date): ERROR - Virtual environment Python not found" >> "${SCRIPT_DIR}/debug.log"
    echo "Error: Virtual environment not found"
    exit 1
fi

# Check if the script exists
if [ ! -f "${SCRIPT_DIR}/auto_reply_single.py" ]; then
    echo "$(date): ERROR - auto_reply_single.py not found" >> "${SCRIPT_DIR}/debug.log"
    echo "Error: auto_reply_single.py not found"
    exit 1
fi

# Use the Python interpreter from the virtual environment with absolute paths
echo "$(date): Executing Python script" >> "${SCRIPT_DIR}/debug.log"
exec "${SCRIPT_DIR}/.venv/bin/python3" "${SCRIPT_DIR}/auto_reply_single.py" "$@" 
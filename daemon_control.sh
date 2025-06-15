#!/bin/bash
# LanceDB Daemon Control Script

DAEMON_DIR="/Users/tomasztunguz/.mutt"
DAEMON_SCRIPT="$DAEMON_DIR/lancedb_daemon.py"
PID_FILE="$DAEMON_DIR/lancedb_daemon.pid"
LOG_FILE="$DAEMON_DIR/lancedb_daemon.log"
SOCKET_PATH="/tmp/lancedb_daemon.sock"

start_daemon() {
    if is_running; then
        echo "Daemon is already running (PID: $(cat $PID_FILE))"
        return 1
    fi
    
    echo "Starting LanceDB daemon..."
    cd "$DAEMON_DIR"
    nohup ./lancedb_daemon.py > /dev/null 2>&1 &
    
    # Wait a moment for startup
    sleep 2
    
    if is_running; then
        echo "Daemon started successfully (PID: $(cat $PID_FILE))"
        echo "Loading models... (this may take 30-60 seconds)"
        tail -f "$LOG_FILE" | grep -m 1 "Components loaded successfully!" > /dev/null
        echo "Daemon ready!"
    else
        echo "Failed to start daemon. Check log: $LOG_FILE"
        return 1
    fi
}

stop_daemon() {
    if ! is_running; then
        echo "Daemon is not running"
        return 1
    fi
    
    echo "Stopping LanceDB daemon..."
    PID=$(cat "$PID_FILE")
    kill "$PID" 2>/dev/null
    
    # Wait for cleanup
    sleep 1
    
    if ! is_running; then
        echo "Daemon stopped successfully"
    else
        echo "Force killing daemon..."
        kill -9 "$PID" 2>/dev/null
        cleanup_files
        echo "Daemon force stopped"
    fi
}

restart_daemon() {
    echo "Restarting LanceDB daemon..."
    stop_daemon
    sleep 1
    start_daemon
}

is_running() {
    if [ ! -f "$PID_FILE" ]; then
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        return 0
    else
        # PID file exists but process is dead
        cleanup_files
        return 1
    fi
}

cleanup_files() {
    [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
    [ -S "$SOCKET_PATH" ] && rm -f "$SOCKET_PATH"
}

status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo "Daemon is running (PID: $PID)"
        
        # Test if daemon is responsive
        if [ -S "$SOCKET_PATH" ]; then
            echo "Socket is available at $SOCKET_PATH"
        else
            echo "Warning: Socket not found - daemon may be starting up"
        fi
    else
        echo "Daemon is not running"
    fi
}

show_log() {
    if [ -f "$LOG_FILE" ]; then
        tail -20 "$LOG_FILE"
    else
        echo "Log file not found: $LOG_FILE"
    fi
}

case "$1" in
    start)
        start_daemon
        ;;
    stop)
        stop_daemon
        ;;
    restart)
        restart_daemon
        ;;
    status)
        status
        ;;
    log)
        show_log
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|log}"
        echo ""
        echo "Commands:"
        echo "  start   - Start the LanceDB daemon"
        echo "  stop    - Stop the LanceDB daemon"
        echo "  restart - Restart the LanceDB daemon"
        echo "  status  - Check daemon status"
        echo "  log     - Show recent log entries"
        exit 1
        ;;
esac 
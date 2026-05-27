#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$SCRIPT_DIR/.server_pids"

start() {
    echo "Starting servers..."

    # Start Flask backend
    cd "$SCRIPT_DIR"
    nohup uv run python -m server.app > /tmp/flask.log 2>&1 &
    FLASK_PID=$!
    echo "Flask backend started (PID: $FLASK_PID)"

    # Start Vue frontend
    cd "$SCRIPT_DIR/web"
    nohup pnpm run dev > /tmp/vue.log 2>&1 &
    VUE_PID=$!
    echo "Vue frontend started (PID: $VUE_PID)"

    # Save PIDs
    echo "$FLASK_PID $VUE_PID" > "$PID_FILE"

    sleep 2
    echo ""
    echo "Servers started:"
    echo "  Flask backend:  http://localhost:5002"
    echo "  Vue frontend:   http://localhost:3000"
    echo ""
    echo "Logs:"
    echo "  Flask: tail -f /tmp/flask.log"
    echo "  Vue:   tail -f /tmp/vue.log"
}

stop() {
    echo "Stopping servers..."

    # Kill processes on specific ports
    for port in 5002 3000; do
        pid=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pid" ]; then
            kill $pid 2>/dev/null && echo "Killed process on port $port (PID: $pid)" || echo "Failed to kill process on port $port"
        fi
    done

    # Also kill from PID file if exists
    if [ -f "$PID_FILE" ]; then
        read FLASK_PID VUE_PID < "$PID_FILE"
        kill -0 "$FLASK_PID" 2>/dev/null && kill "$FLASK_PID" 2>/dev/null
        kill -0 "$VUE_PID" 2>/dev/null && kill "$VUE_PID" 2>/dev/null
        rm -f "$PID_FILE"
    fi

    # Wait for processes to stop
    sleep 1

    # Force kill if still running
    for port in 5002 3000; do
        pid=$(lsof -ti:$port 2>/dev/null)
        if [ -n "$pid" ]; then
            kill -9 $pid 2>/dev/null && echo "Force killed process on port $port (PID: $pid)"
        fi
    done

    echo "Servers stopped"
}

status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "No servers running"
        return
    fi

    read FLASK_PID VUE_PID < "$PID_FILE"

    echo "Server status:"
    if kill -0 "$FLASK_PID" 2>/dev/null; then
        echo "  Flask backend:  running (PID: $FLASK_PID)"
    else
        echo "  Flask backend:  stopped"
    fi

    if kill -0 "$VUE_PID" 2>/dev/null; then
        echo "  Vue frontend:   running (PID: $VUE_PID)"
    else
        echo "  Vue frontend:   stopped"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        stop
        sleep 1
        start
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

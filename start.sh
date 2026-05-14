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
    echo "  Flask backend:  http://localhost:5001"
    echo "  Vue frontend:   http://localhost:3000"
    echo ""
    echo "Logs:"
    echo "  Flask: tail -f /tmp/flask.log"
    echo "  Vue:   tail -f /tmp/vue.log"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "No servers running (PID file not found)"
        return
    fi

    read FLASK_PID VUE_PID < "$PID_FILE"

    echo "Stopping servers..."

    if kill -0 "$FLASK_PID" 2>/dev/null; then
        kill "$FLASK_PID"
        echo "Flask backend stopped (PID: $FLASK_PID)"
    else
        echo "Flask backend not running"
    fi

    if kill -0 "$VUE_PID" 2>/dev/null; then
        kill "$VUE_PID"
        echo "Vue frontend stopped (PID: $VUE_PID)"
    else
        echo "Vue frontend not running"
    fi

    rm -f "$PID_FILE"
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

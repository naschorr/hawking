#!/bin/sh
set -eu

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-hawking}"
mkdir -p "$XDG_RUNTIME_DIR"
chmod 700 "$XDG_RUNTIME_DIR"

if [ -f /tmp/.X0-lock ]; then
	lock_pid=$(cat /tmp/.X0-lock 2>/dev/null || true)
	if [ -z "$lock_pid" ] || [ ! -d "/proc/$lock_pid" ]; then
		rm -f /tmp/.X0-lock /tmp/.X11-unix/X0
	fi
fi

Xvfb :0 -screen 0 1024x768x16 -nolisten tcp &
xvfb_pid=$!

attempt=0
while [ ! -S /tmp/.X11-unix/X0 ]; do
	if ! kill -0 "$xvfb_pid" 2>/dev/null; then
		echo "Xvfb failed to start on display :0" >&2
		exit 1
	fi
	attempt=$((attempt + 1))
	if [ "$attempt" -ge 50 ]; then
		echo "Timed out waiting for Xvfb display :0" >&2
		kill "$xvfb_pid" 2>/dev/null || true
		exit 1
	fi
	sleep 0.1
done

exec python /app/code/hawking/hawking.py
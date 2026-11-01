#!/bin/bash

set -euo pipefail

SERVER_HOST="${THEBRAIN_TUNNEL_HOST:-192.168.40.73}"
SERVER_USER="${THEBRAIN_TUNNEL_USER:-faisal}"
SERVER_SSH_PORT="${THEBRAIN_TUNNEL_SSH_PORT:-22}"
SERVER_API_PORT="${THEBRAIN_TUNNEL_SERVER_PORT:-18001}"
MAC_API_PORT="${THEBRAIN_LOCAL_API_PORT:-8001}"

TUNNEL_LABEL="com.eventmarketdb.thebrain-tunnel"
APP_LABEL="com.eventmarketdb.thebrain-start"
LAUNCH_DOMAIN="gui/$(id -u)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs/EventMarketDB"
TUNNEL_PLIST="$LAUNCH_AGENTS_DIR/$TUNNEL_LABEL.plist"
APP_PLIST="$LAUNCH_AGENTS_DIR/$APP_LABEL.plist"

fail() {
    printf 'Setup stopped: %s\n' "$1" >&2
    exit 1
}

unload_job() {
    local label="$1"
    launchctl bootout "$LAUNCH_DOMAIN/$label" >/dev/null 2>&1 || true
}

uninstall() {
    unload_job "$TUNNEL_LABEL"
    unload_job "$APP_LABEL"
    rm -f "$TUNNEL_PLIST" "$APP_PLIST"
    printf 'Removed the automatic TheBrain tunnel.\n'
}

if [[ "${1:-}" == "--uninstall" ]]; then
    uninstall
    exit 0
fi

[[ "$(uname -s)" == "Darwin" ]] || fail "run this installer on the Mac that runs TheBrain."
[[ -x /usr/bin/ssh ]] || fail "macOS SSH was not found at /usr/bin/ssh."

printf 'Checking automatic SSH access to %s@%s...\n' "$SERVER_USER" "$SERVER_HOST"
if ! /usr/bin/ssh \
    -p "$SERVER_SSH_PORT" \
    -o BatchMode=yes \
    -o ConnectTimeout=8 \
    "$SERVER_USER@$SERVER_HOST" true; then
    fail "SSH needs a password or key confirmation. First make normal SSH login work without a password, then run this installer again."
fi

mkdir -p "$LAUNCH_AGENTS_DIR" "$LOG_DIR"
chmod 700 "$LOG_DIR"

cat >"$TUNNEL_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$TUNNEL_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/ssh</string>
        <string>-NT</string>
        <string>-p</string>
        <string>$SERVER_SSH_PORT</string>
        <string>-o</string>
        <string>BatchMode=yes</string>
        <string>-o</string>
        <string>ExitOnForwardFailure=yes</string>
        <string>-o</string>
        <string>ServerAliveInterval=30</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>-o</string>
        <string>ConnectTimeout=10</string>
        <string>-R</string>
        <string>$SERVER_API_PORT:127.0.0.1:$MAC_API_PORT</string>
        <string>$SERVER_USER@$SERVER_HOST</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>ProcessType</key>
    <string>Background</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/thebrain-tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/thebrain-tunnel-error.log</string>
</dict>
</plist>
PLIST

cat >"$APP_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$APP_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/open</string>
        <string>-g</string>
        <string>-a</string>
        <string>TheBrain</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
PLIST

chmod 600 "$TUNNEL_PLIST" "$APP_PLIST"
plutil -lint "$TUNNEL_PLIST" >/dev/null
plutil -lint "$APP_PLIST" >/dev/null

unload_job "$TUNNEL_LABEL"
unload_job "$APP_LABEL"
launchctl bootstrap "$LAUNCH_DOMAIN" "$APP_PLIST"
launchctl bootstrap "$LAUNCH_DOMAIN" "$TUNNEL_PLIST"
launchctl enable "$LAUNCH_DOMAIN/$APP_LABEL"
launchctl enable "$LAUNCH_DOMAIN/$TUNNEL_LABEL"
launchctl kickstart -k "$LAUNCH_DOMAIN/$TUNNEL_LABEL"

printf '\nAutomatic setup is installed.\n'
printf 'TheBrain will open after Mac login, and the tunnel will reconnect automatically.\n'
printf 'No TheBrain API key was stored.\n'
printf 'Tunnel errors, if any: %s\n' "$LOG_DIR/thebrain-tunnel-error.log"

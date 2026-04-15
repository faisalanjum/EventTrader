#!/usr/bin/env bash
# patch_claude_haiku_advisor.sh — Enable haiku + advisor in Claude Code CLI
#
# The Claude Code CLI has a hardcoded client-side gate (WyH function) that blocks
# haiku from using the advisor tool, even though the Anthropic API fully supports it.
# This script patches the CLI binary to allow haiku as a base model with advisor.
#
# What it does:
#   Changes WyH's first check from .includes("opus-4-6") to .includes("aiku-4-5")
#   This makes haiku model strings (e.g., "claude-haiku-4-5-20251001") pass the gate.
#   The second check .includes("sonnet-4-6") remains untouched.
#   peH (advisor model gate) is NOT modified — advisor must still be opus or sonnet.
#
# Trade-off:
#   Opus as base model will no longer get advisor (unnecessary — opus IS the best model).
#   Sonnet as base model still works with advisor (unchanged).
#   Haiku as base model NOW works with advisor (the whole point).
#
# Usage:
#   ./patch_claude_haiku_advisor.sh          # patch current CLI version
#   ./patch_claude_haiku_advisor.sh --revert # restore original binary
#
# Re-run after each `claude update` or auto-update.

set -euo pipefail

CLAUDE_DIR="${HOME}/.local/share/claude/versions"
BINARY=$(ls -t "${CLAUDE_DIR}"/ 2>/dev/null | grep -E '^[0-9]+\.[0-9]+\.[0-9]+$' | head -1)

if [[ -z "$BINARY" ]]; then
    echo "ERROR: No Claude Code binary found in ${CLAUDE_DIR}" >&2
    exit 1
fi

BINARY_PATH="${CLAUDE_DIR}/${BINARY}"
BACKUP_PATH="${BINARY_PATH}.original"
PATCHED_PATH="${BINARY_PATH}-haiku-patched"

echo "Claude Code binary: ${BINARY_PATH} (v${BINARY})"

# --- Revert mode ---
if [[ "${1:-}" == "--revert" ]]; then
    if [[ -f "$BACKUP_PATH" ]]; then
        # Can't overwrite running binary; copy backup to new name, swap symlinks
        cp "$BACKUP_PATH" "${BINARY_PATH}.restored"
        echo "Restored original binary to ${BINARY_PATH}.restored"
        echo "To activate: stop Claude Code, then: mv '${BINARY_PATH}.restored' '${BINARY_PATH}'"
    else
        echo "No backup found at ${BACKUP_PATH}"
    fi
    exit 0
fi

# --- Patch mode ---

# Find WyH function locations
echo "Scanning for WyH function..."
OFFSETS=$(grep -obUaP 'WyH\(H\)\{let \$=H\.toLowerCase\(\);return \$\.includes\("opus-4-6"\)' "$BINARY_PATH" | cut -d: -f1)

if [[ -z "$OFFSETS" ]]; then
    # Check if already patched
    PATCHED_CHECK=$(grep -obUaP 'WyH\(H\)\{let \$=H\.toLowerCase\(\);return \$\.includes\("aiku-4-5"\)' "$BINARY_PATH" | head -1)
    if [[ -n "$PATCHED_CHECK" ]]; then
        echo "Binary is already patched (haiku advisor enabled)."
        exit 0
    fi
    echo "ERROR: Could not find WyH function in binary. Binary format may have changed." >&2
    exit 1
fi

COUNT=$(echo "$OFFSETS" | wc -l)
echo "Found ${COUNT} WyH occurrence(s)"

# Backup original
if [[ ! -f "$BACKUP_PATH" ]]; then
    cp "$BINARY_PATH" "$BACKUP_PATH"
    echo "Backup saved: ${BACKUP_PATH}"
else
    echo "Backup already exists: ${BACKUP_PATH}"
fi

# Copy for patching (can't write to running binary)
cp "$BINARY_PATH" "$PATCHED_PATH"

# Patch each occurrence: "opus-4-6" → "aiku-4-5" (same 8-byte length)
for OFFSET in $OFFSETS; do
    # "opus-4-6" starts at +48 from the WyH pattern start
    BYTE_OFFSET=$((OFFSET + 48))

    # Verify bytes before patching
    VERIFY=$(dd if="$PATCHED_PATH" bs=1 skip="$BYTE_OFFSET" count=8 2>/dev/null)
    if [[ "$VERIFY" != "opus-4-6" ]]; then
        echo "ERROR: Expected 'opus-4-6' at offset ${BYTE_OFFSET}, got '${VERIFY}'" >&2
        rm -f "$PATCHED_PATH"
        exit 1
    fi

    printf 'aiku-4-5' | dd of="$PATCHED_PATH" bs=1 seek="$BYTE_OFFSET" conv=notrunc 2>/dev/null
    echo "  Patched offset ${BYTE_OFFSET}: opus-4-6 → aiku-4-5"
done

chmod +x "$PATCHED_PATH"

# Verify patch
echo ""
echo "=== Verification ==="
PATCHED_CHECK=$(dd if="$PATCHED_PATH" bs=1 skip=$(($(echo "$OFFSETS" | head -1) + 0)) count=100 2>/dev/null | head -c 100)
echo "WyH now reads: ...${PATCHED_CHECK:48:30}..."

echo ""
echo "=== Patched binary ready ==="
echo "Path: ${PATCHED_PATH}"
echo ""
echo "Usage via CLI:"
echo "  ${PATCHED_PATH} -p --model haiku --settings '{\"advisorModel\":\"opus\"}' \"your prompt\""
echo ""
echo "Usage via SDK:"
echo "  ClaudeAgentOptions("
echo "      cli_path=\"${PATCHED_PATH}\","
echo "      model=\"haiku\","
echo "      settings='{\"advisorModel\": \"opus\"}',"
echo "  )"
echo ""
echo "To replace the default binary (after stopping Claude Code):"
echo "  mv '${PATCHED_PATH}' '${BINARY_PATH}'"

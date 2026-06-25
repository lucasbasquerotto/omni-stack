#!/bin/bash
# Idempotent seed copy — copies seed defaults into /opt/data only if they don't exist.
# Never overwrites existing runtime data.
set -e

SEED_DIR="/opt/omni-stack"
DATA_DIR="/opt/data"

if [ ! -d "$SEED_DIR" ]; then
    echo "[seed-copy] No seed directory at $SEED_DIR, skipping"
    exit 0
fi

echo "[seed-copy] Copying seed defaults from $SEED_DIR to $DATA_DIR (idempotent)"

# Copy plugin configs (plugin.json, mcp-config.json, server.py)
if [ -d "$SEED_DIR/plugins" ]; then
    find "$SEED_DIR/plugins" -type f \( -name 'plugin.json' -o -name 'mcp-config.json' -o -name 'server.py' -o -name 'platform.py' \) | while IFS= read -r f; do
        rel="${f#$SEED_DIR/}"
        target="$DATA_DIR/$rel"
        if [ ! -f "$target" ]; then
            mkdir -p "$(dirname "$target")"
            cp "$f" "$target"
            echo "  + $rel"
        fi
    done
fi

# Copy profile defaults (config.json, templates, memories)
if [ -d "$SEED_DIR/profiles" ]; then
    find "$SEED_DIR/profiles" -type f | while IFS= read -r f; do
        rel="${f#$SEED_DIR/}"
        target="$DATA_DIR/$rel"
        if [ ! -f "$target" ]; then
            mkdir -p "$(dirname "$target")"
            cp "$f" "$target"
            echo "  + $rel"
        fi
    done
fi

# Copy scripts
if [ -d "$SEED_DIR/scripts" ]; then
    find "$SEED_DIR/scripts" -type f | while IFS= read -r f; do
        rel="${f#$SEED_DIR/}"
        target="$DATA_DIR/$rel"
        if [ ! -f "$target" ]; then
            mkdir -p "$(dirname "$target")"
            cp "$f" "$target"
            chmod +x "$target" 2>/dev/null || true
            echo "  + $rel"
        fi
    done
fi

echo "[seed-copy] Done"

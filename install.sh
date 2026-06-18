#!/bin/bash
# Installs the pypinyin IBus engine for the current user, no root required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/ibus-pypinyin"
BIN_DIR="$HOME/.local/bin"
CONFIG_CMD="$BIN_DIR/rootless-pinyin-config"
PANEL_CMD="$BIN_DIR/rootless-pinyin-panel"
USER_SERVICE="$HOME/.local/share/dbus-1/services/org.freedesktop.IBus.service"
USER_SERVICE_BACKUP="$USER_SERVICE.pre-pypinyin"

echo "==> Checking prerequisites"
if ! python3 - "$SCRIPT_DIR/src" <<'PYEOF'
import sys

sys.path.insert(0, sys.argv[1])
try:
    import pinyin_lib
except Exception as exc:
    print("ERROR: could not load libpinyin:", exc, file=sys.stderr)
    print("       Install libpinyin + libpinyin-data, or set LIBPINYIN_PATH and", file=sys.stderr)
    print("       LIBPINYIN_DATA_DIR before running install.sh.", file=sys.stderr)
    raise SystemExit(1)

print("    libpinyin:", pinyin_lib.LIBPINYIN_PATH)
print("    data dir: ", pinyin_lib.SYSTEM_DATA_DIR)
PYEOF
then
    exit 1
fi
if ! python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus" 2>/dev/null; then
    echo "ERROR: python3 IBus GObject Introspection bindings not available." >&2
    echo "       Need python3-gobject and the ibus typelib installed system-wide." >&2
    exit 1
fi

echo "==> Installing engine files to $DEST"
mkdir -p "$DEST"
cp "$SCRIPT_DIR/src/engine.py" \
   "$SCRIPT_DIR/src/pinyin_lib.py" \
   "$SCRIPT_DIR/src/config.py" \
   "$SCRIPT_DIR/src/configure.py" \
   "$SCRIPT_DIR/src/configure_gui.py" \
   "$SCRIPT_DIR/src/panel.py" \
   "$DEST/"
chmod +x "$DEST/engine.py"
chmod +x "$DEST/configure.py" "$DEST/configure_gui.py" "$DEST/panel.py"

echo "==> Installing config command to $CONFIG_CMD"
mkdir -p "$BIN_DIR"
cat > "$CONFIG_CMD" <<EOF
#!/bin/bash
set -euo pipefail
if [ "\${1:-}" = "--cli" ]; then
    shift
    exec python3 "$DEST/configure.py" "\$@"
fi
exec python3 "$DEST/configure_gui.py" "\$@"
EOF
chmod +x "$CONFIG_CMD"

echo "==> Installing floating panel command to $PANEL_CMD"
cat > "$PANEL_CMD" <<EOF
#!/bin/bash
set -euo pipefail
nohup python3 "$DEST/panel.py" "\$@" >/dev/null 2>&1 &
echo "rootless-pinyin panel started."
EOF
chmod +x "$PANEL_CMD"

echo "==> Registering IBus component"
mkdir -p "$HOME/.local/share/ibus/component"
sed "s#__EXEC_PATH__#$DEST/engine.py#" "$SCRIPT_DIR/component/pypinyin.xml.template" \
    > "$HOME/.local/share/ibus/component/pypinyin.xml"

echo "==> Setting IBUS_COMPONENT_PATH for future sessions"
mkdir -p "$HOME/.config/environment.d"
cat > "$HOME/.config/environment.d/ibus-pypinyin.conf" <<EOF
IBUS_COMPONENT_PATH=/usr/share/ibus/component:$HOME/.local/share/ibus/component
EOF
if [ -n "${LIBPINYIN_PATH:-}" ]; then
    printf 'LIBPINYIN_PATH=%s\n' "$LIBPINYIN_PATH" >> "$HOME/.config/environment.d/ibus-pypinyin.conf"
fi
if [ -n "${LIBPINYIN_DATA_DIR:-}" ]; then
    printf 'LIBPINYIN_DATA_DIR=%s\n' "$LIBPINYIN_DATA_DIR" >> "$HOME/.config/environment.d/ibus-pypinyin.conf"
fi

echo "==> Overriding org.freedesktop.IBus D-Bus service to force a cache refresh on start"
mkdir -p "$HOME/.local/share/dbus-1/services"
SYSTEM_SERVICE="/usr/share/dbus-1/services/org.freedesktop.IBus.service"
if [ -f "$USER_SERVICE" ] && [ ! -f "$USER_SERVICE_BACKUP" ]; then
    cp "$USER_SERVICE" "$USER_SERVICE_BACKUP"
    echo "    Backed up existing user D-Bus service to $USER_SERVICE_BACKUP"
fi
if [ -f "$SYSTEM_SERVICE" ]; then
    EXEC_LINE="$(grep '^Exec=' "$SYSTEM_SERVICE" | sed 's/^Exec=//')"
else
    EXEC_LINE="/usr/bin/ibus-daemon --replace --panel disable --xim"
fi
case "$EXEC_LINE" in
    *--cache=*) ;;
    *) EXEC_LINE="$EXEC_LINE --cache=refresh" ;;
esac
cat > "$USER_SERVICE" <<EOF
[D-BUS Service]
Name=org.freedesktop.IBus
Exec=$EXEC_LINE
EOF

echo "==> Adding pypinyin to your GNOME input sources (existing sources are kept)"
if command -v gsettings >/dev/null 2>&1; then
python3 - <<'PYEOF' || true
import subprocess, ast
import sys

try:
    out = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True,
    ).stdout.strip()
    sources = ast.literal_eval(out)
except Exception as exc:
    print("Could not read GNOME input sources; add pypinyin manually:", exc, file=sys.stderr)
    raise SystemExit(0)

entry = ("ibus", "pypinyin")
if entry not in sources:
    sources.append(entry)
    value = "[" + ", ".join(repr(s) for s in sources) + "]"
    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", value],
            check=True,
        )
        print("Added", entry, "to input sources.")
    except Exception as exc:
        print("Could not update GNOME input sources; add pypinyin manually:", exc, file=sys.stderr)
else:
    print("pypinyin already present in input sources.")
PYEOF
else
    echo "    gsettings not found; add 'Pinyin (libpinyin, no-root)' manually."
fi

NEED_RELOGIN=1
echo "==> Trying to refresh the current IBus session"
if command -v ibus-daemon >/dev/null 2>&1; then
    LIVE_COMPONENT_PATH="/usr/share/ibus/component:$HOME/.local/share/ibus/component"
    if IBUS_COMPONENT_PATH="$LIVE_COMPONENT_PATH" ibus-daemon --replace --daemonize --xim --cache=refresh >/dev/null 2>&1; then
        sleep 1
        if command -v ibus >/dev/null 2>&1 && ibus list-engine 2>/dev/null | grep -q 'pypinyin'; then
            echo "    IBus refreshed. pypinyin is available in this session."
            NEED_RELOGIN=0
        else
            echo "    IBus restarted, but pypinyin is not visible yet."
        fi
    else
        echo "    Could not restart ibus-daemon automatically."
    fi
else
    echo "    ibus-daemon not found in PATH."
fi

echo
echo "==> Install complete."
if [ "$NEED_RELOGIN" -eq 0 ]; then
    echo "    You can try switching to 'Pinyin (libpinyin, no-root)' now via"
    echo "    Super+Space or the input source indicator."
else
    echo "    If 'Pinyin (libpinyin, no-root)' is not visible yet, log out and"
    echo "    log back in once so ibus-daemon and the D-Bus session bus refresh."
fi
case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo
        echo "    Note: $BIN_DIR is not in your PATH."
        echo "    Open settings with: $CONFIG_CMD"
        echo "    Open panel with:    $PANEL_CMD"
        ;;
esac

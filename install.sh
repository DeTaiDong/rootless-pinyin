#!/bin/bash
# Installs the pypinyin IBus engine for the current user, no root required.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.local/share/ibus-pypinyin"

echo "==> Checking prerequisites"
if [ ! -f /usr/lib64/libpinyin.so.13 ]; then
    echo "ERROR: /usr/lib64/libpinyin.so.13 not found." >&2
    echo "       This machine doesn't have libpinyin installed system-wide; ask an admin" >&2
    echo "       to install the 'libpinyin' and 'libpinyin-data' packages (or 'ibus-libpinyin')." >&2
    exit 1
fi
if [ ! -d /usr/lib64/libpinyin/data ]; then
    echo "ERROR: /usr/lib64/libpinyin/data not found (libpinyin-data package missing)." >&2
    exit 1
fi
if ! python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus" 2>/dev/null; then
    echo "ERROR: python3 IBus GObject Introspection bindings not available." >&2
    echo "       Need python3-gobject and the ibus typelib installed system-wide." >&2
    exit 1
fi

echo "==> Installing engine files to $DEST"
mkdir -p "$DEST"
cp "$SCRIPT_DIR/src/engine.py" "$SCRIPT_DIR/src/pinyin_lib.py" "$DEST/"
chmod +x "$DEST/engine.py"

echo "==> Registering IBus component"
mkdir -p "$HOME/.local/share/ibus/component"
sed "s#__EXEC_PATH__#$DEST/engine.py#" "$SCRIPT_DIR/component/pypinyin.xml.template" \
    > "$HOME/.local/share/ibus/component/pypinyin.xml"

echo "==> Setting IBUS_COMPONENT_PATH for future sessions"
mkdir -p "$HOME/.config/environment.d"
cat > "$HOME/.config/environment.d/ibus-pypinyin.conf" <<EOF
IBUS_COMPONENT_PATH=/usr/share/ibus/component:$HOME/.local/share/ibus/component
EOF

echo "==> Overriding org.freedesktop.IBus D-Bus service to force a cache refresh on start"
mkdir -p "$HOME/.local/share/dbus-1/services"
SYSTEM_SERVICE="/usr/share/dbus-1/services/org.freedesktop.IBus.service"
if [ -f "$SYSTEM_SERVICE" ]; then
    EXEC_LINE="$(grep '^Exec=' "$SYSTEM_SERVICE" | sed 's/^Exec=//')"
else
    EXEC_LINE="/usr/bin/ibus-daemon --replace --panel disable --xim"
fi
case "$EXEC_LINE" in
    *--cache=*) ;;
    *) EXEC_LINE="$EXEC_LINE --cache=refresh" ;;
esac
cat > "$HOME/.local/share/dbus-1/services/org.freedesktop.IBus.service" <<EOF
[D-BUS Service]
Name=org.freedesktop.IBus
Exec=$EXEC_LINE
EOF

echo "==> Adding pypinyin to your GNOME input sources (existing sources are kept)"
python3 - <<'PYEOF'
import subprocess, ast

out = subprocess.run(
    ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True,
).stdout.strip()
sources = ast.literal_eval(out)
entry = ("ibus", "pypinyin")
if entry not in sources:
    sources.append(entry)
    value = "[" + ", ".join(repr(s) for s in sources) + "]"
    subprocess.run(
        ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", value],
        check=True,
    )
    print("Added", entry, "to input sources.")
else:
    print("pypinyin already present in input sources.")
PYEOF

echo
echo "==> Install complete."
echo "    Log out and log back in once (required so ibus-daemon and the D-Bus"
echo "    session bus pick up the new files), then switch to 'Pinyin (libpinyin,"
echo "    no-root)' via Super+Space or the input source indicator."

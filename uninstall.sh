#!/bin/bash
# Removes the pypinyin IBus engine from the current user's environment.
set -euo pipefail

DEST="$HOME/.local/share/ibus-pypinyin"
COMPONENT="$HOME/.local/share/ibus/component/pypinyin.xml"
ENV_FILE="$HOME/.config/environment.d/ibus-pypinyin.conf"
CONFIG_CMD="$HOME/.local/bin/rootless-pinyin-config"
USER_SERVICE="$HOME/.local/share/dbus-1/services/org.freedesktop.IBus.service"
USER_SERVICE_BACKUP="$USER_SERVICE.pre-pypinyin"

echo "==> Removing installed files"
rm -rf "$DEST" "$COMPONENT" "$ENV_FILE" "$CONFIG_CMD"

echo "==> Restoring D-Bus service override"
if [ -f "$USER_SERVICE_BACKUP" ]; then
    mv "$USER_SERVICE_BACKUP" "$USER_SERVICE"
    echo "    Restored previous user D-Bus service."
elif [ -f "$USER_SERVICE" ]; then
    rm -f "$USER_SERVICE"
    echo "    Removed pypinyin D-Bus service override."
else
    echo "    No user D-Bus service override found."
fi

echo "==> Removing pypinyin from GNOME input sources"
if command -v gsettings >/dev/null 2>&1; then
python3 - <<'PYEOF' || true
import ast
import subprocess
import sys

try:
    out = subprocess.run(
        ["gsettings", "get", "org.gnome.desktop.input-sources", "sources"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True,
    ).stdout.strip()
    sources = ast.literal_eval(out)
except Exception as exc:
    print("Could not read GNOME input sources:", exc, file=sys.stderr)
    raise SystemExit(0)

entry = ("ibus", "pypinyin")
new_sources = [source for source in sources if source != entry]
if new_sources != sources:
    value = "[" + ", ".join(repr(s) for s in new_sources) + "]"
    try:
        subprocess.run(
            ["gsettings", "set", "org.gnome.desktop.input-sources", "sources", value],
            check=True,
        )
        print("Removed", entry, "from input sources.")
    except Exception as exc:
        print("Could not update GNOME input sources:", exc, file=sys.stderr)
else:
    print("pypinyin was not present in input sources.")
PYEOF
else
    echo "    gsettings not found; remove pypinyin manually if needed."
fi

echo
echo "==> Uninstall complete."
echo "    Log out and log back in once so ibus-daemon and the session bus refresh."

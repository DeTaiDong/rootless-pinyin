#!/bin/bash
# Opens the GTK settings window for rootless-pinyin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/src/configure_gui.py"

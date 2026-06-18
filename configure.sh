#!/bin/bash
# Interactive and command-line configuration for rootless-pinyin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/src/configure.py" "$@"

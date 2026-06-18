#!/bin/bash
# Downloads rootless-pinyin into the user's home directory and runs install.sh.
set -euo pipefail

REPO_URL="${ROOTLESS_PINYIN_REPO:-https://github.com/DeTaiDong/rootless-pinyin.git}"
REF="${ROOTLESS_PINYIN_REF:-main}"
INSTALL_DIR="${ROOTLESS_PINYIN_SRC_DIR:-$HOME/.local/share/rootless-pinyin-src}"

usage() {
    cat <<EOF
Usage: bootstrap.sh [install|--update|--uninstall|--configure]

Environment variables:
  ROOTLESS_PINYIN_REPO     Git repository URL. Default: $REPO_URL
  ROOTLESS_PINYIN_REF      Branch to install. Default: $REF
  ROOTLESS_PINYIN_SRC_DIR  Source checkout directory. Default: $INSTALL_DIR
EOF
}

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: required command not found: $1" >&2
        exit 1
    fi
}

download_file() {
    url="$1"
    output="$2"

    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$output"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$output" "$url"
    else
        echo "ERROR: either curl or wget is required to download rootless-pinyin." >&2
        exit 1
    fi
}

download_with_git() {
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo "==> Updating existing source checkout at $INSTALL_DIR"
        git -C "$INSTALL_DIR" fetch origin "$REF"
        git -C "$INSTALL_DIR" checkout "$REF" >/dev/null 2>&1 || git -C "$INSTALL_DIR" checkout -B "$REF" "origin/$REF"
        git -C "$INSTALL_DIR" pull --ff-only origin "$REF"
        return
    fi

    if [ -e "$INSTALL_DIR" ]; then
        echo "ERROR: $INSTALL_DIR already exists but is not a git checkout." >&2
        echo "       Move it away or set ROOTLESS_PINYIN_SRC_DIR to another path." >&2
        exit 1
    fi

    echo "==> Cloning rootless-pinyin into $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    git clone --depth 1 --branch "$REF" "$REPO_URL" "$INSTALL_DIR"
}

download_with_archive() {
    require_cmd tar

    if [ -e "$INSTALL_DIR" ]; then
        echo "ERROR: $INSTALL_DIR already exists and git is unavailable for updating it." >&2
        echo "       Install git, move that directory away, or set ROOTLESS_PINYIN_SRC_DIR." >&2
        exit 1
    fi

    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT

    archive_url="https://github.com/DeTaiDong/rootless-pinyin/archive/refs/heads/$REF.tar.gz"
    archive="$tmp_dir/rootless-pinyin.tar.gz"

    echo "==> Downloading rootless-pinyin archive"
    download_file "$archive_url" "$archive"

    echo "==> Extracting source into $INSTALL_DIR"
    mkdir -p "$(dirname "$INSTALL_DIR")"
    tar -xzf "$archive" -C "$tmp_dir"
    extracted="$(find "$tmp_dir" -maxdepth 1 -type d -name 'rootless-pinyin-*' | head -n 1)"
    if [ -z "$extracted" ]; then
        echo "ERROR: downloaded archive did not contain rootless-pinyin sources." >&2
        exit 1
    fi
    mv "$extracted" "$INSTALL_DIR"
}

ensure_source() {
    if command -v git >/dev/null 2>&1; then
        download_with_git
    else
        download_with_archive
    fi
}

run_install() {
    ensure_source
    echo "==> Running installer"
    "$INSTALL_DIR/install.sh"
}

run_uninstall() {
    if [ -x "$INSTALL_DIR/uninstall.sh" ]; then
        "$INSTALL_DIR/uninstall.sh"
    else
        echo "ERROR: uninstall.sh not found at $INSTALL_DIR." >&2
        echo "       Re-run bootstrap install first, or uninstall manually from README." >&2
        exit 1
    fi
}

run_configure() {
    ensure_source
    if [ -x "$INSTALL_DIR/configure.sh" ]; then
        if [ "$#" -eq 1 ] && [ ! -t 0 ] && [ -r /dev/tty ]; then
            "$INSTALL_DIR/configure.sh" </dev/tty
        else
            "$INSTALL_DIR/configure.sh" "${@:2}"
        fi
    else
        echo "ERROR: configure.sh not found at $INSTALL_DIR." >&2
        exit 1
    fi
}

case "${1:-install}" in
    install)
        run_install
        ;;
    --update|update)
        run_install
        ;;
    --uninstall|uninstall)
        run_uninstall
        ;;
    --configure|configure)
        run_configure "$@"
        ;;
    -h|--help|help)
        usage
        ;;
    *)
        usage >&2
        exit 1
        ;;
esac

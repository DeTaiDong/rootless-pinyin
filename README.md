# rootless-pinyin

A pure-Python IBus pinyin input engine for Linux desktops where you don't
have root, but the system already ships `libpinyin` (common on RHEL/Rocky/
CentOS desktop installs, where `libpinyin` + `libpinyin-data` get pulled in
as a dependency of something else even though the `ibus-libpinyin` RPM
itself was never installed).

It talks directly to the system's `libpinyin.so` via `ctypes` and registers
itself as a **user-level** IBus engine under `~/.local/share` — no `sudo`
required.

## Requirements

Check these before installing:

- `libpinyin` and its data files already exist on the machine:
  ```bash
  rpm -qa | grep libpinyin
  ```
  If missing, this won't work until an admin installs `libpinyin` and
  `libpinyin-data` (or properly installs `ibus-libpinyin`).
  The installer checks common library/data locations automatically. If your
  distro uses a custom path, run install with:
  ```bash
  LIBPINYIN_PATH=/path/to/libpinyin.so \
  LIBPINYIN_DATA_DIR=/path/to/libpinyin/data \
  ./install.sh
  ```
- IBus + PyGObject bindings are present:
  ```bash
  python3 -c "import gi; gi.require_version('IBus','1.0'); from gi.repository import IBus"
  ```
  This should run with no output/errors.
- A GNOME (or other ibus-integrated) desktop session.

## Install

```bash
git clone <your-repo-url> rootless-pinyin
cd rootless-pinyin
./install.sh
```

Then **log out and log back in once**. This is required so that
`ibus-daemon` and the session D-Bus broker both start fresh and pick up
the newly installed files (see "Why a relogin is needed" below). You do
not need to relogin again on subsequent boots.

After logging back in:

1. Settings → Keyboard → Input Sources should already list
   **"Pinyin (libpinyin, no-root)"** (added automatically by `install.sh`).
   If it's missing, add it manually: **+** → Chinese → Pinyin (libpinyin,
   no-root).
2. Switch to it with `Super+Space` or the input source indicator in the
   top bar.
3. Type pinyin in any text field, e.g. `nihao`, then `Space`/`Enter` to
   commit the best guess, or a number key (`2`-`9`) to pick an alternate
   candidate for the current word. `Backspace` edits, `Esc` cancels.

## What `install.sh` does

- Copies `engine.py` + `pinyin_lib.py` to `~/.local/share/ibus-pypinyin/`
- Registers the engine as an IBus component at
  `~/.local/share/ibus/component/pypinyin.xml`
- Sets `IBUS_COMPONENT_PATH` via
  `~/.config/environment.d/ibus-pypinyin.conf`, because this distro's
  `ibus-daemon` does not scan the user component directory by default. If
  `LIBPINYIN_PATH` or `LIBPINYIN_DATA_DIR` were provided during install,
  they are persisted there too.
- Overrides the `org.freedesktop.IBus` D-Bus session service at
  `~/.local/share/dbus-1/services/` to add `--cache=refresh`, since the
  default "auto" cache mode can keep serving a stale component registry
  that doesn't include user-added engines. If you already had a user-level
  override, `install.sh` backs it up as
  `org.freedesktop.IBus.service.pre-pypinyin`.
- Adds `('ibus', 'pypinyin')` to your GNOME input source list
  (`org.gnome.desktop.input-sources`), without touching your existing
  sources. On non-GNOME sessions, this step is skipped and you can add the
  engine manually.

## Why a relogin is needed

Two separate things cache state at startup and don't hot-reload:

- `ibus-daemon` caches the scanned component registry (`~/.cache/ibus/bus/registry`).
- The session D-Bus broker caches the list of activatable `.service` files
  at the time it starts.

Both need to start fresh once, after the files above exist, to pick up
`pypinyin`. Once that's happened, it keeps working across reboots/logins
without any further action.

## Troubleshooting

- `ibus engine pypinyin` says `Cannot find engine pypinyin` → log out/in
  once more.
- No candidates while typing, or the engine doesn't seem to start → check
  `~/.local/share/ibus-pypinyin/engine.py` is executable, and rerun the
  PyGObject/IBus check above.
- Garbled or missing Chinese candidates → confirm the libpinyin data
  directory contains readable `*.bin` files. For custom installs, set
  `LIBPINYIN_DATA_DIR` before running `install.sh`.

## Uninstall

```bash
./uninstall.sh
```

Then log out/in. On GNOME, the script also removes `('ibus', 'pypinyin')`
from your input sources. If a pre-existing user D-Bus service override was
backed up during install, it is restored.

## Limitations

This is a minimal engine, not a drop-in replacement for `ibus-libpinyin`:
no fuzzy-pinyin settings UI, no cloud pinyin, simplified self-learning.
It does do full-sentence smart segmentation (e.g. `woshizhongguoren` →
我是中国人) using the real libpinyin library and dictionary data.

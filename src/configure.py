#!/usr/bin/python3
"""Command-line configurator for rootless-pinyin."""

import configparser
import os
import sys

from config import CONFIG_PATH, UserConfig


def _parser():
    UserConfig.load()
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(CONFIG_PATH)
    for section in ("general", "fuzzy", "phrases"):
        if not parser.has_section(section):
            parser.add_section(section)
    return parser


def _save(parser):
    with open(CONFIG_PATH, "w") as f:
        parser.write(f)


def _set_fuzzy(value):
    parser = _parser()
    parser.set("fuzzy", "enabled", "true" if value else "false")
    _save(parser)
    print("Fuzzy pinyin:", "on" if value else "off")


def _add_phrase(key, value):
    key = key.strip().lower()
    value = value.strip()
    if not key or not value:
        raise SystemExit("phrase key and value cannot be empty")
    parser = _parser()
    parser.set("phrases", key, value)
    _save(parser)
    print("Added phrase:", key, "=", value)


def _remove_phrase(key):
    parser = _parser()
    removed = parser.remove_option("phrases", key.strip().lower())
    _save(parser)
    print("Removed phrase:" if removed else "Phrase not found:", key)


def _show():
    UserConfig.load()
    with open(CONFIG_PATH) as f:
        print(f.read().rstrip())


def _prompt(question, default=""):
    suffix = " [%s]" % default if default else ""
    value = input(question + suffix + ": ").strip()
    return value or default


def _interactive():
    print("rootless-pinyin config")
    print("Config file:", CONFIG_PATH)
    parser = _parser()

    current = parser.getboolean("fuzzy", "enabled", fallback=False)
    answer = _prompt("Enable fuzzy pinyin? (y/n)", "y" if current else "n").lower()
    if answer in ("y", "yes"):
        parser.set("fuzzy", "enabled", "true")
    elif answer in ("n", "no"):
        parser.set("fuzzy", "enabled", "false")

    print()
    print("Add custom phrases. Press Enter on an empty key to finish.")
    while True:
        key = input("Phrase key: ").strip().lower()
        if not key:
            break
        value = input("Phrase text: ").strip()
        if value:
            parser.set("phrases", key, value)

    _save(parser)
    print()
    print("Saved. Switch input method once or run update to refresh IBus.")


def _usage():
    print("""Usage:
  configure.sh
  configure.sh show
  configure.sh fuzzy on|off
  configure.sh phrase add KEY TEXT...
  configure.sh phrase remove KEY
""".rstrip())


def main(argv):
    if not argv:
        _interactive()
        return

    if argv[0] in ("-h", "--help", "help"):
        _usage()
    elif argv[0] == "show":
        _show()
    elif argv[0] == "fuzzy" and len(argv) == 2 and argv[1] in ("on", "off"):
        _set_fuzzy(argv[1] == "on")
    elif argv[0] == "phrase" and len(argv) >= 4 and argv[1] == "add":
        _add_phrase(argv[2], " ".join(argv[3:]))
    elif argv[0] == "phrase" and len(argv) == 3 and argv[1] in ("remove", "rm", "delete"):
        _remove_phrase(argv[2])
    else:
        _usage()
        raise SystemExit(1)


if __name__ == "__main__":
    main(sys.argv[1:])

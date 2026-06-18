"""User configuration for rootless-pinyin."""

import configparser
import os

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "rootless-pinyin")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.ini")

DEFAULT_CONFIG = """# rootless-pinyin user config

[general]
page_size = 9
max_candidates = 90
shift_toggle_english = true
chinese_punctuation = true
enter_commits_raw = true
theme = system

[fuzzy]
enabled = false
pairs = z_zh,c_ch,s_sh,l_n,f_h,en_eng,in_ing
max_variants = 8

[floating]
opacity = 0.9
theme = system

[phrases]
# Custom phrases. Left side is pinyin or shortcode, right side is the text.
# Examples:
# email = your.name@example.com
# addr = Your address
# xiexie = 谢谢
"""

FUZZY_PAIR_MAP = {
    "z_zh": ("z", "zh"),
    "c_ch": ("c", "ch"),
    "s_sh": ("s", "sh"),
    "l_n": ("l", "n"),
    "f_h": ("f", "h"),
    "en_eng": ("en", "eng"),
    "in_ing": ("in", "ing"),
}


def _bool(parser, section, option, fallback):
    return parser.getboolean(section, option, fallback=fallback)


def _int(parser, section, option, fallback, minimum=None, maximum=None):
    value = parser.getint(section, option, fallback=fallback)
    if minimum is not None:
        value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


class UserConfig(object):
    def __init__(self):
        self.path = CONFIG_PATH
        self.page_size = 9
        self.max_candidates = 90
        self.shift_toggle_english = True
        self.chinese_punctuation = True
        self.enter_commits_raw = True
        self.theme = "system"
        self.fuzzy_enabled = False
        self.fuzzy_pairs = []
        self.max_fuzzy_variants = 8
        self.phrases = {}
        self.floating_opacity = 0.9
        self.floating_theme = "system"

    @classmethod
    def load(cls):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w") as f:
                f.write(DEFAULT_CONFIG)

        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(CONFIG_PATH)

        config = cls()
        config.page_size = _int(parser, "general", "page_size", 9, 1, 9)
        config.max_candidates = _int(parser, "general", "max_candidates", 90, 9, 200)
        config.shift_toggle_english = _bool(parser, "general", "shift_toggle_english", True)
        config.chinese_punctuation = _bool(parser, "general", "chinese_punctuation", True)
        config.enter_commits_raw = _bool(parser, "general", "enter_commits_raw", True)
        config.theme = parser.get("general", "theme", fallback="system")
        if config.theme not in ("system", "light", "dark"):
            config.theme = "system"
        config.fuzzy_enabled = _bool(parser, "fuzzy", "enabled", False)
        config.max_fuzzy_variants = _int(parser, "fuzzy", "max_variants", 8, 0, 32)

        pair_names = parser.get("fuzzy", "pairs", fallback="")
        config.fuzzy_pairs = [
            FUZZY_PAIR_MAP[name.strip()]
            for name in pair_names.split(",")
            if name.strip() in FUZZY_PAIR_MAP
        ]

        if parser.has_section("phrases"):
            config.phrases = {
                key.strip().lower(): value.strip()
                for key, value in parser.items("phrases")
                if key.strip() and value.strip()
            }

        config.floating_opacity = parser.getfloat("floating", "opacity", fallback=0.9)
        config.floating_opacity = min(1.0, max(0.3, config.floating_opacity))
        config.floating_theme = parser.get("floating", "theme", fallback="system")
        if config.floating_theme not in ("system", "light", "dark"):
            config.floating_theme = "system"

        return config


def fuzzy_variants(raw, pairs, limit):
    if not raw or not pairs or limit <= 0:
        return []

    variants = []
    seen = {raw}
    for left, right in pairs:
        if right in raw:
            replacements = ((right, left),)
        elif left in raw:
            replacements = ((left, right),)
        else:
            replacements = ()

        for old, new in replacements:
            variant = raw.replace(old, new)
            if variant in seen:
                continue
            seen.add(variant)
            variants.append(variant)
            if len(variants) >= limit:
                return variants
    return variants

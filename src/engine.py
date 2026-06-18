#!/usr/bin/python3
"""User-level IBus pinyin engine backed by the system libpinyin.so via ctypes.

Registered under $XDG_DATA_HOME/ibus/component so it runs without root.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("IBus", "1.0")
from gi.repository import GLib, IBus

from config import UserConfig, fuzzy_variants
from pinyin_lib import PinyinSession

USER_DATA_DIR = os.path.join(GLib.get_user_cache_dir(), "ibus-pypinyin")

CHINESE_PUNCTUATION = {
    ",": "，",
    ".": "。",
    "?": "？",
    "!": "！",
    ":": "：",
    ";": "；",
    "(": "（",
    ")": "）",
    "[": "【",
    "]": "】",
    "<": "《",
    ">": "》",
    "\\": "、",
}


class PyPinyinEngine(IBus.Engine):
    __gtype_name__ = "PyPinyinEngine"

    def __init__(self):
        super(PyPinyinEngine, self).__init__()
        os.makedirs(USER_DATA_DIR, exist_ok=True)
        self.config = UserConfig.load()
        self.session = PinyinSession(USER_DATA_DIR)
        self.buffer = ""
        self.primary_candidate = None
        self.candidates = []
        self.page = 0
        self.english_mode = False
        self._status_timeout = 0
        self._shift_pressed = False
        self._shift_used = False

    def _is_letter(self, keyval):
        return (IBus.KEY_a <= keyval <= IBus.KEY_z) or (IBus.KEY_A <= keyval <= IBus.KEY_Z)

    def _key_char(self, keyval):
        if 0x20 <= keyval <= 0x7e:
            return chr(keyval)
        return ""

    def _is_shift(self, keyval):
        return keyval in (IBus.KEY_Shift_L, IBus.KEY_Shift_R)

    def _is_pinyin_separator(self, keyval):
        return self._key_char(keyval) == "'"

    def _append_separator(self):
        if not self.buffer or self.buffer.endswith("'"):
            return False
        self.buffer += "'"
        self.page = 0
        self._refresh()
        return True

    def _flash_status(self, text):
        if self._status_timeout:
            GLib.source_remove(self._status_timeout)
        self.update_auxiliary_text(IBus.Text.new_from_string(text), True)
        self._status_timeout = GLib.timeout_add(1200, self._hide_status)

    def _hide_status(self):
        self._status_timeout = 0
        if not self.buffer:
            self.hide_auxiliary_text()
        return False

    def _toggle_english_mode(self):
        if self.buffer:
            self._commit_best_and_reset()
        self.english_mode = not self.english_mode
        self._clear_ui()
        self._flash_status("英文模式" if self.english_mode else "拼音模式")

    def _phrase_candidates(self):
        out = []
        for key, text in self.config.phrases.items():
            if self.buffer == key:
                consume = len(key)
            elif self.buffer.startswith(key + "'"):
                consume = len(key) + 1
            else:
                continue
            out.append({"text": text, "ptr": None, "consume": consume, "train": False})
        return out

    def _fuzzy_candidates(self, sentence):
        if not self.config.fuzzy_enabled:
            return []

        out = []
        seen = {sentence}
        for variant in fuzzy_variants(
            self.buffer, self.config.fuzzy_pairs, self.config.max_fuzzy_variants
        ):
            self.session.parse(variant)
            best = self.session.best_sentence()
            if best and best not in seen:
                seen.add(best)
                out.append({"text": best, "ptr": None, "consume": len(self.buffer), "train": False})
            for text, _ptr in self.session.candidates(0, limit=5):
                if text and text not in seen:
                    seen.add(text)
                    out.append({"text": text, "ptr": None, "consume": len(self.buffer), "train": False})
                if len(out) >= 12:
                    return out
        return out

    def _refresh(self):
        self.session.parse(self.buffer)
        sentence_text = self.session.best_sentence() or self.buffer
        sentence = {
            "text": sentence_text,
            "ptr": None,
            "consume": len(self.buffer),
            "train": True,
        }
        phrase_candidates = self._phrase_candidates()
        exact_phrases = [c for c in phrase_candidates if c["consume"] >= len(self.buffer)]
        prefix_phrases = [c for c in phrase_candidates if c["consume"] < len(self.buffer)]

        self.primary_candidate = exact_phrases[0] if exact_phrases else sentence
        fuzzy = self._fuzzy_candidates(sentence_text)
        self.session.parse(self.buffer)
        normal = [
            {"text": text, "ptr": ptr, "consume": None, "train": True}
            for text, ptr in self.session.candidates(0, limit=self.config.max_candidates)
            if text != sentence_text and text != self.primary_candidate["text"]
        ]
        remaining_exact = exact_phrases[1:]
        sentence_fallback = [] if self.primary_candidate is sentence else [sentence]
        self.candidates = remaining_exact + prefix_phrases + sentence_fallback + normal + fuzzy
        self.page = min(self.page, self._last_page())
        self._update_candidates(self.primary_candidate["text"])

    def _last_page(self):
        total = 1 + len(self.candidates)
        return max(0, (total - 1) // self.config.page_size)

    def _candidate_for_display_index(self, idx):
        absolute = self.page * self.config.page_size + idx
        if absolute == 0:
            return self.primary_candidate
        real_idx = absolute - 1
        if real_idx >= len(self.candidates):
            return None
        return self.candidates[real_idx]

    def _update_candidates(self, sentence=None):
        sentence = sentence or self.session.best_sentence() or self.buffer

        table = IBus.LookupTable.new(self.config.page_size, 0, True, True)
        table.set_cursor_visible(False)
        for label in ("1", "2", "3", "4", "5", "6", "7", "8", "9")[:self.config.page_size]:
            table.append_label(IBus.Text.new_from_string(label))

        start = self.page * self.config.page_size
        end = start + self.config.page_size
        for absolute in range(start, end):
            if absolute == 0:
                text = sentence
            else:
                real_idx = absolute - 1
                if real_idx >= len(self.candidates):
                    break
                text = self.candidates[real_idx]["text"]
            table.append_candidate(IBus.Text.new_from_string(text))
        self.update_lookup_table(table, True)

        self.update_preedit_text(IBus.Text.new_from_string(self.buffer), len(self.buffer), True)
        self.update_auxiliary_text(
            IBus.Text.new_from_string(
                "%s  →  %s    %d/%d"
                % (self.buffer, sentence, self.page + 1, self._last_page() + 1)
            ),
            True,
        )

    def _clear_ui(self):
        if self._status_timeout:
            GLib.source_remove(self._status_timeout)
            self._status_timeout = 0
        self.hide_preedit_text()
        self.hide_lookup_table()
        self.hide_auxiliary_text()
        self.primary_candidate = None
        self.candidates = []
        self.page = 0

    def _reset_state(self):
        self.buffer = ""
        self.page = 0
        self.session.reset()
        self._clear_ui()

    def _commit(self, text):
        self.commit_text(IBus.Text.new_from_string(text))

    def _commit_best_and_reset(self):
        selected = self.primary_candidate or {
            "text": self.session.best_sentence() or self.buffer,
            "ptr": None,
            "consume": len(self.buffer),
            "train": True,
        }
        self._commit_candidate(selected)

    def _commit_raw_and_reset(self):
        self._commit(self.buffer)
        self._reset_state()

    def _select_candidate(self, idx):
        selected = self._candidate_for_display_index(idx)
        if not selected:
            return
        self._commit_candidate(selected)

    def _commit_candidate(self, selected):
        text = selected["text"]
        ptr = selected["ptr"]
        consume = selected["consume"]
        if ptr is not None:
            consume = self.session.choose(0, ptr)
        elif selected["train"]:
            self.session.train()
        self._commit(text)
        self.buffer = self.buffer[consume or len(self.buffer):]
        self.session.reset()
        self.page = 0
        if self.buffer:
            self._refresh()
        else:
            self._clear_ui()

    def _page_down(self):
        if self.page >= self._last_page():
            return True
        self.page += 1
        self._update_candidates()
        return True

    def _page_up(self):
        if self.page <= 0:
            return True
        self.page -= 1
        self._update_candidates()
        return True

    def do_process_key_event(self, keyval, keycode, state):
        if self.config.shift_toggle_english and self._is_shift(keyval):
            if state & IBus.ModifierType.RELEASE_MASK:
                should_toggle = self._shift_pressed and not self._shift_used
                self._shift_pressed = False
                self._shift_used = False
                if should_toggle:
                    self._toggle_english_mode()
                    return True
                return False
            self._shift_pressed = True
            self._shift_used = False
            return False

        if state & IBus.ModifierType.RELEASE_MASK:
            return False

        if self._shift_pressed and (state & IBus.ModifierType.SHIFT_MASK):
            self._shift_used = True

        if self.english_mode:
            return False

        if state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK
                    | IBus.ModifierType.SUPER_MASK):
            if self.buffer:
                self._commit_best_and_reset()
            return False

        if self._is_letter(keyval):
            self.buffer += chr(keyval).lower()
            self.page = 0
            self._refresh()
            return True

        if self._is_pinyin_separator(keyval):
            return self._append_separator()

        if keyval == IBus.KEY_BackSpace:
            if not self.buffer:
                return False
            self.buffer = self.buffer[:-1]
            self.session.reset()
            self.page = 0
            if self.buffer:
                self._refresh()
            else:
                self._clear_ui()
            return True

        if keyval in (IBus.KEY_space, IBus.KEY_KP_Space):
            if not self.buffer:
                return False
            self._commit_best_and_reset()
            return True

        if keyval in (IBus.KEY_Return, IBus.KEY_KP_Enter):
            if not self.buffer:
                return False
            if self.config.enter_commits_raw:
                self._commit_raw_and_reset()
            else:
                self._commit_best_and_reset()
            return True

        if keyval == IBus.KEY_Escape:
            if not self.buffer:
                return False
            self._reset_state()
            return True

        if IBus.KEY_1 <= keyval <= IBus.KEY_9:
            if not self.buffer:
                return False
            idx = keyval - IBus.KEY_1
            if idx < self.config.page_size:
                self._select_candidate(idx)
            return True

        if keyval in (
            IBus.KEY_Page_Down, IBus.KEY_KP_Page_Down,
            IBus.KEY_Down, IBus.KEY_Right, IBus.KEY_KP_Down, IBus.KEY_KP_Right,
        ) or self._key_char(keyval) == "=":
            return self._page_down() if self.buffer else False

        if keyval in (
            IBus.KEY_Page_Up, IBus.KEY_KP_Page_Up,
            IBus.KEY_Up, IBus.KEY_Left, IBus.KEY_KP_Up, IBus.KEY_KP_Left,
        ) or self._key_char(keyval) == "-":
            return self._page_up() if self.buffer else False

        if self.buffer:
            self._commit_best_and_reset()

        char = self._key_char(keyval)
        if self.config.chinese_punctuation and char in CHINESE_PUNCTUATION:
            self._commit(CHINESE_PUNCTUATION[char])
            return True
        return False

    def do_focus_out(self):
        if self.buffer:
            self._reset_state()

    def do_reset(self):
        self._reset_state()

    def do_disable(self):
        if self.buffer:
            self._reset_state()
        self.session.save()

    def do_destroy(self):
        self.session.save()
        self.session.close()
        parent_destroy = getattr(super(PyPinyinEngine, self), "do_destroy", None)
        if parent_destroy:
            parent_destroy()

def main():
    mainloop = GLib.MainLoop()
    bus = IBus.Bus()
    if not bus.is_connected():
        sys.stderr.write("ibus-pypinyin: could not connect to ibus-daemon\n")
        sys.exit(1)
    bus.connect("disconnected", lambda _b: mainloop.quit())

    factory = IBus.Factory.new(bus.get_connection())
    factory.add_engine("pypinyin", PyPinyinEngine.__gtype__)
    bus.request_name("org.freedesktop.IBus.PyPinyin", 0)

    mainloop.run()


if __name__ == "__main__":
    main()

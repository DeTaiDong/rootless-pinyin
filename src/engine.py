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
        self.session = PinyinSession(USER_DATA_DIR)
        self.buffer = ""
        self.candidates = []
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

    def _refresh(self):
        self.session.parse(self.buffer)
        sentence = self.session.best_sentence() or self.buffer
        self.candidates = [c for c in self.session.candidates(0, limit=9) if c[0] != sentence][:8]

        table = IBus.LookupTable.new(9, 0, True, True)
        table.set_cursor_visible(False)
        for label in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            table.append_label(IBus.Text.new_from_string(label))
        table.append_candidate(IBus.Text.new_from_string(sentence))
        for text, _ptr in self.candidates:
            table.append_candidate(IBus.Text.new_from_string(text))
        self.update_lookup_table(table, True)

        self.update_preedit_text(IBus.Text.new_from_string(self.buffer), len(self.buffer), True)
        self.update_auxiliary_text(
            IBus.Text.new_from_string("%s  →  %s" % (self.buffer, sentence)), True
        )

    def _clear_ui(self):
        if self._status_timeout:
            GLib.source_remove(self._status_timeout)
            self._status_timeout = 0
        self.hide_preedit_text()
        self.hide_lookup_table()
        self.hide_auxiliary_text()
        self.candidates = []

    def _reset_state(self):
        self.buffer = ""
        self.session.reset()
        self._clear_ui()

    def _commit(self, text):
        self.commit_text(IBus.Text.new_from_string(text))

    def _commit_best_and_reset(self):
        sentence = self.session.best_sentence() or self.buffer
        self._commit(sentence)
        self.session.train()
        self._reset_state()

    def _select_candidate(self, idx):
        if idx == 0:
            self._commit_best_and_reset()
            return
        real_idx = idx - 1
        if real_idx >= len(self.candidates):
            return
        text, ptr = self.candidates[real_idx]
        new_offset = self.session.choose(0, ptr)
        self._commit(text)
        self.buffer = self.buffer[new_offset:]
        self.session.reset()
        if self.buffer:
            self._refresh()
        else:
            self._clear_ui()

    def do_process_key_event(self, keyval, keycode, state):
        if self._is_shift(keyval):
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
            self._refresh()
            return True

        if self._is_pinyin_separator(keyval):
            return self._append_separator()

        if keyval == IBus.KEY_BackSpace:
            if not self.buffer:
                return False
            self.buffer = self.buffer[:-1]
            self.session.reset()
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
            self._select_candidate(keyval - IBus.KEY_1)
            return True

        if keyval in (IBus.KEY_Up, IBus.KEY_Down, IBus.KEY_Page_Up, IBus.KEY_Page_Down):
            return bool(self.buffer)

        if self.buffer:
            self._commit_best_and_reset()

        char = self._key_char(keyval)
        if char in CHINESE_PUNCTUATION:
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

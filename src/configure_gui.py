#!/usr/bin/python3
"""GTK settings window for rootless-pinyin."""

import configparser
import os
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import CONFIG_PATH, UserConfig


FUZZY_LABELS = (
    ("z_zh", "z / zh"),
    ("c_ch", "c / ch"),
    ("s_sh", "s / sh"),
    ("l_n", "l / n"),
    ("f_h", "f / h"),
    ("en_eng", "en / eng"),
    ("in_ing", "in / ing"),
)


def load_parser():
    UserConfig.load()
    parser = configparser.ConfigParser()
    parser.optionxform = str
    parser.read(CONFIG_PATH)
    for section in ("general", "fuzzy", "phrases"):
        if not parser.has_section(section):
            parser.add_section(section)
    return parser


def save_parser(parser):
    with open(CONFIG_PATH, "w") as f:
        parser.write(f)


def bool_value(parser, section, option, fallback=False):
    return parser.getboolean(section, option, fallback=fallback)


class SettingsWindow(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="rootless-pinyin 设置")
        self.set_border_width(14)
        self.set_default_size(520, 430)

        self.parser = load_parser()
        self._apply_theme()

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.add(outer)

        notebook = Gtk.Notebook()
        outer.pack_start(notebook, True, True, 0)

        notebook.append_page(self._general_page(), Gtk.Label(label="常规"))
        notebook.append_page(self._fuzzy_page(), Gtk.Label(label="模糊音"))
        notebook.append_page(self._phrases_page(), Gtk.Label(label="自定义短语"))

        hint = Gtk.Label(
            label="保存后切换一下输入法，或重新运行 update 刷新 IBus。",
            xalign=0,
        )
        outer.pack_start(hint, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)
        outer.pack_start(actions, False, False, 0)

        save = Gtk.Button(label="保存")
        save.connect("clicked", self._on_save)
        actions.pack_start(save, False, False, 0)

        close = Gtk.Button(label="关闭")
        close.connect("clicked", lambda _button: self.destroy())
        actions.pack_start(close, False, False, 0)

    def _switch(self, label, active):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        text = Gtk.Label(label=label, xalign=0)
        switch = Gtk.Switch()
        switch.set_active(active)
        row.pack_start(text, True, True, 0)
        row.pack_start(switch, False, False, 0)
        return row, switch

    def _general_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=12)

        row, self.shift_switch = self._switch(
            "轻按 Shift 切换英文模式",
            bool_value(self.parser, "general", "shift_toggle_english", True),
        )
        box.pack_start(row, False, False, 0)

        row, self.punctuation_switch = self._switch(
            "中文标点",
            bool_value(self.parser, "general", "chinese_punctuation", True),
        )
        box.pack_start(row, False, False, 0)

        row, self.enter_switch = self._switch(
            "Enter 上屏原始拼音",
            bool_value(self.parser, "general", "enter_commits_raw", True),
        )
        box.pack_start(row, False, False, 0)

        grid = Gtk.Grid(column_spacing=12, row_spacing=10)
        box.pack_start(grid, False, False, 0)

        self.page_spin = Gtk.SpinButton()
        self.page_spin.set_range(1, 9)
        self.page_spin.set_increments(1, 1)
        self.page_spin.set_value(self.parser.getint("general", "page_size", fallback=9))
        grid.attach(Gtk.Label(label="每页候选数", xalign=0), 0, 0, 1, 1)
        grid.attach(self.page_spin, 1, 0, 1, 1)

        self.max_spin = Gtk.SpinButton()
        self.max_spin.set_range(9, 200)
        self.max_spin.set_increments(9, 18)
        self.max_spin.set_value(self.parser.getint("general", "max_candidates", fallback=90))
        grid.attach(Gtk.Label(label="最多候选数", xalign=0), 0, 1, 1, 1)
        grid.attach(self.max_spin, 1, 1, 1, 1)

        self.theme_combo = Gtk.ComboBoxText()
        for key, label in (("system", "跟随系统"), ("light", "白天"), ("dark", "夜间")):
            self.theme_combo.append(key, label)
        self.theme_combo.set_active_id(self.parser.get("general", "theme", fallback="system"))
        self.theme_combo.connect("changed", lambda _combo: self._apply_theme_from_combo())
        grid.attach(Gtk.Label(label="设置窗口主题", xalign=0), 0, 2, 1, 1)
        grid.attach(self.theme_combo, 1, 2, 1, 1)

        note = Gtk.Label(
            label="提示：候选框外观由 IBus/桌面主题控制，这里主要调整设置窗口主题。",
            xalign=0,
        )
        note.set_line_wrap(True)
        box.pack_start(note, False, False, 0)

        return box

    def _fuzzy_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, border_width=12)

        row, self.fuzzy_switch = self._switch(
            "开启模糊音",
            bool_value(self.parser, "fuzzy", "enabled", False),
        )
        box.pack_start(row, False, False, 0)

        current = set(
            name.strip()
            for name in self.parser.get("fuzzy", "pairs", fallback="").split(",")
            if name.strip()
        )
        self.fuzzy_checks = {}
        grid = Gtk.Grid(column_spacing=16, row_spacing=8)
        box.pack_start(grid, False, False, 0)
        for i, (key, label) in enumerate(FUZZY_LABELS):
            check = Gtk.CheckButton(label=label)
            check.set_active(key in current)
            self.fuzzy_checks[key] = check
            grid.attach(check, i % 2, i // 2, 1, 1)

        self.fuzzy_spin = Gtk.SpinButton()
        self.fuzzy_spin.set_range(0, 32)
        self.fuzzy_spin.set_increments(1, 4)
        self.fuzzy_spin.set_value(self.parser.getint("fuzzy", "max_variants", fallback=8))
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.pack_start(Gtk.Label(label="模糊候选补充数量", xalign=0), True, True, 0)
        row.pack_start(self.fuzzy_spin, False, False, 0)
        box.pack_start(row, False, False, 0)

        return box

    def _phrases_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, border_width=12)

        self.phrase_store = Gtk.ListStore(str, str)
        for key, value in self.parser.items("phrases"):
            if key.strip() and value.strip():
                self.phrase_store.append([key, value])

        view = Gtk.TreeView(model=self.phrase_store)
        for idx, title in enumerate(("短码", "内容")):
            renderer = Gtk.CellRendererText()
            renderer.set_property("editable", True)
            renderer.connect("edited", self._on_phrase_edited, idx)
            column = Gtk.TreeViewColumn(title, renderer, text=idx)
            column.set_resizable(True)
            view.append_column(column)
        self.phrase_view = view

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.add(view)
        box.pack_start(scroller, True, True, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(actions, False, False, 0)
        add = Gtk.Button(label="添加")
        add.connect("clicked", self._add_phrase)
        actions.pack_start(add, False, False, 0)
        remove = Gtk.Button(label="删除")
        remove.connect("clicked", self._remove_phrase)
        actions.pack_start(remove, False, False, 0)

        return box

    def _on_phrase_edited(self, _renderer, path, text, column):
        self.phrase_store[path][column] = text.strip()

    def _add_phrase(self, _button):
        self.phrase_store.append(["", ""])

    def _remove_phrase(self, _button):
        selection = self.phrase_view.get_selection()
        model, treeiter = selection.get_selected()
        if treeiter:
            model.remove(treeiter)

    def _apply_theme_from_combo(self):
        self._apply_theme(self.theme_combo.get_active_id())

    def _apply_theme(self, theme=None):
        theme = theme or self.parser.get("general", "theme", fallback="system")
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", theme == "dark")

    def _on_save(self, _button):
        self.parser.set("general", "shift_toggle_english", str(self.shift_switch.get_active()).lower())
        self.parser.set("general", "chinese_punctuation", str(self.punctuation_switch.get_active()).lower())
        self.parser.set("general", "enter_commits_raw", str(self.enter_switch.get_active()).lower())
        self.parser.set("general", "page_size", str(self.page_spin.get_value_as_int()))
        self.parser.set("general", "max_candidates", str(self.max_spin.get_value_as_int()))
        self.parser.set("general", "theme", self.theme_combo.get_active_id() or "system")

        self.parser.set("fuzzy", "enabled", str(self.fuzzy_switch.get_active()).lower())
        pairs = [key for key, check in self.fuzzy_checks.items() if check.get_active()]
        self.parser.set("fuzzy", "pairs", ",".join(pairs))
        self.parser.set("fuzzy", "max_variants", str(self.fuzzy_spin.get_value_as_int()))

        self.parser.remove_section("phrases")
        self.parser.add_section("phrases")
        for row in self.phrase_store:
            key = row[0].strip().lower()
            value = row[1].strip()
            if key and value:
                self.parser.set("phrases", key, value)

        save_parser(self.parser)
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="已保存设置",
        )
        dialog.format_secondary_text("切换一下输入法或重新运行 update 后生效。")
        dialog.run()
        dialog.destroy()


def main():
    win = SettingsWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Could not open settings window:", exc, file=sys.stderr)
        raise

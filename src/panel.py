#!/usr/bin/python3
"""Small optional floating panel for rootless-pinyin."""

import os
import subprocess
import sys

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import UserConfig


class FloatingPanel(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="rootless-pinyin")
        self.config = UserConfig.load()

        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.set_border_width(6)
        self.set_opacity(self.config.floating_opacity)
        self._apply_theme()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(box)

        label = Gtk.Label(label="拼")
        label.set_margin_start(6)
        label.set_margin_end(6)
        box.pack_start(label, False, False, 0)

        settings = Gtk.Button(label="设置")
        settings.connect("clicked", self._open_settings)
        box.pack_start(settings, False, False, 0)

        close = Gtk.Button(label="×")
        close.connect("clicked", lambda _button: self.destroy())
        box.pack_start(close, False, False, 0)

        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        self.connect("destroy", Gtk.main_quit)

    def _apply_theme(self):
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property(
                "gtk-application-prefer-dark-theme",
                self.config.floating_theme == "dark",
            )

    def _open_settings(self, _button):
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "configure_gui.py")
        subprocess.Popen([sys.executable, script])

    def _on_press(self, _widget, event):
        if event.button == 1:
            self.begin_move_drag(event.button, int(event.x_root), int(event.y_root), event.time)
            return True
        return False

    def _on_release(self, _widget, _event):
        return False


def main():
    win = FloatingPanel()
    win.show_all()
    screen = Gdk.Screen.get_default()
    if screen:
        monitor = screen.get_primary_monitor()
        geo = screen.get_monitor_geometry(monitor)
        win.move(geo.x + geo.width - 150, geo.y + 80)
    Gtk.main()


if __name__ == "__main__":
    main()

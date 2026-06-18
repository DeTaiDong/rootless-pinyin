#!/usr/bin/python3
"""Small optional floating panel for rootless-pinyin."""

import os
import subprocess
import sys

import cairo
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import UserConfig


LIGHT_CSS = b"""
window {
    background: transparent;
}
.panel {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid rgba(32, 36, 42, 0.16);
    border-radius: 18px;
}
.brand {
    color: #ffffff;
    background: #1f6feb;
    border-radius: 14px;
    font-weight: 700;
    padding: 4px 10px;
}
.panel-button {
    color: #20242a;
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 4px 10px;
}
.panel-button:hover {
    background: rgba(31, 111, 235, 0.12);
}
.close-button:hover {
    background: rgba(218, 54, 51, 0.14);
}
"""

DARK_CSS = b"""
window {
    background: transparent;
}
.panel {
    background: rgba(34, 39, 46, 0.94);
    border: 1px solid rgba(255, 255, 255, 0.14);
    border-radius: 18px;
}
.brand {
    color: #ffffff;
    background: #2f81f7;
    border-radius: 14px;
    font-weight: 700;
    padding: 4px 10px;
}
.panel-button {
    color: #f0f3f6;
    background: transparent;
    border: none;
    border-radius: 12px;
    padding: 4px 10px;
}
.panel-button:hover {
    background: rgba(255, 255, 255, 0.1);
}
.close-button:hover {
    background: rgba(248, 81, 73, 0.18);
}
"""


class FloatingPanel(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="rootless-pinyin")
        self.config = UserConfig.load()

        self.set_app_paintable(True)
        self._enable_transparent_window()
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_resizable(False)
        self.set_border_width(0)
        self.set_opacity(self.config.floating_opacity)
        self._apply_theme()
        self._apply_css()

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.get_style_context().add_class("panel")
        box.set_margin_start(0)
        box.set_margin_end(0)
        box.set_margin_top(0)
        box.set_margin_bottom(0)
        self.add(box)

        label = Gtk.Label(label="拼")
        label.set_margin_start(6)
        label.set_margin_end(6)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.get_style_context().add_class("brand")
        box.pack_start(label, False, False, 0)

        settings = Gtk.Button(label="设置")
        settings.get_style_context().add_class("panel-button")
        settings.connect("clicked", self._open_settings)
        box.pack_start(settings, False, False, 0)

        close = Gtk.Button(label="×")
        close.get_style_context().add_class("panel-button")
        close.get_style_context().add_class("close-button")
        close.connect("clicked", lambda _button: self.destroy())
        box.pack_start(close, False, False, 0)

        self.connect("button-press-event", self._on_press)
        self.connect("button-release-event", self._on_release)
        self.connect("destroy", Gtk.main_quit)

    def _enable_transparent_window(self):
        screen = self.get_screen()
        if screen and screen.is_composited():
            visual = screen.get_rgba_visual()
            if visual:
                self.set_visual(visual)
        self.connect("draw", self._draw_transparent_background)

    def _draw_transparent_background(self, _widget, cr):
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.set_source_rgba(0, 0, 0, 0)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _apply_theme(self):
        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property(
                "gtk-application-prefer-dark-theme",
                self.config.floating_theme == "dark",
            )

    def _apply_css(self):
        provider = Gtk.CssProvider()
        if self.config.floating_theme == "dark":
            provider.load_from_data(DARK_CSS)
        else:
            provider.load_from_data(LIGHT_CSS)
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
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

#!/usr/bin/env python
# Copyright (C) 2007-2008 Jan Alonzo <jmalonzo@unpluggable.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# TODO:
#
# * fix tab relabelling
# * search page interface
# * custom button - w/o margins/padding to make tabs thin
#

from gettext import gettext as _

import gobject
import gtk
import pango
import webkit
from inspector import Inspector

ABOUT_PAGE = """
<html><head><title>PyWebKitGtk - About</title></head><body>
<h1>Welcome to <code>webbrowser.py</code></h1>
<p>
<strong>Home:</strong><a
href="http://code.google.com/p/pywebkitgtk/">http://code.google.com/p/pywebkitgtk/</a><br/>
<strong>Wiki:</strong><a
href="http://live.gnome.org/PyWebKitGtk">http://live.gnome.org/PyWebKitGtk</a><br/>
</p>
</body></html>
"""

class BrowserPage(webkit.WebView):

    def __init__(self):
        webkit.WebView.__init__(self)
        settings = self.get_settings()
        settings.set_property("enable-developer-extras", True)

        # scale other content besides from text as well
        self.set_full_content_zoom(True)

        # make sure the items will be added in the end
        # hence the reason for the connect_after
        self.connect_after("populate-popup", self.populate_popup)

    def populate_popup(self, view, menu):
        # zoom buttons
        zoom_in = gtk.ImageMenuItem(gtk.STOCK_ZOOM_IN)
        zoom_in.connect('activate', zoom_in_cb, view)
        menu.append(zoom_in)

        zoom_out = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
        zoom_out.connect('activate', zoom_out_cb, view)
        menu.append(zoom_out)

        zoom_hundred = gtk.ImageMenuItem(gtk.STOCK_ZOOM_100)
        zoom_hundred.connect('activate', zoom_hundred_cb, view)
        menu.append(zoom_hundred)

        menu.append(gtk.SeparatorMenuItem())

        aboutitem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        menu.append(aboutitem)
        aboutitem.connect('activate', about_pywebkitgtk_cb, view)

        menu.show_all()
        return False

class TabLabel (gtk.HBox):
    """A class for Tab labels"""

    __gsignals__ = {
        "close": (gobject.SIGNAL_RUN_FIRST,
                  gobject.TYPE_NONE,
                  (gobject.TYPE_OBJECT,))
        }

    def __init__ (self, title, child):
        """initialize the tab label"""
        gtk.HBox.__init__(self, False, 4)
        self.title = title
        self.child = child
        self.label = gtk.Label(title)
        self.label.props.max_width_chars = 30
        self.label.set_ellipsize(pango.ELLIPSIZE_MIDDLE)
        self.label.set_alignment(0.0, 0.5)

        icon = gtk.image_new_from_stock(gtk.STOCK_ORIENTATION_PORTRAIT, gtk.ICON_SIZE_MENU)
        close_image = gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        close_button = gtk.Button()
        close_button.set_relief(gtk.RELIEF_NONE)
        close_button.connect("clicked", self._close_tab, child)
        close_button.add(close_image)
        self.pack_start(icon, False, False, 0)
        self.pack_start(self.label, True, True, 0)
        self.pack_start(close_button, False, False, 0)

        self.set_data("label", self.label)
        self.set_data("close-button", close_button)
        self.connect("style-set", tab_label_style_set_cb)

    def set_label_text (self, text):
        """sets the text of this label"""
        self.label.set_label(text)

    def _close_tab (self, widget, child):
        self.emit("close", child)

def tab_label_style_set_cb (tab_label, style):
    context = tab_label.get_pango_context()
    metrics = context.get_metrics(tab_label.style.font_desc, context.get_language())
    char_width = metrics.get_approximate_digit_width()
    (width, height) = gtk.icon_size_lookup_for_settings(tab_label.get_settings(), gtk.ICON_SIZE_MENU)
    tab_label.set_size_request(20 * pango.PIXELS(char_width) + 2 * width, -1)
    button = tab_label.get_data("close-button")
    button.set_size_request(width + 4, height + 4)


class ContentPane (gtk.Notebook):

    __gsignals__ = {
        "focus-view-title-changed": (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE,
                                     (gobject.TYPE_OBJECT, gobject.TYPE_STRING,)),
        "focus-view-load-committed": (gobject.SIGNAL_RUN_FIRST,
                                      gobject.TYPE_NONE,
                                      (gobject.TYPE_OBJECT, gobject.TYPE_OBJECT,))
        }

    def __init__ (self):
        """initialize the content pane"""
        gtk.Notebook.__init__(self)
        self.props.scrollable = True
        self.props.homogeneous = True
        self.connect("switch-page", self._switch_page)

        self.show_all()
        self._hovered_uri = None

    def load (self, text):
        """load the given uri in the current web view"""
        child = self.get_nth_page(self.get_current_page())
        view = child.get_child()
        view.open(text)

    def new_tab (self, url=None):
        """creates a new page in a new tab"""
        # create the tab content
        browser = BrowserPage()
        browser.connect("hovering-over-link", self._hovering_over_link_cb)
        browser.connect("populate-popup", self._populate_page_popup_cb)
        browser.connect("load-committed", self._view_load_committed_cb)
        browser.connect("load-finished", self._view_load_finished_cb)
        inspector = Inspector(browser.get_web_inspector())

        scrolled_window = gtk.ScrolledWindow()
        scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.add(browser)
        scrolled_window.show_all()

        # load the content
        self._hovered_uri = None
        if not url:
            browser.load_string(ABOUT_PAGE, "text/html", "iso-8859-15", "about")
            url = "about"
        else:
            browser.open(url)

        # create the tab
        label = TabLabel(url, scrolled_window)
        label.connect("close", self._close_tab)
        label.show_all()

        new_tab_number = self.append_page(scrolled_window, label)
        self.set_tab_label_packing(scrolled_window, False, False, gtk.PACK_START)
        self.set_tab_label(scrolled_window, label)

        # hide the tab if there's only one
        self.set_show_tabs(self.get_n_pages() > 1)

        self.show_all()
        self.set_current_page(new_tab_number)

    def _populate_page_popup_cb(self, view, menu):
        # misc
        if self._hovered_uri:
            open_in_new_tab = gtk.MenuItem(_("Open Link in New Tab"))
            open_in_new_tab.connect("activate", self._open_in_new_tab, view)
            menu.insert(open_in_new_tab, 0)
            menu.show_all()

    def _open_in_new_tab (self, menuitem, view):
        self.new_tab(self._hovered_uri)

    def _close_tab (self, label, child):
        page_num = self.page_num(child)
        if page_num != -1:
            view = child.get_child()
            view.destroy()
            self.remove_page(page_num)
        self.set_show_tabs(self.get_n_pages() > 1)

    def _switch_page (self, notebook, page, page_num):
        child = self.get_nth_page(page_num)
        view = child.get_child()
        frame = view.get_main_frame()
        self.emit("focus-view-load-committed", view, frame)

    def _hovering_over_link_cb (self, view, title, uri):
        self._hovered_uri = uri

    def _view_load_committed_cb (self, view, frame):
        self.emit("focus-view-load-committed", view, frame)

    def _view_load_finished_cb(self, view, frame):
        child = self.get_nth_page(self.get_current_page())
        label = self.get_tab_label(child)
        title = frame.get_title()
        if not title:
           title = frame.get_uri()
        label.set_label_text(title)


class WebToolbar(gtk.Toolbar):

    __gsignals__ = {
        "load-requested": (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_STRING,)),
        "new-tab-requested": (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ())
        }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        # location entry
        self._entry = gtk.Entry()
        self._entry.connect('activate', self._entry_activate_cb)
        entry_item = gtk.ToolItem()
        entry_item.set_expand(True)
        entry_item.add(self._entry)
        self._entry.show()

        self.insert(entry_item, -1)
        entry_item.show()

        # add tab button
        button = gtk.ToolButton(gtk.STOCK_ADD)
        button.connect("clicked", self._add_tab_cb)
        self.insert(button, -1)
        button.show()

    def location_set_text (self, text):
        self._entry.set_text(text)

    def _entry_activate_cb(self, entry):
        self.emit("load-requested", entry.props.text)

    def _add_tab_cb (self, button):
        self.emit("new-tab-requested")

class WebBrowser(gtk.Window):

    def __init__(self):
        gtk.Window.__init__(self)

        toolbar = WebToolbar()
        content_tabs = ContentPane()
        content_tabs.connect("focus-view-load-committed", self._load_committed_cb, toolbar)
        toolbar.connect("load-requested", load_requested_cb, content_tabs)
        toolbar.connect("new-tab-requested", new_tab_requested_cb, content_tabs)

        vbox = gtk.VBox(spacing=1)
        vbox.pack_start(toolbar, expand=False, fill=False)
        vbox.pack_start(content_tabs)

        self.add(vbox)
        self.set_default_size(800, 600)
        self.connect('destroy', destroy_cb, content_tabs)

        content_tabs.new_tab("http://www.google.com")

        self.show_all()

    def _load_committed_cb (self, tabbed_pane, view, frame, toolbar):
        title = frame.get_title()
        if not title:
           title = frame.get_uri()
        self.set_title(_("PyWebKitGtk - %s") % title)
        load_committed_cb(tabbed_pane, view, frame, toolbar)

# event handlers
def new_tab_requested_cb (toolbar, content_pane):
    content_pane.new_tab("about:blank")

def load_requested_cb (widget, text, content_pane):
    if not text:
        return
    content_pane.load(text)

def load_committed_cb (tabbed_pane, view, frame, toolbar):
    uri = frame.get_uri()
    if uri:
        toolbar.location_set_text(uri)

def destroy_cb(window, content_pane):
    """destroy window resources"""
    num_pages = content_pane.get_n_pages()
    while num_pages != -1:
        child = content_pane.get_nth_page(num_pages)
        if child:
            view = child.get_child()
            view.destroy()
        num_pages = num_pages - 1
    window.destroy()
    gtk.main_quit()

# context menu item callbacks
def about_pywebkitgtk_cb(menu_item, web_view):
    web_view.open("http://live.gnome.org/PyWebKitGtk")

def zoom_in_cb(menu_item, web_view):
    """Zoom into the page"""
    web_view.zoom_in()

def zoom_out_cb(menu_item, web_view):
    """Zoom out of the page"""
    web_view.zoom_out()

def zoom_hundred_cb(menu_item, web_view):
    """Zoom 100%"""
    if not (web_view.get_zoom_level() == 1.0):
        web_view.set_zoom_level(1.0)

if __name__ == "__main__":
    webbrowser = WebBrowser()
    gtk.main()

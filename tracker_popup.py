import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class TrackerPopUp(Gtk.Dialog):
    def __init__(self, parent):
        response = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OK, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(self, title='New tracker', transient_for=parent)
        self.add_buttons(*response)
        self.set_default_size(300, 50)
        self.entry = Gtk.Entry()
        self.entry.connect('activate', self.on_activation)
        box = self.get_content_area()
        box.add(self.entry)
        self.show_all()

    def get_text(self):
        text = self.entry.get_text()
        return text

    def on_activation(self, _):
        self.response(Gtk.ResponseType.OK)

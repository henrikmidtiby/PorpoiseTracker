import os
from tracker_popup import TrackerPopUp
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GObject


class GridHandler:
    def __init__(self, jump_to_frame_func):
        self.jump_to_frame_func = jump_to_frame_func
        self.current_video_iter = None
        self.current_video = None
        self.video_dict = {}
        self.remove_marking_func = None
        self.update_draw_markings_func = None
        self.current_selection = None
        self.current_iter = None
        self.current_name = None
        self.current_path = ''
        self.color = Gdk.RGBA(1, 0, 0, 1)
        self.window = None
        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_size_request(350, 100)
        self.scrolled_window.set_vexpand(True)
        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_property('icon_size', 1)
        context = self.toolbar.get_style_context()
        context.add_class('inline-toolbar')
        self.vbox.add(self.scrolled_window)
        self.vbox.add(self.toolbar)
        self.status_button = Gtk.ToolButton()
        self.status_button.set_icon_name('dialog-information')
        self.status_button.connect('clicked', self.on_status_button)
        self.toolbar.add(self.status_button)
        self.add_button = Gtk.ToolButton()
        self.add_button.set_icon_name('list-add')
        self.add_button.connect('clicked', self.on_add)
        self.toolbar.add(self.add_button)
        self.remove_button = Gtk.ToolButton()
        self.remove_button.set_icon_name('list-remove')
        self.remove_button.connect('clicked', self.on_remove)
        self.toolbar.add(self.remove_button)
        self.color_button_item = Gtk.ToolItem()
        self.color_button = Gtk.ColorButton()
        self.color_button_item.add(self.color_button)
        self.color_button.connect('color-set', self.on_color_button)
        self.color_button.set_color(Gdk.color_parse('red'))
        self.toolbar.add(self.color_button_item)
        self.jump_to_frame_button = Gtk.ToolButton()
        self.jump_to_frame_button.set_icon_name('go-jump')
        self.jump_to_frame_button.connect('clicked', self.on_jump_to_frame)
        self.toolbar.add(self.jump_to_frame_button)
        self.popover = Gtk.Popover()
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.popover_label = Gtk.Label(label='Video, Log and FOV not opened')
        vbox.pack_start(self.popover_label, False, True, 10)
        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.TOP)

        self.tree_store = Gtk.TreeStore(str, str, str, bool, object, Gdk.RGBA.__gtype__)
        self.tree_view = Gtk.TreeView.new_with_model(self.tree_store)
        self.tree_select = self.tree_view.get_selection()
        self.tree_select.set_select_function(self.selection_function)
        self.tree_select.set_mode(Gtk.SelectionMode.BROWSE)
        self.tree_select.connect('changed', self.on_tree_change)
        self.color_renderer = Gtk.CellRendererText()
        self.color_column = Gtk.TreeViewColumn('', self.color_renderer, background_rgba=5)
        self.tree_view.append_column(self.color_column)
        self.text_renderer = Gtk.CellRendererText()
        self.text_name_renderer = Gtk.CellRendererText()
        self.text_renderer.set_alignment(1, 1)
        self.name_column = Gtk.TreeViewColumn('Video/Name', self.text_name_renderer, text=0)
        self.name_column.set_expand(True)
        self.name_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.name_column.set_resizable(True)
        self.tree_view.append_column(self.name_column)
        self.time_column = Gtk.TreeViewColumn('Time', self.text_renderer, text=1)
        self.tree_view.append_column(self.time_column)
        self.length_column = Gtk.TreeViewColumn('Length', self.text_renderer, text=2)
        self.tree_view.append_column(self.length_column)
        self.toggle_renderer = Gtk.CellRendererToggle()
        self.toggle_renderer.connect('toggled', self.on_show_hide)
        self.hide_column = Gtk.TreeViewColumn('Hide', self.toggle_renderer, active=3)
        self.tree_view.append_column(self.hide_column)
        self.scrolled_window.add(self.tree_view)
        self.tree_view.set_expander_column(self.name_column)

    def selection_function(self, selection, tree_store, path, other):
        str_path = str(path).split(':')
        if self.current_video != self.tree_store[str_path[0]][0]:
            return False
        if len(str_path) < 2:
            return False
        return True

    def on_open_video(self, video):
        self.current_video = video
        if self.current_video_iter is not None:
            self.tree_view.collapse_row(self.tree_store.get_path(self.current_video_iter))
        if video in self.video_dict:
            self.current_video_iter = self.video_dict[video]
            self.tree_view.expand_row(self.tree_store.get_path(self.current_video_iter), True)
        else:
            self.current_video_iter = self.tree_store.append(None, [video, '', '', False, None, Gdk.RGBA()])
            self.video_dict.update({video: self.current_video_iter})
            tree_iter = self.tree_store.append(self.current_video_iter, ['Doodles', '', '', False, None, self.color])
            self.tree_view.expand_row(self.tree_store.get_path(self.current_video_iter), True)
            self.tree_select.select_iter(tree_iter)
        self.update_draw_markings_func()

    def on_color_button(self, button):
        color = button.get_rgba()
        if self.current_selection:
            marking = self.tree_store[self.current_iter][4]
            marking.color = color
        else:
            n_children = self.tree_store.iter_n_children(self.current_iter)
            for i in range(n_children):
                child = self.tree_store.iter_nth_child(self.current_iter, i)
                marking = self.tree_store[child][4]
                marking.color = color
                self.tree_store[child][5] = color
        self.tree_store[self.current_iter][5] = color
        self.update_draw_markings_func()

    def on_jump_to_frame(self, button):
        position = self.current_selection.marking[-1] * 1e-9
        self.jump_to_frame_func(position)

    def on_show_hide(self, button, path):
        self._on_show_hide(path)
        self.update_draw_markings_func()

    def _on_show_hide(self, path):
        marking = self.tree_store[path][4]
        if marking:
            if self.tree_store[path][3]:
                marking.hide = False
            else:
                marking.hide = True
            self.tree_store[path][3] = not self.tree_store[path][3]
        else:
            tree_iter = self.tree_store.get_iter(path)
            n_children = self.tree_store.iter_n_children(tree_iter)
            for i in range(n_children):
                child = self.tree_store.iter_nth_child(tree_iter, i)
                new_path = self.tree_store.get_path(child)
                self._on_show_hide(new_path)
            self.tree_store[tree_iter][3] = not self.tree_store[tree_iter][3]

    def on_tree_change(self, selection):
        model, tree_iter = selection.get_selected()
        if tree_iter:
            self.current_iter = tree_iter
            self.current_selection = model[tree_iter][4]
            self.current_path = ''
            temp = str(model.get_path(tree_iter)).split(':')
            if len(temp) <= 2:
                self.current_path = ':'.join(temp)
            else:
                self.current_path = ':'.join(temp[:2])
            self.current_name = model[self.current_path][0]
        else:
            self.current_iter = None
            self.current_selection = None
            self.current_path = None
            self.current_name = None

    def add_marking(self, marking):
        time = str('%.1f' % (marking.marking[-1] * 1e-9))
        length = str('%.2f' % (marking.data[0]) if marking.data[0] else '')
        tree_iter = self.tree_store.get_iter_from_string(self.current_path)
        self.tree_store.append(tree_iter, [self.current_name, time, length, False, marking, marking.color])

    def on_add(self, button):
        dialog = TrackerPopUp(self.window)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            name = dialog.get_text()
            dialog.destroy()
            tree_iter = self.tree_store.append(self.current_video_iter, [name, '', '', False, None, self.color])
            self.tree_select.select_iter(tree_iter)
        else:
            dialog.destroy()

    def add_marking_from_csv(self, marking):
        time = str('%.1f' % (marking.marking[-1] * 1e-9))
        length = str('%.2f' % (marking.data[0]) if marking.data[0] else '')
        video_name = marking.video.split(os.sep)[-1]
        for video in self.tree_store:
            if video_name == str(video[0]):
                for name in video.iterchildren():
                    if marking.name == str(name[0]):
                        self.tree_store.append(name.iter, ['', time, length, False, marking, marking.color])
                        return None
                tree_iter = self.tree_store.append(video.iter, [marking.name, '', '', False, None, marking.color])
                self.tree_store.append(tree_iter, ['', time, length, False, marking, marking.color])
                return None
        tree_iter1 = self.tree_store.append(None, [video_name, '', '', False, None, Gdk.RGBA()])
        self.video_dict.update({video_name: tree_iter1})
        tree_iter2 = self.tree_store.append(tree_iter1, [marking.name, '', '', False, None, marking.color])
        self.tree_store.append(tree_iter2, ['', time, length, False, marking, marking.color])

    def on_remove(self, button):
        if self.current_iter:
            if self.current_selection is None:
                self.remove_branch()
            else:
                self.remove_marking_func(self.current_selection)
            self.tree_store.remove(self.current_iter)

    def remove_branch(self):
        n_children = self.tree_store.iter_n_children(self.current_iter)
        for i in range(n_children):
            child = self.tree_store.iter_nth_child(self.current_iter, i)
            marking = self.tree_store[child][4]
            self.remove_marking_func(marking)

    def on_status_button(self, button):
        self.popover.set_relative_to(button)
        self.popover.show_all()
        self.popover.popup()

    def update_status(self, message, status_type='info'):
        if status_type == 'error':
            icon = 'dialog-error'
        elif status_type == 'warning':
            icon = 'dialog-warning'
        elif status_type == 'ok':
            icon = 'gtk-ok'
        else:
            icon = 'dialog-information'
        self.status_button.set_icon_name(icon)
        self.popover_label.set_text(message)

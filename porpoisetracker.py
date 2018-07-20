from collections import OrderedDict
from gtk_modules import Menu, Video, VideoDrawHandler, Mouse
from gtk_modules.dialogs import ProgressDialog, FileDialog, Dialog
from test_mouse_draw import MouseDraw
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio


class PorpoiseTracker(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.test',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.menu = Menu(self)
        self._file_menu = OrderedDict()
        self._file_menu.update({'_Preferences': ('preferences', '&lt;Primary&gt;p', self.on_preferences)})
        self._file_menu.update({'separator1': None})
        self._file_menu.update({'_Open video': ('open-video', '&lt;Primary&gt;o', self.on_open_video)})
        self._file_menu.update({'_Import drone log': ('import-drone-log', '&lt;Primary&gt;i', self.on_import_drone_log, False)})
        self._file_menu.update({'_Import fov': ('import-fov', '&lt;Primary&gt;&lt;shift&gt;i', self.on_import_fov)})
        self._file_menu.update({'_Import camera params': ('import-camera-params', '&lt;Primary&gt;l', self.on_import_camera_params)})
        self._file_menu.update({'separator2': None})
        self._file_menu.update({'_Save': ('save', '&lt;Primary&gt;s', self.on_save, False)})
        self._file_menu.update({'_Save as': ('save-as', '&lt;Primary&gt;&lt;shift&gt;s', self.on_save_as, False)})
        self._file_menu.update({'_Export video': ('export-video', '&lt;Primary&gt;e', self.on_export_video, False)})
        self._file_menu.update({'separator3': None})
        self._file_menu.update({'_Remove temp files': ('remove-temp-files', None, self.on_remove_temp_files)})
        self._file_menu.update({'_Quit': ('quit', '&lt;Primary&gt;q', self.on_quit)})
        self.menu.add_sub_menu('_File', self._file_menu)
        self._media_menu = OrderedDict()
        self._media_menu.update({'_Play/Pause': ('play-pause', 'space', self.on_play_pause, False)})
        self._media_menu.update({'_Speed x1/2': ('speed1-2', 'minus', self.on_speed_x1_2, False)})
        self._media_menu.update({'_Speed x1': ('speed1', '0', self.on_speed_x1, False)})
        self._media_menu.update({'_Speed x5': ('speed5', 'plus', self.on_speed_x5, False)})
        self._media_menu.update({'separator1': None})
        self._media_menu.update({'_Next frame': ('next-frame', '2', self.on_next_frame, False)})
        self._media_menu.update({'_Previous frame': ('previous-frame', '1', self.on_previous_frame, False)})
        self._media_menu.update({'separator2': None})
        self._media_menu.update({'_Zoom in': ('zoom-in', '&lt;Primary&gt;plus', self.on_zoom_in, False)})
        self._media_menu.update({'_Zoom Out': ('zoom-out', '&lt;Primary&gt;minus', self.on_zoom_out, False)})
        self._media_menu.update({'_Zoom to 100%': ('zoom-normal', '&lt;Primary&gt;0', self.on_zoom_normal, False)})
        self.menu.add_sub_menu('_Media', self._media_menu)
        self._draw_menu = OrderedDict()
        self._draw_menu.update({'_Point': ('point', None, self.on_draw_point, False)})
        self._draw_menu.update({'_line': ('line', None, self.on_draw_line, False)})
        self._draw_menu.update({'_Box': ('box', None, self.on_draw_box, False)})
        self.menu.add_sub_menu('_Draw', self._draw_menu)
        _help = OrderedDict()
        _help.update({'_About': ('about', None, self.on_about)})
        self.menu.add_sub_menu('_Help', _help)
        self.video = Video()
        self.mouse = Mouse(self.video.event_box)
        self.draw_handler = VideoDrawHandler(self.video.emit_draw_signal)
        self.video.signals.connect('video_draw', self.draw_handler.draw)
        self.mouse_draw = MouseDraw(self.mouse.signals, self.draw_handler.signals, self.video.get_position)
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.menu.make_actions()

    def do_activate(self):
        self.menu.activate_menu()
        self.window = Gtk.ApplicationWindow()
        self.window.set_title('Multi Image Annotator')
        self.window.set_application(self)
        self.window.connect('delete_event', self.on_quit)
        self.window.set_size_request(500, 500)
        vertical_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vertical_box.pack_start(self.video.scrolled_window, True, True, 0)
        vertical_box.pack_start(self.video.controls, False, False, 0)
        self.window.add(vertical_box)
        self.window.show_all()

    def enable_media_menu(self, menu, enable):
        for label in menu:
            self.menu.enable_menu_item(label, enable)

    def _enable_media_menu(self, _):
        menu = ['_Speed x1/2', '_Speed x1', '_Speed x5', '_Next frame', '_Previous frame']
        self.enable_media_menu(menu, self.video.player_paused)

    def on_preferences(self, *_):
        pass

    def on_open_video(self, *_):
        dialog = FileDialog(self.window, 'File', 'open')
        dialog.add_mime_filter('python', 'text/x-python')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file = dialog.get_filename()
            dialog.destroy()
            self.video.open_video(file)
            self.enable_media_menu(self._media_menu, True)
            self.video.playback_button.connect('clicked', self._enable_media_menu)
        else:
            dialog.destroy()

    def on_import_drone_log(self, *_):
        pass

    def on_import_fov(self, *_):
        pass

    def on_import_camera_params(self, *_):
        pass

    def on_save(self, *_):
        pass

    def on_save_as(self, *_):
        pass

    def on_export_video(self, *_):
        pass

    def on_remove_temp_files(self, *_):
        pass

    def on_quit(self, *_):
        self.quit()

    def on_play_pause(self, *_):
        self.video.playback_button.clicked()
        self._enable_media_menu(None)

    def on_speed_x1_2(self, *_):
        self.video.change_speed('slow')

    def on_speed_x1(self, *_):
        self.video.change_speed()

    def on_speed_x5(self, *_):
        self.video.change_speed('fast')

    def on_next_frame(self, *_):
        self.video.next_frame()

    def on_previous_frame(self, *_):
        self.video.previous_frame()

    def on_zoom_in(self, *_):
        self.video.zoom_in()

    def on_zoom_out(self, *_):
        self.video.zoom_out()

    def on_zoom_normal(self, *_):
        self.video.zoom_normal()

    def on_draw_point(self, *_):
        pass

    def on_draw_line(self, *_):
        pass

    def on_draw_box(self, *_):
        pass

    def on_about(self, *_):
        dialog = Dialog(self.window, 'About', 'close')
        label1 = Gtk.Label('This is a application to meassure and track porpoises.\n')
        label2 = Gtk.Label('Made by:')
        label3 = Gtk.Label('Henrik Egemose, hesc@mmmi.sdu.dk')
        dialog.box.add(label1)
        dialog.box.add(label2)
        dialog.box.add(label3)
        dialog.show_all()
        dialog.run()
        dialog.destroy()


if __name__ == '__main__':
    app = PorpoiseTracker()
    app.run()

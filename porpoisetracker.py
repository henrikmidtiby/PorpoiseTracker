import os
import sys
if sys.platform == 'win32':
    os.environ['GST_PLUGIN_PATH'] = './;./gst-plugins'
import argparse
import shutil
from collections import OrderedDict
from gtk_modules import Menu, Video, VideoDrawHandler, Mouse
from gtk_modules.dialogs import FileDialog, Dialog
from mouse_draw_handler import MouseDrawHandler
from tracker_grid_handler import GridHandler
from drone_log import DroneLog
from fov import Fov
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gio, GLib


class PorpoiseTracker(Gtk.Application):
    def __init__(self):
        super().__init__(application_id='org.test',
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.menu = Menu(self)
        self._file_menu = OrderedDict()
        self._media_menu = OrderedDict()
        self._draw_menu = OrderedDict()
        self._help = OrderedDict()
        self.add_menu()
        self.video = Video()
        self.mouse = Mouse(self.video.event_box)
        self.draw_handler = VideoDrawHandler(self.video.emit_draw_signal)
        self.video.signals.connect('video_draw', self.draw_handler.draw)
        self.grid_handler = GridHandler(self.video.jump_to_position)
        self.drone_log = DroneLog()
        self.video.on_pause_and_slide_change_func = self.drone_log.update_plot
        self.fov = Fov()
        self.mouse_draw = MouseDrawHandler(self.mouse, self.draw_handler, self.video,
                                           self.drone_log, self.fov, self.grid_handler, self.allow_draw)
        self.window = None
        self.save_file = None
        self.video_open = False
        self.drone_log_open = False
        self.fov_open = False
        self.camera_params_open = False

    def add_menu(self):
        self.add_file_submenu()
        self.add_media_submenu()
        self.add_help_submenu()

    def add_help_submenu(self):
        self._help.update({'_About': ('about', None, self.on_about)})
        self.menu.add_sub_menu('_Help', self._help)

    def add_media_submenu(self):
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

    def add_file_submenu(self):
        self._file_menu.update({'_Preferences': ('preferences', '&lt;Primary&gt;p', self.on_preferences)})
        self._file_menu.update({'separator1': None})
        self._file_menu.update({'_Open video': ('open-video', '&lt;Primary&gt;o', self.on_open_video)})
        self._file_menu.update({'_Import drone log': ('import-drone-log', '&lt;Primary&gt;i', self.on_import_drone_log, False)})
        self._file_menu.update({'_Import fov': ('import-fov', '&lt;Primary&gt;&lt;shift&gt;i', self.on_import_fov)})
        self._file_menu.update({'_Import camera params': ('import-camera-params', '&lt;Primary&gt;l', self.on_import_camera_params)})
        self._file_menu.update({'_Open annotations': ('open-annotations', '&lt;Primary&gt;&lt;shift&gt;o', self.on_open_annotations)})
        self._file_menu.update({'_Change start height': ('change-start-height', None, self.on_change_start_height)})
        self._file_menu.update({'separator2': None})
        self._file_menu.update({'_Save': ('save', '&lt;Primary&gt;s', self.on_save)})
        self._file_menu.update({'_Save as': ('save-as', '&lt;Primary&gt;&lt;shift&gt;s', self.on_save_as)})
        self._file_menu.update({'_Export video': ('export-video', '&lt;Primary&gt;e', self.on_export_video, False)})
        self._file_menu.update({'separator3': None})
        self._file_menu.update({'_Remove temp files': ('remove-temp-files', None, self.on_remove_temp_files)})
        self._file_menu.update({'_Quit': ('quit', '&lt;Primary&gt;q', self.on_quit)})
        self.menu.add_sub_menu('_File', self._file_menu)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.menu.make_actions()

    def do_activate(self):
        self.menu.activate_menu()
        self.window = Gtk.ApplicationWindow()
        self.window.set_title('Porpoise Measure')
        self.window.set_application(self)
        self.window.connect('delete_event', self.on_quit)
        self.window.set_size_request(700, 500)
        self.grid_handler.window = self.window
        vertical_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vertical_box.pack_start(self.video.scrolled_window, True, True, 0)
        vertical_box.pack_start(self.video.controls, False, False, 0)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_start(vertical_box, True, True, 0)
        hbox.pack_start(self.grid_handler.vbox, False, False, 0)
        self.video.draw_area.connect('realize', self.parse_args)
        self.window.add(hbox)
        self.window.show_all()
        self.mouse_draw.window = self.window

    def enable_media_menu(self, menu, enable):
        for label in menu:
            self.menu.enable_menu_item(label, enable)

    def _enable_media_menu(self, _):
        menu = ['_Speed x1/2', '_Speed x1', '_Speed x5', '_Next frame', '_Previous frame']
        self.enable_media_menu(menu, self.video.player_paused)

    def allow_draw(self):
        if self.video_open and self.drone_log_open and self.fov_open and self.grid_handler.current_name:
            return True
        else:
            return False

    def on_preferences(self, *_):
        dialog = Dialog(self.window, 'Preferences', 'cancel_ok')
        grid = Gtk.Grid()
        label = Gtk.Label(label='Default color:')
        grid.attach(label, 0, 0, 1, 1)
        color_button = Gtk.ColorButton()
        color_button.set_rgba(self.mouse_draw.color)
        color_button.set_use_alpha(True)
        color_button.connect('color-set', self.on_color_button)
        grid.attach(color_button, 1, 0, 1, 1)
        label = Gtk.Label(label='Line thickness:')
        grid.attach(label, 0, 1, 1, 1)
        line_adjustment = Gtk.Adjustment(3, 1, 10, 1, 1, 0)
        line_spinner = Gtk.SpinButton()
        line_spinner.set_numeric(True)
        line_spinner.set_adjustment(line_adjustment)
        line_spinner.set_value(3)
        line_spinner.set_update_policy(Gtk.SpinButtonUpdatePolicy.ALWAYS)
        grid.attach(line_spinner, 1, 1, 1, 1)
        label = Gtk.Label(label='Point size:')
        grid.attach(label, 0, 2, 1, 1)
        point_adjustment = Gtk.Adjustment(5, 1, 30, 1, 1, 0)
        point_spinner = Gtk.SpinButton()
        point_spinner.set_numeric(True)
        point_spinner.set_adjustment(point_adjustment)
        point_spinner.set_value(5)
        point_spinner.set_update_policy(Gtk.SpinButtonUpdatePolicy.ALWAYS)
        grid.attach(point_spinner, 1, 2, 1, 1)
        dialog.box.add(grid)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            dialog.destroy()
            line_thickness = line_spinner.get_value_as_int()
            point_size = point_spinner.get_value_as_int()
            self.draw_handler.line_thickness = line_thickness
            self.draw_handler.point_size = point_size
            self.draw_handler.video_draw_signal()
        else:
            dialog.destroy()

    def on_color_button(self, button):
        color = button.get_rgba()
        self.mouse_draw.color = color
        self.draw_handler.color = color

    def open_status(self):
        not_open = []
        if not self.video_open:
            not_open.append('Video')
        if not self.drone_log_open:
            not_open.append('Log')
        if not self.fov_open:
            not_open.append('FOV')
        if len(not_open) == 2:
            string = not_open[0] + ' and ' + not_open[1] + ' not opened'
            self.grid_handler.update_status(string)
        elif len(not_open) == 1:
            string = not_open[0] + ' not opened'
            self.grid_handler.update_status(string)
        else:
            string = 'All good to go!'
            self.grid_handler.update_status(string, 'ok')

    def on_open_video(self, *_):
        dialog = FileDialog(self.window, 'Choose a video', 'open')
        dialog.add_mime_filter('Video', 'video/quicktime')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file = dialog.get_filename()
            dialog.destroy()
            self.open_video_from_file(file)

        else:
            dialog.destroy()

    def open_video_from_file(self, file):
        if sys.platform == 'win32':
            path = file.split(':')[-1]
            path_as_list = path.split('\\')
            file = ''
            for p in path_as_list[1:]:
                file += '/' + p.replace(' ', '\\ ')
        else:
            file = file.replace(' ', '\\ ')
        try:
            print("Opening video file: '%s'" % file)
            self.video.open_video(file)
            self.enable_media_menu(self._media_menu, True)
            self.video.playback_button.connect('clicked', self._enable_media_menu)
            self.drone_log.set_video_length(self.video.duration * 1e-9)
            self.menu.enable_menu_item('_Import drone log', True)
            self.menu.enable_menu_item('_Export video', True)
            self.mouse_draw.video = file
            self.video_open = True
            self.open_status()
        except AttributeError:
            self.grid_handler.update_status('Error opening video', 'error')

    def on_import_drone_log(self, *_):
        dialog = FileDialog(self.window, 'Choose a drone log', 'open')
        dialog.add_mime_filter('raw log', 'text/plain')
        dialog.add_mime_filter('csv log', 'text/csv')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            log_file = dialog.get_filename()
            dialog.destroy()
            self.open_drone_log_from_file(log_file)
        else:
            dialog.destroy()

    def open_drone_log_from_file(self, log_file):
        self.drone_log.drone_log_data = {}
        if log_file.endswith('.csv'):
            log_generator = self.drone_log.get_csv_log_generator(log_file, self.window)
        else:
            log_generator = self.drone_log.get_log_generator(log_file, self.window)
        try:
            print("Opening log file: '%s'" % log_file)
            log_generator.__next__()
            GLib.idle_add(log_generator.__next__)
            self.drone_log_open = True
            self.open_status()
        except ValueError:
            self.grid_handler.update_status('Error opening drone log', 'error')

    def on_import_fov(self, *_):
        dialog = FileDialog(self.window, 'Choose a FOV file', 'open')
        dialog.add_mime_filter('csv', 'test/csv')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fov_file = dialog.get_filename()
            self.open_fov_file(fov_file)
        dialog.destroy()

    def open_fov_file(self, fov_file):
        try:
            print("Opening fov file: '%s'" % fov_file)
            self.fov.set_fov_from_file(fov_file)
            self.fov_open = True
            self.open_status()
        except ValueError:
            self.grid_handler.update_status('Error opening FOV file', 'error')

    def on_import_camera_params(self, *_):
        dialog = FileDialog(self.window, 'Choose a Camera param Matlab file', 'open')
        dialog.add_mime_filter('Matlab file', 'text/plain')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            mat_file = dialog.get_filename()
            dialog.destroy()
            self.open_camera_params_file(mat_file)
        else:
            dialog.destroy()

    def open_camera_params_file(self, mat_file):
        try:
            print("Opening camera parameters in: '%s'" % mat_file)
            self.fov.set_camera_params(mat_file)
            self.camera_params_open = True
        except TypeError:
            self.grid_handler.update_status('Error opening camera params', 'error')

    def on_change_start_height(self, *_):
        dialog = Dialog(self.window, 'Start height in meters', 'cancel_ok')
        adjustment = Gtk.Adjustment(0, 0, 1000, 1, 1, 0)
        spinner = Gtk.SpinButton()
        spinner.set_adjustment(adjustment)
        dialog.box.add(spinner)
        dialog.show_all()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            start_height = spinner.get_value()
            self.drone_log.height_difference = start_height
            dialog.destroy()
        else:
            dialog.destroy()

    def on_save(self, *_):
        if self.save_file is not None:
            self.mouse_draw.save(self.save_file)
        else:
            self.on_save_as()

    def on_save_as(self, *_):
        dialog = FileDialog(self.window, 'Save as', 'save', 'untitled.csv')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            self.save_file = dialog.get_filename()
            dialog.destroy()
            self.mouse_draw.save(self.save_file)
        else:
            dialog.destroy()

    def on_export_video(self, *_):
        pass

    def on_open_annotations(self, *_):
        dialog = FileDialog(self.window, 'Choose a annotations csv file', 'open')
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            file = dialog.get_filename()
            dialog.destroy()
            self.open_annotations(file)
        else:
            dialog.destroy()

    def open_annotations(self, file):
        try:
            print("Opening annotations file: '%s'" % file)
            self.mouse_draw.open_annotations(file)
        except ValueError:
            self.grid_handler.update_status('Error opening annotations file', 'error')

    @staticmethod
    def on_remove_temp_files(*_):
        shutil.rmtree('temp/')
        os.mkdir('temp/')

    def on_quit(self, *_):
        self.on_remove_temp_files()
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

    def on_about(self, *_):
        dialog = Dialog(self.window, 'About', 'close')
        label1 = Gtk.Label('This is a application to measure porpoises.\n')
        label2 = Gtk.Label('Made by:')
        label3 = Gtk.Label('Henrik Egemose, hesc@mmmi.sdu.dk')
        with open('version.txt') as version_file:
            version = version_file.read()
        label4 = Gtk.Label('Version: ' + version)
        dialog.box.add(label1)
        dialog.box.add(label2)
        dialog.box.add(label3)
        dialog.box.add(label4)
        dialog.show_all()
        dialog.run()
        dialog.destroy()

    def parse_args(self, _):
        parser = argparse.ArgumentParser(description='Measure porpoises')
        parser.add_argument('--video', type=str, help='Open video file')
        parser.add_argument('--log', type=str, help='Open drone log')
        parser.add_argument('--fov', type=str, help='Open fov file')
        parser.add_argument('--cam', type=str, help='Open camera parameter file')
        parser.add_argument('--annotations', type=str, help='Open annotations file')
        args = parser.parse_args()
        if args.video:
            video_file = os.path.abspath(args.video)
            self.open_video_from_file(video_file)
        if args.fov:
            self.open_fov_file(args.fov)
        if args.cam:
            self.open_camera_params_file(args.cam)
        if args.annotations:
            self.open_annotations(args.annotations)
        if args.log:
            self.open_drone_log_from_file(args.log)


if __name__ == '__main__':
    app = PorpoiseTracker()
    app.run()

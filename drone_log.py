import os
import sys
import subprocess
import csv
import numpy as np
from itertools import product
from datetime import datetime
from matplotlib.backends.backend_gtk3 import NavigationToolbar2GTK3
from matplotlib.backends.backend_gtk3agg import FigureCanvasGTK3Agg as FigureCanvas
from matplotlib.figure import Figure
from gtk_modules.dialogs import ProgressDialog
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject


class DroneLog:
    def __init__(self):
        self.log_file = None
        self.drone_log_data = {}
        self.log_time_list = []
        self.video_list = []
        self.plot_list = []
        self.video_start_time = 0
        self.video_lat_lon = None
        self.video_length_difference_to_logfile = 10
        self.plot_win = None
        self.height_difference = 0
        self.video_length = 0

    def set_video_length(self, video_length):
        self.video_length = video_length

    def set_video_start_time(self, video_start_time):
        self.video_start_time = video_start_time

    def get_csv_log_generator(self, log_file, window):
        progress_dialog = ProgressDialog(window, 'Loading log', 2)
        progress_dialog.show()
        progress_update_generator = progress_dialog.update_progress()
        progress_update_generator.__next__()
        yield True
        parse_log_gen = self.parse_csv_log_generator(log_file)
        for _ in zip(progress_update_generator, parse_log_gen):
            yield True
        progress_dialog.close()
        self.plot_log_data()
        yield False

    def parse_csv_log_generator(self, log_file):
        yield True
        self.parse_log(log=log_file)
        yield False

    def parse_log_generator(self, log_file):
        self.convert_log(log_file)
        yield True
        self.parse_log()
        yield False

    def get_log_generator(self, log_file, window):
        progress_dialog = ProgressDialog(window, 'Loading log', 2)
        progress_dialog.show()
        progress_update_generator = progress_dialog.update_progress()
        progress_update_generator.__next__()
        parse_log_gen = self.parse_log_generator(log_file)
        parse_log_gen.__next__()
        yield True
        for _ in zip(progress_update_generator, parse_log_gen):
            yield True
        progress_dialog.close()
        self.plot_log_data()
        yield False

    def show_warning_if_video_and_log_does_not_match(self):
        if self.video_length_difference_to_logfile > 2:
            dialog = Gtk.MessageDialog(self.plot_win, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CANCEL, "Error: Video and log does probably not match")
            dialog.format_secondary_text(
                "The video and log file recording differs by %.1f seconds." % self.video_length_difference_to_logfile)
            dialog.run()
            dialog.destroy()

    def convert_log(self, log_file):
        path = os.path.join('temp', 'drone_log.csv')
        if os.path.isfile(path):
            os.remove(path)
        if sys.platform == 'linux':
            cmd = 'wine drone_log/TXTlogToCSVtool "' + log_file + '" "' + path + '"'
        else:
            cmd = 'drone_log\\TXTlogToCSVtool "' + log_file + '" "' + path + '"'
        self.log_file = log_file
        subprocess.call(cmd, shell=True)

    @staticmethod
    def remove_null_bytes(log):
        with open(log, 'rb') as fi:
            data = fi.read()
        with open(log, 'wb') as fo:
            fo.write(data.replace(b'\x00', b''))

    def parse_log(self, log=None):
        self.drone_log_data = {}
        self.log_time_list = []
        self.video_list = []
        self.plot_list = []
        if log is None:
            log = os.path.join('temp', 'drone_log.csv')
        self.remove_null_bytes(log)
        with open(log, encoding='iso8859_10') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            field_names = reader.__next__()
            update_time_idx = field_names.index('CUSTOM.updateTime')
            gimbal_pitch_idx = field_names.index('GIMBAL.pitch')
            gimbal_yaw_idx = field_names.index('GIMBAL.yaw')
            gimbal_roll_idx = field_names.index('GIMBAL.roll')
            height_idx = field_names.index('OSD.height [m]')
            video_idx = field_names.index('CUSTOM.isVideo')
            latitude_idx = field_names.index('OSD.latitude')
            longitude_idx = field_names.index('OSD.longitude')
            video_start = None
            video_end = None
            last_is_video = ''
            for row in reader:
                if row[update_time_idx] != '':
                    try:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S.%f').timestamp()
                        date_time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S.%f')
                    except ValueError:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S').timestamp()
                        date_time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S')
                    try:
                        height = float(row[height_idx])
                        pitch = float(row[gimbal_pitch_idx]) * np.pi / 180
                        yaw = float(row[gimbal_yaw_idx]) * np.pi / 180
                        roll = float(row[gimbal_roll_idx]) * np.pi / 180
                        yaw_pitch_roll = (yaw, pitch, roll)
                        latitude = float(row[latitude_idx])
                        longitude = float(row[longitude_idx])
                    except ValueError:
                        continue
                    pos = (latitude, longitude)
                    self.drone_log_data.update({time: (height, yaw_pitch_roll, pos, date_time)})
                    self.log_time_list.append(time)
                    self.plot_list.append((float(row[gimbal_yaw_idx]), float(row[gimbal_pitch_idx]), float(row[gimbal_roll_idx]), height))
                    is_video = row[video_idx]
                    if is_video and video_start is None:
                        video_start = time
                    if not is_video and last_is_video:
                        video_end = time
                    if video_start and video_end:
                        self.video_list.append((video_start, video_end))
                        video_start = None
                        video_end = None
                    last_is_video = is_video

    def get_video_start_time(self):
        """
        Get start time of the loaded video.
        
        Iterate through all recordings in the log file and
        locate the recording with a duration similar to the
        length of the loaded video or a location.
        """
        keep_diff = np.inf
        video_start_time = 0
        print('\n      video length: %f' % self.video_length)
        if self.video_lat_lon is not None:
            print('    Video location: (%f, %f)' % (self.video_lat_lon[0], self.video_lat_lon[1]))
        for recording in self.video_list:
            if self.video_lat_lon:
                _, _, pos, _ = self.drone_log_data[recording[0]]
                diff = abs(pos[0] - self.video_lat_lon[0]) + abs(pos[1] - self.video_lat_lon[1])
                print('recording location: (%f, %f)' % (pos[0], pos[1]))
            else:
                recording_length = recording[1] - recording[0]
                diff = abs(recording_length - self.video_length)
                print('  recording length: %f' % recording_length)
            if diff < keep_diff:
                video_start_time = recording[0]
                keep_diff = diff
        self.video_start_time = video_start_time
        self.video_length_difference_to_logfile = keep_diff
        self.show_warning_if_video_and_log_does_not_match()

    def get_data(self, time):
        diff = np.Inf
        height = None
        rotation = None
        pos = None
        date_time = None
        for time_stamp, height_and_rotation_and_pos_and_time in self.drone_log_data.items():
            t = time_stamp - self.video_start_time
            d = abs(time - t)
            if d < diff:
                height = (height_and_rotation_and_pos_and_time[0] + self.height_difference)
                rotation = height_and_rotation_and_pos_and_time[1]
                pos = height_and_rotation_and_pos_and_time[2]
                date_time = height_and_rotation_and_pos_and_time[3]
                diff = d
        return height, rotation, pos, date_time

    def plot_log_data(self):
        self.plot_win = PlotWindow()
        self.plot_win.connect('click_on_plot', self._update_video_start_time)
        self.plot_win.plot(self.log_time_list, self.plot_list, self.video_list)
        self.update_video_plot()

    def update_video_plot(self):
        self.plot_win.update_video_length_plot(self.video_start_time - self.log_time_list[0], self.video_length)
        self.update_plot(0)

    def update_plot(self, time):
        if self.plot_win:
            self.plot_win.update_plot(time + self.video_start_time - self.log_time_list[0])

    def update_video_start_time(self, video_start_time):
        self._update_video_start_time(None, video_start_time)

    def _update_video_start_time(self, _, video_start_time):
        self.video_start_time = video_start_time + self.log_time_list[0]
        if self.plot_win:
            self.plot_win.update_video_length_plot(video_start_time, self.video_length)
            self.update_plot(0)


class NavigationToolbar(NavigationToolbar2GTK3):
    # only display the buttons we need
    toolitems = [t for t in NavigationToolbar2GTK3.toolitems if
                 t[0] in ('Home', 'Zoom', 'Save')]


class PlotWindow(Gtk.Window):
    __gsignals__ = {
        'click_on_plot': (GObject.SIGNAL_RUN_FIRST, None, (float,))
    }

    def __init__(self):
        super().__init__(title="Yaw Pitch Roll Plot")
        self.window_closed = False
        self.connect('destroy', self.on_destroy)
        self.f = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.f)
        self.f.canvas.mpl_connect('pick_event', self.on_pick)
        vbox = Gtk.VBox()
        self.add(vbox)
        vbox.pack_start(self.canvas, True, True, 0)
        toolbar = NavigationToolbar(self.canvas, self)
        vbox.pack_start(toolbar, False, False, 0)
        self.set_size_request(750, 600)
        self.axarr = None
        self.video_length_plots = [None]*4
        self.yaw_time = None
        self.pitch_time = None
        self.roll_time = None
        self.height_time = None
        self.start_time_stamp = None
        self.video_list = None
        self.show_all()

    def on_destroy(self, *_):
        self.window_closed = True

    def plot(self, time_stamps, data, video_list):
        self.video_list = video_list
        self.start_time_stamp = time_stamps[0]
        time = [t - time_stamps[0] for t in time_stamps]
        yaw, pitch, roll, height = zip(*data)
        self.axarr = self.f.subplots(nrows=2, ncols=2)
        self.plot_yaw(self.axarr, yaw, time)
        self.plot_pitch(self.axarr, pitch, time)
        self.plot_roll(self.axarr, roll, time)
        self.plot_height(self.axarr, height, time)

    @staticmethod
    def shift_yaw(yaw):
        new_yaw = []
        last_point = 0
        shift = 0
        for point in yaw:
            if (last_point > 150 and point < -150) or (last_point < -150 and point > 150):
                if point < 0:
                    shift += 360
                else:
                    shift -= 360
            new_point = point + shift
            last_point = point
            new_yaw.append(new_point)
        return new_yaw

    def plot_yaw(self, axarr, yaw, time):
        new_yaw = self.shift_yaw(yaw)
        for offset in range(-10 * 360, 10 * 360 + 1, 360):
            yaw_with_offset = [x + offset for x in new_yaw]
            axarr[0, 0].plot(time, yaw_with_offset, 'blue')
        axarr[0, 0].set_ylim([-200, 200])
        axarr[0, 0].set_xlim([0, time[-1]])
        axarr[0, 0].set_xlabel('Seconds')
        axarr[0, 0].set_ylabel('Degrees')
        axarr[0, 0].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in self.video_list:
            axarr[0, 0].axvspan(xmin=video[0] - self.start_time_stamp, xmax=video[1] - self.start_time_stamp, color='#bbbbbb', picker=1)
        self.yaw_time = axarr[0, 0].axvline(x=0, color='red', linewidth=2)
        axarr[0, 0].set_title('Yaw')

    def plot_pitch(self, axarr, pitch, time):
        axarr[0, 1].plot(time, pitch, 'blue')
        axarr[0, 1].set_ylim([-100, 30])
        axarr[0, 1].set_xlim([0, time[-1]])
        axarr[0, 1].set_xlabel('Seconds')
        axarr[0, 1].set_ylabel('Degrees')
        axarr[0, 1].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in self.video_list:
            axarr[0, 1].axvspan(xmin=video[0] - self.start_time_stamp, xmax=video[1] - self.start_time_stamp, color='#bbbbbb', picker=1)
        self.pitch_time = axarr[0, 1].axvline(x=0, color='red', linewidth=2)
        axarr[0, 1].set_title('Pitch')

    def plot_roll(self, axarr, roll, time):
        axarr[1, 1].plot(time, roll, 'blue')
        axarr[1, 1].set_ylim([-180, 180])
        axarr[1, 1].set_xlim([0, time[-1]])
        axarr[1, 1].set_xlabel('Seconds')
        axarr[1, 1].set_ylabel('Degrees')
        axarr[1, 1].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in self.video_list:
            axarr[1, 1].axvspan(xmin=video[0] - self.start_time_stamp, xmax=video[1] - self.start_time_stamp, color='#bbbbbb', picker=1)
        self.roll_time = axarr[1, 1].axvline(x=0, color='red', linewidth=2)
        axarr[1, 1].set_title('Roll')

    def plot_height(self, axarr, height, time):
        axarr[1, 0].plot(time, height, 'blue')
        axarr[1, 0].set_xlim([0, time[-1]])
        axarr[1, 0].set_xlabel('Seconds')
        axarr[1, 0].set_ylabel('Meters')
        axarr[1, 0].xaxis.set_ticks(np.arange(0, time[-1], 60))
        ylim = axarr[1, 0].get_ylim()
        for video in self.video_list:
            axarr[1, 0].axvspan(xmin=video[0] - self.start_time_stamp, xmax=video[1] - self.start_time_stamp, color='#bbbbbb', picker=1)
        self.height_time = axarr[1, 0].axvline(x=0, color='red', linewidth=2)
        axarr[1, 0].set_ylim(ylim)
        axarr[1, 0].set_title('Height')

    def update_plot(self, time):
        self.yaw_time.set_xdata(time)
        self.pitch_time.set_xdata(time)
        self.roll_time.set_xdata(time)
        self.height_time.set_xdata(time)
        self.canvas.draw()
        self.canvas.flush_events()

    def update_video_length_plot(self, video_start, video_length):
        for plot in self.video_length_plots:
            if plot:
                plot.remove()
        self.video_length_plots = [self.axarr[x, y].axvspan(xmin=video_start, xmax=video_start + video_length, ymin=0, ymax=0.1, color='#99ff99') for x, y in product(range(2), range(2))]

    def on_pick(self, event):
        video_start = np.min(event.artist.get_xy(), axis=0)[0]
        self.emit('click_on_plot', video_start)


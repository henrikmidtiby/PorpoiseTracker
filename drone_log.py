import os
import sys
import subprocess
import csv
import numpy as np
from datetime import datetime
import logging
from matplotlib.backends.backend_gtk3agg import (FigureCanvasGTK3Agg as FigureCanvas)
from matplotlib.figure import Figure
from gtk_modules.dialogs import ProgressDialog
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class DroneLog:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.log_file = None
        self.drone_log_data = {}
        self.log_time_list = []
        self.video_list = []
        self.plot_list = []
        self.video_start_time = None
        self.plot_win = None
        self.height_difference = 0
        self.video_length = None

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
        self.update_plot(0)
        yield False

    def parse_csv_log_generator(self, log_file):
        yield True
        self.parse_log(log=log_file)
        yield False

    def parse_log_generator(self, log_file):
        self.convert_log(log_file)
        yield True
        self.parse_log()
        self.get_video_start_time()
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
        self.update_plot(0)
        yield False

    def convert_log(self, log_file):
        path = os.path.join('temp', 'drone_log.csv')
        if sys.platform == 'linux':
            cmd = 'wine drone_log/TXTlogToCSVtool "' + log_file + '" "' + path + '"'
        else:
            cmd = 'drone_log\TXTlogToCSVtool "' + log_file + '" "' + path + '"'
        self.log_file = log_file
        res = subprocess.call(cmd, shell=True)
        self.logger.info('subprocess results {}'.format(res))

    @staticmethod
    def remove_null_bytes(log):
        with open(log, 'rb') as fi:
            data = fi.read()
        with open(log, 'wb') as fo:
            fo.write(data.replace(b'\x00', b''))

    def parse_log(self, log=None):
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
        length of the loaded video.
        """
        keep_diff = np.inf
        video_start_time = 0
        for recording in self.video_list:
            recording_length = recording[1] - recording[0]
            diff = abs(recording_length - self.video_length)
            print("video length: %f\n" % self.video_length)
            print("recording length: %f\n" % recording_length)
            if diff < keep_diff:
                video_start_time = recording[0]
                keep_diff = diff
        self.video_start_time = video_start_time

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
        self.plot_win.plot(self.log_time_list, self.plot_list, self.video_list)

    def update_plot(self, time):
        if self.plot_win:
            self.plot_win.update_plot(time + self.video_start_time - self.log_time_list[0])


class PlotWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Yaw Pitch Roll Plot")
        self.f = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvas(self.f)
        self.yaw_time = None
        self.pitch_time = None
        self.roll_time = None
        self.height_time = None
        self.add(self.canvas)

    def plot(self, time_stamps, data, video_list):
        time = [t - time_stamps[0] for t in time_stamps]
        yaw, pitch, roll, height = zip(*data)

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

        axarr = self.f.subplots(nrows=2, ncols=2)

        for offset in range(-10*360, 10*360+1, 360):
            yaw_with_offset = [x + offset for x in new_yaw]
            axarr[0, 0].plot(time, yaw_with_offset, 'blue')
        axarr[0, 0].set_ylim([-200, 200])
        axarr[0, 0].set_xlim([0, time[-1]])
        axarr[0, 0].set_xlabel('Seconds')
        axarr[0, 0].set_ylabel('Degrees')
        axarr[0, 0].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in video_list:
            axarr[0, 0].fill_betweenx(y=[-220, 220], x1=video[0] - time_stamps[0], x2=video[1] - time_stamps[0], color='#bbbbbb')
        self.yaw_time = axarr[0, 0].axvline(x=0, color='red', linewidth=2)
        axarr[0, 0].set_title('Yaw')

        axarr[0, 1].plot(time, pitch, 'blue')
        axarr[0, 1].set_ylim([-100, 30])
        axarr[0, 1].set_xlim([0, time[-1]])
        axarr[0, 1].set_xlabel('Seconds')
        axarr[0, 1].set_ylabel('Degrees')
        axarr[0, 1].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in video_list:
            axarr[0, 1].fill_betweenx(y=[-200, 200], x1=video[0] - time_stamps[0], x2=video[1] - time_stamps[0], color='#bbbbbb')
        self.pitch_time = axarr[0, 1].axvline(x=0, color='red', linewidth=2)
        axarr[0, 1].set_title('Pitch')

        axarr[1, 1].plot(time, roll, 'blue')
        axarr[1, 1].set_ylim([-180, 180])
        axarr[1, 1].set_xlim([0, time[-1]])
        axarr[1, 1].set_xlabel('Seconds')
        axarr[1, 1].set_ylabel('Degrees')
        axarr[1, 1].xaxis.set_ticks(np.arange(0, time[-1], 60))
        for video in video_list:
            axarr[1, 1].fill_betweenx(y=[-200, 200], x1=video[0] - time_stamps[0], x2=video[1] - time_stamps[0], color='#bbbbbb')
        self.roll_time = axarr[1, 1].axvline(x=0, color='red', linewidth=2)
        axarr[1, 1].set_title('Roll')

        axarr[1, 0].plot(time, height, 'blue')
        axarr[1, 0].set_xlim([0, time[-1]])
        axarr[1, 0].set_xlabel('Seconds')
        axarr[1, 0].set_ylabel('Meters')
        axarr[1, 0].xaxis.set_ticks(np.arange(0, time[-1], 60))
        ylim = axarr[1, 0].get_ylim()
        for video in video_list:
            axarr[1, 0].fill_betweenx(y=ylim, x1=video[0] - time_stamps[0], x2=video[1] - time_stamps[0], color='#bbbbbb')
        self.height_time = axarr[1, 0].axvline(x=0, color='red', linewidth=2)
        axarr[1, 0].set_ylim(ylim)
        axarr[1, 0].set_title('Height')

        self.show_all()

    def update_plot(self, time):
        self.yaw_time.set_xdata(time)
        self.pitch_time.set_xdata(time)
        self.roll_time.set_xdata(time)
        self.height_time.set_xdata(time)
        self.canvas.draw()
        self.canvas.flush_events()


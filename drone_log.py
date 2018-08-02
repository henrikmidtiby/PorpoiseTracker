import sys
import subprocess
import csv
import numpy as np
from datetime import datetime
import logging
from gtk_modules.dialogs import ProgressDialog


class DroneLog:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.log_file = None
        self.drone_log_data = {}
        self.height_difference = 0
        self.video_length = None

    def set_video_length(self, video_length):
        self.video_length = video_length

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
        yield False

    def parse_csv_log_generator(self, log_file):
        video_start_time = self.get_video_start_row(log=log_file)
        yield True
        self.parse_log(video_start_time, log=log_file)
        yield False

    def parse_log_generator(self, log_file):
        self.convert_log(log_file)
        video_start_time = self.get_video_start_row()
        yield True
        self.parse_log(video_start_time)
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
        yield False

    def convert_log(self, log_file):
        if sys.platform == 'linux':
            cmd = 'wine drone_log/TXTlogToCSVtool "' + log_file + '" ".temp/drone_log.csv"'
        else:
            cmd = 'drone_log/TXTlogToCSVtool "' + log_file + '" ".temp/drone_log.csv"'
        self.log_file = log_file
        res = subprocess.call(cmd, shell=True)
        self.logger.info('subprocess results {}'.format(res))

    def get_video_start_row(self, log=None):
        if log is None:
            log = '.temp/drone_log.csv'
        self.remove_null_bytes(log)
        with open(log, encoding='iso8859_10') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            field_names = reader.__next__()
            update_time_idx = field_names.index('CUSTOM.updateTime')
            video_idx = field_names.index('CUSTOM.isVideo')
            video_start_time = None
            video_length = []
            video_start_times = []
            recording_start = False
            time = None
            for row in reader:
                if row[update_time_idx] != '':
                    try:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S.%f').timestamp()
                    except ValueError:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S').timestamp()
                    if row[video_idx] == 'Recording':
                        if video_start_time is None:
                            video_start_time = time
                            recording_start = True
                    else:
                        if recording_start:
                            recording_start = False
                            video_length.append(time - video_start_time)
                            video_start_times.append(video_start_time)
                            video_start_time = None
                else:
                    self.logger.warning('drone log (%s) row error! row skipped.', self.log_file)
            if recording_start:
                video_length.append(time - video_start_time)
                video_start_times.append(video_start_time)
        keep_video_start_time = None
        keep_diff = np.Inf
        for l, t in zip(video_length, video_start_times):
            diff = abs(self.video_length - l)
            if diff < keep_diff:
                keep_diff = diff
                keep_video_start_time = t
        return keep_video_start_time

    def parse_log(self, video_start_timestamp, log=None):
        if log is None:
            log = '.temp/drone_log.csv'
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
            video_start_time = None
            recording_start = False
            for row in reader:
                if row[update_time_idx] != '':
                    try:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S.%f').timestamp()
                        date_time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S.%f')
                    except ValueError:
                        time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S').timestamp()
                        date_time = datetime.strptime(row[update_time_idx], '%Y/%m/%d %H:%M:%S')
                else:
                    time = 0
                    date_time = 0
                    self.logger.warning('drone log (%s) row error! row skipped.', self.log_file)
                if time >= video_start_timestamp:
                    if row[video_idx] == 'Recording':
                        if video_start_time is None:
                            recording_start = True
                            video_start_time = time
                            time = 0
                        else:
                            time = time - video_start_time
                        height = float(row[height_idx])
                        pitch = float(row[gimbal_pitch_idx])*np.pi/180
                        yaw = float(row[gimbal_yaw_idx])*np.pi/180
                        roll = float(row[gimbal_roll_idx])*np.pi/180
                        yaw_pitch_roll = (yaw, pitch, roll)
                        latitude = float(row[latitude_idx])
                        longitude = float(row[longitude_idx])
                        pos = (latitude, longitude)
                        self.drone_log_data.update({time: (height, yaw_pitch_roll, pos, date_time)})
                    else:
                        if recording_start:
                            break
        if not self.drone_log_data:
            self.logger.warning('No video recording found in the log (%s).', self.log_file)

    @staticmethod
    def remove_null_bytes(log):
        with open(log, 'rb') as fi:
            data = fi.read()
        with open(log, 'wb') as fo:
            fo.write(data.replace(b'\x00', b''))

    def get_data(self, time):
        diff = np.Inf
        height = None
        rotation = None
        pos = None
        date_time = None
        for t, height_and_rotation_and_pos_and_time in self.drone_log_data.items():
            d = abs(time - t)
            if d < diff:
                height = (height_and_rotation_and_pos_and_time[0] + self.height_difference)
                rotation = height_and_rotation_and_pos_and_time[1]
                pos = height_and_rotation_and_pos_and_time[2]
                date_time = height_and_rotation_and_pos_and_time[3]
                diff = d
        return height, rotation, pos, date_time

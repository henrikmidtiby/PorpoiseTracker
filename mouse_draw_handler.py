from collections import defaultdict, namedtuple
import numpy as np
from tracked_object import MarkObject
import csv
import cv2
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


class MouseDrawHandler:
    def __init__(self, mouse, draw_handler, video, drone_log, fov, grid_handler, allow_draw):
        self.data_tuple = namedtuple('data', ['length', 'time', 'lat', 'lon', 'easting', 'northing', 'zone', 'drone_height',
                                              'drone_yaw', 'drone_pitch', 'drone_roll', 'drone_lat', 'drone_lon'])
        self.window = None
        self.mouse_signals = mouse.signals
        self.mouse_signals.connect('left_mouse_press', self.pressed)
        self.mouse_signals.connect('left_mouse_release', self.released)
        self.mouse_signals.connect('left_mouse_move', self.move)
        self.draw_handler = draw_handler
        self.draw_handler.str_func = self.print_drone_height
        self.draw_handler.horizon = None
        self.video_handler = video
        self.drone_log = drone_log
        self.fov = fov
        self.grid_handler = grid_handler
        self.grid_handler.remove_marking_func = self.remove_marking
        self.grid_handler.update_draw_markings_func = self.update_draw_markings
        self.allow_draw = allow_draw
        self.last_pressed = None
        self.current_pos = None
        self.size = None
        self.markings = defaultdict(list)
        self.color = Gdk.RGBA(1, 0, 0, 1)
        self.video = None
        self.horizon_dict = self.get_horizon_dict()

    def print_drone_height(self, position):
        drone_height, rotation = self.drone_log.get_data(position * 1e-9)[:2]
        if drone_height is not None:
            string = u'Height: {:.1f}m Yaw: {:.1f}\N{DEGREE SIGN} Pitch: {:.1f}\N{DEGREE SIGN}'.format(drone_height, rotation[0]*180/np.pi, rotation[1]*180/np.pi)
            return string
        else:
            return False

    def toggle_draw_horizon(self):
        if self.draw_handler.horizon is not None:
            self.draw_handler.horizon = None
        else:
            self.draw_handler.horizon = self.draw_horizon
        self.video_handler.emit_draw_signal()

    def draw_horizon(self, position):
        self.fov.set_image_size(*self.video_handler.video_size)
        drone_rotation = self.drone_log.get_data(position * 1e-9)[1]
        if drone_rotation is not None:
            image_points = self.fov.get_horizon_and_world_corners(self.horizon_dict, drone_rotation)
            return image_points
        else:
            return False

    @staticmethod
    def get_horizon_dict():
        world_points = defaultdict(list)
        for x in np.linspace(-np.pi, np.pi, 100):
            point = (0, np.cos(x), np.sin(x))
            world_points['NS'].append(point)
        for x in np.linspace(-np.pi, np.pi, 100):
            point = (np.cos(x), 0, np.sin(x))
            world_points['EW'].append(point)
        for x in np.linspace(-np.pi, np.pi, 100):
            point = (np.cos(x), np.sin(x), 0)
            world_points['pitch0'].append(point)
        for x in np.linspace(-np.pi, np.pi, 100):
            point = (np.cos(x) / np.sqrt(2), np.sin(x) / np.sqrt(2), -1 / np.sqrt(2))
            world_points['pitch45'].append(point)
        return world_points

    def pressed(self, event, x, y, width, height):
        if self.video_handler.player_paused and self.allow_draw():
            self.last_pressed = np.array([x, y])
            self.size = (width, height)

    def released(self, event, x, y):
        if self.video_handler.player_paused and self.allow_draw():
            dist = np.linalg.norm(self.last_pressed - np.array([x, y]))
            position = self.video_handler.get_position()
            if dist < 5:
                self.add_point(x, y, position)
            else:
                self.add_line(x, y, position)

    def add_line(self, x, y, position):
        if self.allow_draw():
            draw_mark = np.array([self.last_pressed[0], self.last_pressed[1],
                                  x, y, self.size[0], self.size[1], position])
            drone_data = self.drone_log.get_data(position * 1e-9)
            image_points = np.array([[x, y], [self.last_pressed[0], self.last_pressed[1]]])
            scale = self.video_handler.video_size[0] / self.size[0]
            scaled_image_points = image_points * scale
            self.fov.set_image_size(*self.video_handler.video_size)
            world_points = self.fov.get_world_points(scaled_image_points, *drone_data[:3])
            length = np.linalg.norm(world_points[1]-world_points[0])
            scaled_image_point = np.mean(scaled_image_points, axis=0)
            world_point, zone = self.fov.get_world_point(scaled_image_point, drone_data[0], drone_data[1], drone_data[2], True)
            latlon = self.fov.convert_utm(world_point[0], world_point[1], zone)
            data = self.data_tuple(length, drone_data[-1], latlon[0], latlon[1], world_point[0], world_point[1], zone,
                                   drone_data[0], drone_data[1][0], drone_data[1][1], drone_data[1][2],
                                   drone_data[2][0], drone_data[2][1])
            line = MarkObject(self.grid_handler.current_name, self.color, draw_mark, data, self.video)
            self.grid_handler.add_marking(line)
            self.markings['lines'].append(line)
            self.update_draw_lines()
            self.draw_handler.signals.emit('line_draw', None)

    def add_point(self, x, y, position):
        if self.allow_draw():
            draw_mark = np.array([x, y, self.size[0], self.size[1], position])
            drone_data = self.drone_log.get_data(position * 1e-9)
            image_point = np.array([x, y])
            scale = self.video_handler.video_size[0] / self.size[0]
            scaled_image_point = image_point * scale
            self.fov.set_image_size(*self.video_handler.video_size)
            world_point, zone = self.fov.get_world_point(scaled_image_point, drone_data[0], drone_data[1], drone_data[2], True)
            latlon = self.fov.convert_utm(world_point[0], world_point[1], zone)
            data = self.data_tuple(None, drone_data[-1], latlon[0], latlon[1], world_point[0], world_point[1], zone,
                                   drone_data[0], drone_data[1][0], drone_data[1][1], drone_data[1][2],
                                   drone_data[2][0], drone_data[2][1])
            point = MarkObject(self.grid_handler.current_name, self.color, draw_mark, data, self.video)
            self.grid_handler.add_marking(point)
            self.markings['points'].append(point)
            self.update_draw_points()
            self.draw_handler.signals.emit('point_draw', None)

    def remove_marking(self, marking):
        for mark in self.markings['points']:
            if mark == marking:
                self.markings['points'].remove(mark)
                break
        for mark in self.markings['lines']:
            if mark == marking:
                self.markings['lines'].remove(mark)
                break
        self.update_draw_markings()

    def update_draw_markings(self):
        self.update_draw_lines()
        self.update_draw_points()
        self.video_handler.emit_draw_signal()

    def update_draw_points(self):
        points = []
        for p in self.markings['points']:
            points.append([p.marking, p.color, p.hide])
        self.draw_handler.points = points

    def update_draw_lines(self):
        lines = []
        for l in self.markings['lines']:
            lines.append([l.marking, l.color, l.hide])
        self.draw_handler.lines = lines

    def move(self, event, x, y):
        if self.video_handler.player_paused:
            if self.allow_draw():
                self.current_pos = np.array([x, y])
                position = self.video_handler.get_position()
                self.draw_handler.signals.emit('line_draw_live', self.last_pressed[0], self.last_pressed[1],
                                               x, y, self.size[0], self.size[1], position)

    def save(self, filename):
        with open(filename, 'w') as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            header = ['name', 'length', 'time', 'lat', 'lon', 'easting', 'northing', 'zone', 'drone height', 'drone yaw', 'drone pitch', 'drone roll',
                      'drone lat', 'drone lon', 'x1', 'y1', 'x2', 'y2', 'width', 'height', 'video position',
                      'red', 'green', 'blue', 'alpha', 'video name']
            writer.writerow(header)
            for p in self.markings['points']:
                marking = [p.marking[0], p.marking[1], None, None]
                marking.extend(p.marking[2:])
                row = [p.name]
                row.extend(p.data)
                row.extend(marking)
                color = [p.color.red, p.color.green, p.color.blue, p.color.alpha]
                row.extend(color)
                row.append(p.video)
                writer.writerow(row)
            for l in self.markings['lines']:
                row = [l.name]
                row.extend(l.data)
                row.extend(l.marking)
                color = [l.color.red, l.color.green, l.color.blue, l.color.alpha]
                row.extend(color)
                row.append(l.video)
                writer.writerow(row)

    def open_annotations(self, filename):
        with open(filename, 'r') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                if row.get('length'):
                    self.add_line_from_csv(row)
                else:
                    self.add_point_from_csv(row)

    def add_line_from_csv(self, row):
        draw_mark = np.array([float(row.get('x1', 0)), float(row.get('y1', 0)), float(row.get('x2', 0)), float(row.get('y2', 0)),
                              float(row.get('width', 0)), float(row.get('height', 0)), int(row.get('video position', 0))])
        data = self.data_tuple(float(row.get('length', 0)), row.get('time'), float(row.get('lat', 0)), float(row.get('lon', 0)),
                               float(row.get('easting', 0)), float(row.get('northing', 0)), row.get('zone'),
                               float(row.get('drone height', 0)), float(row.get('drone yaw', 0)), float(row.get('drone pitch', 0)), float(row.get('drone roll', 0)),
                               float(row.get('drone lat', 0)), float(row.get('drone lon', 0)))
        color = Gdk.RGBA(float(row.get('red', 1)), float(row.get('green', 0)), float(row.get('blue', 0)), float(row.get('alpha', 1)))
        line = MarkObject(row.get('name'), color, draw_mark, data, row.get('video name'))
        self.grid_handler.add_marking_from_csv(line)
        self.markings['lines'].append(line)
        self.update_draw_lines()

    def add_point_from_csv(self, row):
        draw_mark = np.array([float(row.get('x1', 0)), float(row.get('y1', 0)), float(row.get('width', 0)), float(row.get('height', 0)), int(row.get('video position', 0))])
        data = self.data_tuple(None, row.get('time'), float(row.get('lat', 0)), float(row.get('lon', 0)),
                               float(row.get('easting', 0)), float(row.get('northing', 0)), row.get('zone'),
                               float(row.get('drone height', 0)), float(row.get('drone yaw', 0)), float(row.get('drone pitch', 0)), float(row.get('drone roll', 0)),
                               float(row.get('drone lat', 0)), float(row.get('drone lon', 0)))
        color = Gdk.RGBA(float(row.get('red', 1)), float(row.get('green', 0)), float(row.get('blue', 0)), float(row.get('alpha', 1)))
        point = MarkObject(row.get('name'), color, draw_mark, data, row.get('video name'))
        self.grid_handler.add_marking_from_csv(point)
        self.markings['points'].append(point)
        self.update_draw_points()

    def export_video_gen(self, video_input_file, video_export_file):
        cap = cv2.VideoCapture(video_input_file)
        frame_rate = cap.get(cv2.CAP_PROP_FPS)
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_num = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(video_export_file, fourcc, frame_rate, (frame_width, frame_height))
        yield frame_num
        while cap.isOpened():
            pos = int(cap.get(cv2.CAP_PROP_POS_MSEC) * 1e6)
            ret, frame = cap.read()
            if ret:
                new_frame = frame.copy()
                for point in self.markings['points']:
                    if int(point.marking[-1]) == pos:
                        scale_width = frame_width / point.marking[2]
                        scale_height = frame_height / point.marking[3]
                        center = (int(point.marking[0]*scale_width), int(point.marking[1]*scale_height))
                        color = (int(point.color.green*255), int(point.color.blue*255), int(point.color.red*255))
                        cv2.circle(new_frame, center, 10, color, -1)
                for line in self.markings['lines']:
                    if int(line.marking[-1]) == pos:
                        scale_width = frame_width / line.marking[4]
                        scale_height = frame_height / line.marking[5]
                        point1 = (int(line.marking[0]*scale_width), int(line.marking[1]*scale_height))
                        point2 = (int(line.marking[2]*scale_width), int(line.marking[3]*scale_height))
                        color = (int(line.color.green * 255), int(line.color.blue * 255), int(line.color.red * 255))
                        cv2.line(new_frame, point1, point2, color, 5)
                out.write(new_frame)
            else:
                break
            yield True
        cap.release()
        out.release()
        yield False




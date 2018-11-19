from collections import defaultdict, namedtuple
import numpy as np
from tracked_object import MarkObject
import csv
import gi
gi.require_version('Gdk', '3.0')
from gi.repository import Gdk


class MouseDrawHandler:
    def __init__(self, mouse, draw_handler, video, drone_log, fov, grid_handler, allow_draw):
        self.data_tuple = namedtuple('data', ['length', 'time', 'lat', 'lon', 'drone_height',
                                              'drone_yaw', 'drone_pitch', 'drone_roll', 'drone_lat', 'drone_lon'])
        self.window = None
        self.mouse_signals = mouse.signals
        self.mouse_signals.connect('left_mouse_press', self.pressed)
        self.mouse_signals.connect('left_mouse_release', self.released)
        self.mouse_signals.connect('left_mouse_move', self.move)
        self.draw_handler = draw_handler
        self.draw_handler.str_func = self.print_drone_height
        self.draw_handler.horizon = self.draw_horizon
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

    def print_drone_height(self, position):
        drone_height, rotation = self.drone_log.get_data(position * 1e-9)[:2]
        if drone_height is not None:
            string = u'Height: {:.1f}m Yaw: {:.1f}\N{DEGREE SIGN} Pitch: {:.1f}\N{DEGREE SIGN}'.format(drone_height, rotation[0]*180/np.pi, rotation[1]*180/np.pi)
            self.draw_horizon(position)
            return string
        else:
            return False

    def draw_horizon(self, position):
        self.fov.set_image_size(*self.video_handler.video_size)
        drone_rotation = self.drone_log.get_data(position * 1e-9)[1]
        nsev = [(0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)]
        x_value, direction = self.fov.get_world_corner(nsev, drone_rotation)
        return x_value, direction

    def pressed(self, event, x, y, width, height):
        self.last_pressed = np.array([x, y])
        self.size = (width, height)

    def released(self, event, x, y):
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
            latlon = self.fov.get_gps_point(scaled_image_point, *drone_data[:3])
            data = self.data_tuple(length, drone_data[-1], latlon[0], latlon[1],
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
            latlon = self.fov.get_gps_point(scaled_image_point, *drone_data[:3])
            data = self.data_tuple(None, drone_data[-1], latlon[0], latlon[1],
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
        if self.allow_draw():
            self.current_pos = np.array([x, y])
            position = self.video_handler.get_position()
            self.draw_handler.signals.emit('line_draw_live', self.last_pressed[0], self.last_pressed[1],
                                           x, y, self.size[0], self.size[1], position)

    def save(self, file_name):
        with open(file_name, 'w') as csv_file:
            writer = csv.writer(csv_file, delimiter=',')
            header = ['Name', 'length', 'time', 'lat', 'lon', 'drone height', 'drone yaw', 'drone pitch', 'drone roll',
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

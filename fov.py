import csv
from math import tan, cos, sin, pi
import numpy as np
import scipy.io as sio
import utm
import cv2


class Fov:
    def __init__(self):
        self.image_size = None
        self.horizontal_fov = None
        self.vertical_fov = None
        self.camera_matrix = None
        self.dist_coefficients = None
        self.camera_matrix = None
        self.dist_coefficients = None

    def set_image_size(self, width, height):
        if self.camera_matrix is not None:
            corners = np.array([[[0, 0], [width, 0], [width, height], [0, height]]], dtype=np.float32)
            undist_corners = cv2.undistortPoints(corners, self.camera_matrix, self.dist_coefficients, P=self.camera_matrix)[0]
            w = (undist_corners[1][0] - undist_corners[0][0] + undist_corners[2][0] - undist_corners[3][0]) / 2
            h = (undist_corners[3][1] - undist_corners[0][1] + undist_corners[2][1] - undist_corners[1][1]) / 2
            self.image_size = (w, h)
        else:
            self.image_size = (width, height)

    def set_fov_from_file(self, fov_file):
        with open(fov_file, 'r') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            field_names = reader.__next__()
            horizontal_fov_idx = field_names.index('horizontal_fov')
            vertical_fov_idx = field_names.index('vertical_fov')
            row = reader.__next__()
            self.horizontal_fov = (float(row[horizontal_fov_idx])) * pi / 180
            self.vertical_fov = (float(row[vertical_fov_idx])) * pi / 180

    def set_camera_params(self, mat_file):
        mat_contents = sio.loadmat(mat_file, squeeze_me=True)
        self.camera_matrix = np.transpose(mat_contents['camera_matrix'])
        self.dist_coefficients = np.append(mat_contents['dist_coeff'], [0, 0])

    def set_fov(self, horizontal_fov, vertical_fov):
        self.horizontal_fov = horizontal_fov * pi / 180
        self.vertical_fov = vertical_fov * pi / 180

    @staticmethod
    def roll(roll):
        return np.array([[cos(roll), 0, sin(roll)], [0, 1, 0], [-sin(roll), 0, cos(roll)]])

    @staticmethod
    def pitch(pitch):
        return np.array([[1, 0, 0], [0, cos(pitch), -sin(pitch)], [0, sin(pitch), cos(pitch)]])

    @staticmethod
    def yaw(yaw):
        return np.array([[cos(yaw), -sin(yaw), 0], [sin(yaw), cos(yaw), 0], [0, 0, 1]])

    def rotation(self, yaw, pitch, roll):
        return self.yaw(yaw) @ self.pitch(pitch) @ self.roll(roll)

    def get_unit_vector(self, image_point):
        if self.camera_matrix is not None:
            undist_point = cv2.undistortPoints(np.array([[image_point]], dtype=np.float32), self.camera_matrix, self.dist_coefficients, P=self.camera_matrix)[0][0]
        else:
            undist_point = image_point
        image_center = np.array([self.image_size[0]/2, self.image_size[1]/2])
        image_point_from_center = undist_point - image_center
        horizontal_angle_per_pixel = self.horizontal_fov / self.image_size[0]
        vertical_angle_per_pixel = self.vertical_fov / self.image_size[1]
        x = tan(horizontal_angle_per_pixel * image_point_from_center[0])
        y = 1
        z = tan(- vertical_angle_per_pixel * image_point_from_center[1])
        vector = np.array([x, y, z])
        return vector

    def get_world_point(self, image_point, drone_height, yaw_pitch_roll, pos, return_zone=False):
        unit_vector = self.get_unit_vector(image_point)
        yaw_pitch_roll = (-yaw_pitch_roll[0], yaw_pitch_roll[1], yaw_pitch_roll[2])
        rotation_matrix = self.rotation(*yaw_pitch_roll)
        rotated_vector = rotation_matrix @ unit_vector
        ground_vector = rotated_vector / rotated_vector[2] * -drone_height
        east_north_zone = self.convert_gps(*pos)
        world_point = ground_vector[:2] + np.array(east_north_zone[:2])
        if return_zone:
            return world_point, east_north_zone[2:]
        else:
            return world_point

    def get_world_points(self, image_points, drone_height, yaw_pitch_roll, pos):
        world_points = []
        for image_point in image_points:
            world_point = self.get_world_point(image_point, drone_height, yaw_pitch_roll, pos)
            world_points.append(world_point)
        return world_points

    def get_gps_point(self, image_point, drone_height, yaw_pitch_roll, pos):
        world_point, zone = self.get_world_point(image_point, drone_height, yaw_pitch_roll, pos, True)
        lat, lon = self.convert_utm(world_point[0], world_point[1], zone)
        return lat, lon

    @staticmethod
    def convert_gps(lat, lon):
        east_north_zone = utm.from_latlon(lat, lon)
        return east_north_zone

    @staticmethod
    def convert_utm(east, north, zone):
        lat, lon = utm.to_latlon(east, north, *zone)
        return lat, lon
class MarkObject:
    def __init__(self, name, color, marking, data, from_video, log_file, fov_file):
        self.video = from_video
        self.log_file = log_file
        self.fov_file = fov_file
        self.name = name
        self.color = color
        self.marking = marking
        self.data = data
        self.hide = False


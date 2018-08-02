class MarkObject:
    def __init__(self, name, color, marking, data, from_video):
        self.video = from_video
        self.name = name
        self.color = color
        self.marking = marking
        self.data = data
        self.hide = False


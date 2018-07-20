import numpy as np


class MouseDraw:
    def __init__(self, mouse_signals, draw_signals, get_position):
        self.mouse_signals = mouse_signals
        self.draw_signals = draw_signals
        self.mouse_signals.connect('left_mouse_press', self.pressed)
        self.mouse_signals.connect('left_mouse_release', self.released)
        self.mouse_signals.connect('left_mouse_move', self.move)
        self.last_pressed = None
        self.current_pos = None
        self.size = None
        self.get_position = get_position

    def pressed(self, event, x, y, width, height):
        self.last_pressed = np.array([x, y])
        self.size = (width, height)

    def released(self, event, x, y):
        dist = np.linalg.norm(self.last_pressed - np.array([x, y]))
        position = self.get_position()
        if dist < 5:
            self.draw_signals.emit('point_draw', x, y, *self.size, position)
        else:
            self.draw_signals.emit('box_draw', *self.last_pressed, x, y, *self.size, position)

    def move(self, event, x, y):
        self.current_pos = np.array([x, y])
        position = self.get_position()
        self.draw_signals.emit('box_draw_live', *self.last_pressed, x, y, *self.size, position)

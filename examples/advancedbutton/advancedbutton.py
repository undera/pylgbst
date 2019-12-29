import time
import threading

DOUBLE_CLICK_TIME = 0.5
LONG_PRESS_TIME = 0.7


class AdvancedButton:
    def __init__(self, hub):
        self.state = 0
        self.last_pressed = 0
        self.press_time = None
        self.hub = hub
        self.hub.button.subscribe(self.pressed)
        self.click = ButtonAction()
        self.double_click = ButtonAction()
        self.long_press = ButtonAction()

    def pressed(self, state):
        if state == 2:
            return

        press_time = time.time()

        if state == 1:
            self.state = 1
            self.press_time = press_time
            return

        if state == 0 and self.state == 1:
            self.state = 0
            press_duration = press_time - self.press_time
        else:
            return

        if press_duration > LONG_PRESS_TIME:
            # long press
            self.long_press.notify()
            return

        if (press_time - self.last_pressed) < DOUBLE_CLICK_TIME:
            # double click
            self.last_pressed = 0
            self.double_click.notify()
            return

        # could be first of a double click, could be single click
        self.last_pressed = press_time

        def timeout():
            time.sleep(DOUBLE_CLICK_TIME)
            if self.last_pressed == press_time:
                # not clicked while sleeping
                # single click
                self.click.notify()

        threading.Thread(target=timeout).start()


class ButtonAction:
    def __init__(self):
        self.subscribers = set()

    def subscribe(self, callback):
        self.subscribers.add(callback)

    def unsubscribe(self, callback=None):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def notify(self):
        for subscriber in self.subscribers.copy():
            subscriber()

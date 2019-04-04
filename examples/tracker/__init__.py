import json
import logging
import os
import time
import traceback
from threading import Thread

import cv2
import imutils as imutils
from matplotlib import pyplot

from pylgbst.hub import MoveHub
from pylgbst.peripherals import COLOR_RED, COLOR_BLUE, COLOR_YELLOW

cascades_dir = '/usr/share/opencv/haarcascades'
face_cascade = cv2.CascadeClassifier(cascades_dir + '/haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cascades_dir + '/haarcascade_smile.xml')

LINE_THICKNESS = 2


class FaceTracker(MoveHub):
    def __init__(self, connection=None):
        super(FaceTracker, self).__init__(connection)
        self._is_smile_on = False
        self.cur_img = None
        self.cur_face = None
        self.cur_smile = None
        self.smile_counter = 0

    def capture(self):
        logging.info("Starting cam...")
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920 / 2)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080 / 2)
        # cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        # cap.set(cv2.CAP_PROP_XI_AUTO_WB, 1)
        # cap.set(cv2.CAP_PROP_XI_AEAG, 1)

        size = (int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))

        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        fps = cap.get(cv2.CAP_PROP_FPS)
        video = cv2.VideoWriter('output_%d.avi' % int(time.time()), fourcc, fps, size)

        try:
            while True:
                flag, img = cap.read()
                if self.cur_face is not None:
                    (x, y, w, h) = self.cur_face
                    if LINE_THICKNESS:
                        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255,), LINE_THICKNESS)
                video.write(img)
                self.cur_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                logging.debug("Got frame")
        finally:
            logging.info("Releasing cam...")
            cap.release()
            video.release()

    def _find_face(self):
        bodies, rejects, weights = face_cascade.detectMultiScale3(self.cur_img, 1.5, 5, outputRejectLevels=True)
        if len(bodies):
            logging.debug("Bodies: %s / Weights: %s", bodies, weights)
        else:
            return None

        items = []
        for n in range(0, len(bodies)):
            items.append((bodies[n], weights[n]))

        self.cur_face = None
        return self._reduce(bodies)

    def _reduce(self, values):
        res = None
        for x, y, w, h in values:
            if res is None:
                res = (x, y, w, h)
            else:
                new_xy = (min(x, res[0]), min(y, res[1]))
                res = new_xy + (max(x + w, res[0] + res[2]) - new_xy[0], max(y + h, res[1] + res[3]) - new_xy[1])
        return res

    def _find_smile(self, cur_face):
        roi_color = None
        if cur_face is not None:
            (x, y, w, h) = cur_face
            roi_color = self.cur_img[y:y + h, x:x + w]
            smile = self._reduce(smile_cascade.detectMultiScale(roi_color, 1.5, 20))
        else:
            smile = None

        if not smile:
            self.cur_smile = None
            self.smile_counter -= 1
        else:
            (ex, ey, ew, eh) = smile
            self.cur_smile = (ex, ey, ew, eh)
            if LINE_THICKNESS:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 255, 0), LINE_THICKNESS)
            self.smile_counter += 1

        logging.info("Smile counter: %s", self.smile_counter)
        if self.smile_counter > 2:
            self.smile_counter = 2
            self._smile(True)
        if self.smile_counter < 0:
            self.smile_counter = 0
            self._smile(False)

    def _smile(self, on=True):
        if on and not self._is_smile_on:
            self._is_smile_on = True
            self.motor_B.angled(-90, 0.5)
            self.led.set_color(COLOR_RED)

        if not on and self._is_smile_on:
            self._is_smile_on = False
            self.motor_B.angled(90, 0.5)

    def _find_color(self):
        # from https://www.pyimagesearch.com/2015/09/14/ball-tracking-with-opencv/
        # and https://thecodacus.com/opencv-object-tracking-colour-detection-python/#.W2DHFd_IQsM

        blurred = cv2.GaussianBlur(self.cur_img, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)

        try:
            # having color values in file allows finding values easier
            with open(os.path.join(os.path.dirname(__file__), "color.json")) as fhd:
                data = json.loads(fhd.read())
                lower = tuple(data[0])
                upper = tuple(data[1])
        except BaseException:
            logging.debug("%s", traceback.format_exc())
            lower = (100, 100, 100,)
            upper = (130, 255, 255,)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.erode(mask, None, iterations=5)
        mask = cv2.dilate(mask, None, iterations=5)

        # if not (int(time.time()) % 2):
        #    self.cur_img = mask

        ret, thresh = cv2.threshold(mask, 20, 255, 0)
        cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]

        return self._reduce([cv2.boundingRect(c) for c in cnts])

    def _auto_pan(self, cur_face):
        (x, y, w, h) = cur_face
        height, width, channels = self.cur_img.shape

        cam_center = (width / 2, height / 2)
        face_center = (x + w / 2, y + h / 2)

        horz = 1.5 * (face_center[0] - cam_center[0]) / float(width)
        vert = 0.7 * (face_center[1] - cam_center[1]) / float(height)

        logging.info("Horiz %.3f, vert %3f", horz, vert)
        if abs(horz) < 0.1:
            horz = 0
        if abs(vert) < 0.15:
            vert = 0

        self.motor_external.start_power(horz)
        self.motor_A.start_power(-vert)

    def main(self):
        thr = Thread(target=self.capture)
        thr.setDaemon(True)
        thr.start()

        while self.cur_img is None:
            pass

        plt = pyplot.imshow(self.cur_img)
        pyplot.tight_layout()
        pyplot.ion()
        pyplot.show()

        try:
            while thr.isAlive() and self.connection.is_alive():
                self._process_picture(plt)
        finally:
            self._smile(False)

    def _process_picture(self, plt):
        self.cur_face = self._find_face()
        # self.cur_face = self._find_color()

        if self.cur_face is None:
            self.motor_external.stop()
            self.motor_AB.stop()
            if not self._is_smile_on:
                self.led.set_color(COLOR_BLUE)
        else:
            if not self._is_smile_on:
                self.led.set_color(COLOR_YELLOW)

            self._auto_pan(self.cur_face)
            self._find_smile(self.cur_face)
        plt.set_array(self.cur_img)
        logging.debug("Updated frame")
        pyplot.pause(0.02)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        hub = FaceTracker()
        hub.main()
    finally:
        pass
        # conn.disconnect()

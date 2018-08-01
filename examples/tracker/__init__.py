import json
import logging
import os
import traceback
from threading import Thread

import cv2
import imutils as imutils
from matplotlib import pyplot

from pylgbst import get_connection_auto
from pylgbst.comms import DebugServerConnection
from pylgbst.movehub import MoveHub


class FaceTracker(MoveHub):
    def __init__(self, connection=None):
        super(FaceTracker, self).__init__(connection)
        self.cur_img = None

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
        video = cv2.VideoWriter('output.avi', fourcc, fps, size)

        try:
            while True:
                flag, img = cap.read()
                self.cur_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                logging.debug("Got frame")
                video.write(self.cur_img)
        finally:
            logging.info("Releasing cam...")
            cap.release()
            video.release()

    face_cascade = cv2.CascadeClassifier('/usr/share/opencv/haarcascades/' + 'haarcascade_frontalface_default.xml')

    def _find_faces(self):
        bodies, rejects, weights = self.face_cascade.detectMultiScale3(self.cur_img, 1.5, 5, outputRejectLevels=True)
        return bodies, weights

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
        except:
            logging.debug("%s", traceback.format_exc())
            lower = (100, 100, 100,)
            upper = (130, 255, 255,)
        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # if not (int(time.time()) % 2):
        #    self.cur_img = mask

        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if imutils.is_cv2() else cnts[1]

        return [cv2.boundingRect(c) for c in cnts], (0,) * len(cnts)

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

        self.motor_external.constant(horz)
        self.motor_A.constant(-vert)

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

        cur_face = (0, 0, 0, 0)
        while thr.isAlive():
            # bodies, weights = self._find_color()
            bodies, weights = self._find_faces()

            if len(bodies):
                logging.debug("Bodies: %s / Weights: %s", bodies, weights)
            else:
                self.motor_external.stop()
                self.motor_AB.stop()

            items = []
            for n in range(0, len(bodies)):
                items.append((bodies[n], weights[n]))

            for item in sorted(items, key=lambda i: i[1], reverse=True):
                cur_face = item[0]

                self._auto_pan(cur_face)
                break

            (x, y, w, h) = cur_face
            cv2.rectangle(self.cur_img, (x, y), (x + w, y + h), (255, 0, 0), 2)

            plt.set_array(self.cur_img)
            logging.debug("Updated frame")
            pyplot.pause(0.02)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    try:
        conn = DebugServerConnection()
    except BaseException:
        logging.debug("Failed to use debug server: %s", traceback.format_exc())
        conn = get_connection_auto()

    try:
        hub = FaceTracker(conn)
        hub.main()
    finally:
        pass
        # conn.disconnect()


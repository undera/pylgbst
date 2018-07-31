import logging
import traceback
from threading import Thread

import cv2
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

        try:
            while True:
                flag, img = cap.read()
                self.cur_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                logging.debug("Got frame")

        finally:
            logging.info("Releasing cam...")
            cap.release()

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

        face_cascade = cv2.CascadeClassifier('/usr/share/opencv/haarcascades/' + 'haarcascade_frontalface_default.xml')
        # face_cascade = cv2.CascadeClassifier('/usr/share/opencv/haarcascades/' + 'haarcascade_frontalface_alt.xml')
        # face_cascade = cv2.CascadeClassifier('/usr/share/opencv/haarcascades/' + 'haarcascade_frontalface_alt2.xml')

        idle = 0
        while thr.isAlive():
            bodies, rejects, weights = face_cascade.detectMultiScale3(self.cur_img, 1.5, 5, outputRejectLevels=True)

            if len(bodies):
                idle = 0
                logging.debug("Bodies: %s / Weights: %s", bodies, weights)
            elif idle >= 1:
                logging.info("Stop motors because of idle")
                self.motor_external.stop()
                self.motor_AB.stop()
                idle = 0
            else:
                idle += 1

            items = []
            for n in range(0, len(bodies)):
                (x, y, w, h) = bodies[n]
                cv2.rectangle(self.cur_img, (x, y), (x + w, y + h), (255, 0, 0), 2)
                items.append((bodies[n], weights[n]))

            for item in sorted(items, key=lambda x: x[1], reverse=True):
                (x, y, w, h) = item[0]
                height, width, channels = self.cur_img.shape
                cam_center = (width / 2, height / 2)
                face_center = (x + w / 2, y + h / 2)

                horz = 1.5 * (face_center[0] - cam_center[0]) / float(width)
                vert = 0.7 * (face_center[1] - cam_center[1]) / float(height)

                logging.info("Horiz %s, vert %s, weight: %s", horz, vert, item[1])

                if abs(horz) < 0.1:
                    horz = 0
                if abs(vert) < 0.1:
                    vert = 0

                self.motor_external.constant(horz)
                self.motor_AB.constant(-vert)
                break

            plt.set_array(self.cur_img)
            # pyplot.draw()
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

# obj = A()
# obj.main()

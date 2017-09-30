import logging
import matplotlib.pyplot as plt
from threading import Thread

import numpy
from PIL import Image


class Tracer(object):
    def __init__(self, fname):
        super(Tracer, self).__init__()
        self.orig = Image.open(fname)
        self.conv1 = self.orig.convert("1")
        self.src = numpy.asarray(self.conv1)
        self.dst = numpy.copy(self.src)
        self.dst.fill(False)
        self.mark = numpy.copy(self.dst)
        # start in center
        self.height, self.width = self.dst.shape
        self.posy = self.height / 2
        self.posx = self.width / 2

    def trace(self):
        while self._has_unchecked_pixels():
            # go circles to find a pixel in src
            self._spiral_till_pixel()

            # move until we find new pixels
            self._move_while_you_can()

    def _has_unchecked_pixels(self):
        ix, iy = numpy.where(self.mark == False)
        return len(ix) or len(iy)

    def _spiral_till_pixel(self):
        radius = 1
        direction = 0
        offset = 0
        while self._has_unchecked_pixels():
            in_lower = self.posy < self.height and self.posx < self.width
            in_upper = self.posy >= 0 and self.posx >= 0
            if in_lower and in_upper and not self.mark[self.posy][self.posx]:
                if self.src[self.posy][self.posx]:
                    return

                self.mark[self.posy][self.posx] = True

            if direction == 0:
                self.posx += 1
                self.posy += 0
            elif direction == 1:
                self.posx += 0
                self.posy += 1
            elif direction == 2:
                self.posx += -1
                self.posy += 0
            elif direction == 3:
                self.posx += 0
                self.posy += -1
            else:
                pass

            offset += 1
            if offset >= radius:
                # time.sleep(0.01)
                offset = 0
                direction += 1
                if direction > 3:
                    direction = 0

                if direction in (0, 2):
                    radius += 1

        raise KeyboardInterrupt("End of image")  # end of image

    def _move_while_you_can(self):
        logging.debug("%s %s", self.posy, self.posx)
        self.mark[self.posy][self.posx] = True
        self.dst[self.posy][self.posx] = True
        # self.posx += 1
        # self.posy += 1


class TracerVisualizer(object):
    def __init__(self, tracer):
        """
        :type tracer: Tracer
        """
        self.tracer = tracer

    def run(self):
        tracer = self.tracer

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(nrows=2, ncols=2)
        ax1.imshow(tracer.orig)
        ax2.imshow(tracer.src)
        plt.show(block=False)

        thr = Thread(target=tracer.trace)
        thr.setDaemon(True)
        thr.start()

        while plt.get_fignums():  # weird trick to react on close
            ax3.set_title("%s:%s" % (tracer.posx, tracer.posy))
            ax3.imshow(tracer.mark, cmap='gray')
            ax4.imshow(tracer.dst, cmap='gray')
            plt.pause(0.5)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    trc = Tracer("/tmp/truck.png")

    TracerVisualizer(trc).run()

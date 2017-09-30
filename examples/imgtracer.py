import logging
import matplotlib.pyplot as plt
import time
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

    def trace(self):
        width, height = self.dst.shape
        self.dst.fill(False)
        mark = numpy.copy(self.dst)

        # start in center
        posx = width / 2
        posy = height / 2

        # go circles to find a pixel in src

        # move until we find new pixels
        # repeat

        for x in range(0, width):
            for y in range(0, height):
                time.sleep(0.01)
                if (x + y) % 2 == 0:
                    self.dst[x][y] = True


class TracerVisualizer(object):
    def __init__(self, tracer):
        """
        :type tracer: Tracer
        """
        self.tracer = tracer

    def run(self):
        tracer = self.tracer
        thr = Thread(target=tracer.trace)
        thr.setDaemon(True)
        thr.start()

        fig, (ax1, ax2, ax3) = plt.subplots(nrows=1, ncols=3)
        ax1.imshow(tracer.orig)
        ax2.imshow(tracer.conv1)
        plt.show(block=False)

        while plt.get_fignums():  # weird trick to react on close
            ax3.imshow(tracer.dst, cmap='gray')
            plt.pause(0.01)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    trc = Tracer("/tmp/truck.png")

    TracerVisualizer(trc).run()

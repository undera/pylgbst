import json
import logging
import matplotlib.pyplot as plt
import time
from threading import Thread

import numpy
from PIL import Image


class Tracer(object):
    def __init__(self, fname):
        super(Tracer, self).__init__()
        self.threshold = 64
        self.orig_fname = fname
        self.orig = Image.open(fname)
        self.conv1 = self.remove_transparency(self.orig)
        self.conv1 = self.conv1.convert("L")
        self.src = numpy.asarray(self.conv1)
        self.dst = numpy.copy(self.src)
        self.dst.fill(False)
        self.mark = numpy.copy(self.dst)
        # start in center
        self.height, self.width = self.dst.shanape[0:2]
        self.posy = self.height / 2
        self.posx = self.width / 2
        self.lines = []

    def remove_transparency(self, im, bg_colour=(255, 255, 255)):
        # from https://stackoverflow.com/questions/35859140/remove-transparency-alpha-from-any-image-using-pil
        # Only process if image has transparency (http://stackoverflow.com/a/1963146)
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):

            # Need to convert to RGBA if LA format due to a bug in PIL (http://stackoverflow.com/a/1963146)
            alpha = im.convert('RGBA').split()[-1]

            # Create a new background image of our matt color.
            # Must be RGBA because paste requires both images have the same format
            # (http://stackoverflow.com/a/8720632  and  http://stackoverflow.com/a/9459208)
            bg = Image.new("RGBA", im.size, bg_colour + (255,))
            bg.paste(im, mask=alpha)
            return bg

        else:
            return im

    def trace(self):
        while self._has_unchecked_pixels():
            # go circles to find a pixel in src
            if not self._spiral_till_pixel():
                break

            # move until we find new pixels
            self._move_while_you_can()

        logging.info("Done")
        with open(self.orig_fname + ".json", "wt") as fhd:
            fhd.write(json.dumps(self.lines))

    def _has_unchecked_pixels(self):
        ix, iy = numpy.where(self.mark == False)  # FIXME: highly inefficient
        return len(ix) or len(iy)

    def is_src(self, posx, posy):
        return self.src[posy][posx] < self.threshold

    def _spiral_till_pixel(self):  # TODO: optimize it, maybe use different algo (not spiral, just walkthrough?)
        radius = 1
        direction = 0
        offset = 0
        while self._has_unchecked_pixels():
            in_lower = self.posy < self.height and self.posx < self.width
            in_upper = self.posy >= 0 and self.posx >= 0
            if in_lower and in_upper and not self.mark[self.posy][self.posx]:
                if self.is_src(self.posx, self.posy):
                    return True

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
                raise ValueError()

            offset += 1
            if offset >= radius:
                # time.sleep(0.01)
                offset = 0
                direction += 1
                if direction > 3:
                    direction = 0

                if direction in (0, 2):
                    radius += 1

        return False

    def _move_while_you_can(self):
        # time.sleep(0.1)
        logging.debug("%s:%s=%s", self.posy, self.posx, self.src[self.posy][self.posx])

        dirs = self._check_directions()  # TODO: use stack of this knowledge to speed-up walktrough
        dx, dy, length = self._get_best_direction(dirs)

        self.dst[self.posy][self.posx] = True
        self.mark[self.posy][self.posx] = True

        line = {
            "x1": self.posx, "y1": self.posy,
            "x2": self.posx + dx * length, "y2": self.posy + dy * length,
            "len": length
        }
        self.lines.append(line)
        logging.info("%s", line)

        for n in range(0, length):
            self.posy += dy
            self.posx += dx
            self.dst[self.posy][self.posx] = True
            self.mark[self.posy][self.posx] = True

    def _check_directions(self):
        dirs = {
            -1: {-1: 0, 0: 0, 1: 0},
            0: {-1: 0, 0: 0, 1: 0},
            1: {-1: 0, 0: 0, 1: 0},
        }
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue

                length = 1
                while True:
                    cx = self.posx + length * dx
                    cy = self.posy + length * dy

                    if not (0 <= cx < self.width) or not (0 <= cy < self.height):
                        break

                    if not self.is_src(cx, cy) or self.mark[cy][cx]:
                        break

                    dirs[dy][dx] = length
                    length += 1

        return dirs

    def _get_best_direction(self, dirs):
        bestlen = 0
        bestx = 0
        besty = 0
        for y in dirs:
            for x in dirs[y]:
                if dirs[y][x] > bestlen:
                    bestlen = dirs[y][x]
                    bestx = x
                    besty = y
        return bestx, besty, bestlen


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
        ax2.imshow(tracer.src, cmap='binary')
        plt.show(block=False)

        thr = Thread(target=tracer.trace)
        thr.setDaemon(True)
        thr.start()

        while plt.get_fignums():  # weird trick to react on close
            ax3.set_title("%s:%s" % (tracer.posx, tracer.posy))
            ax3.imshow(tracer.mark, cmap='gray')
            ax4.imshow(tracer.dst, cmap='gray')
            plt.pause(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    trc = Tracer("test3.png")

    TracerVisualizer(trc).run()
    time.sleep(5)

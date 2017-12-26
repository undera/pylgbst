def lego(plotter, t):
    h = t * 5.0
    w = t * 3.0

    plotter.move(-t * 2.0, 0)
    l(h, plotter, t, w)
    plotter.move(0, w + t)
    e(h, plotter, t, w)
    plotter.move(0, w + t)
    g(plotter, t)
    plotter.move(0, w + t)
    o(plotter, t)


def o(plotter, t):
    # O
    plotter.move(t, 0)
    plotter.line(3 * t, 0)
    plotter.line(t, t)
    plotter.line(0, t)
    plotter.line(-t, t)
    plotter.line(-3 * t, 0)
    plotter.line(-t, -t)
    plotter.line(0, -t)
    plotter.line(t, -t)
    plotter.move(0, t)
    plotter.line(3 * t, 0)
    plotter.line(0, t)
    plotter.line(-3 * t, 0)
    plotter.line(0, -t)


def g(plotter, t):
    # G
    plotter.move(t, 0)
    plotter.line(3 * t, 0)
    plotter.line(t, t)
    plotter.line(0, t)
    plotter.line(-t, t)
    plotter.line(-t, 0)
    plotter.line(0, -t)
    plotter.line(t, 0)
    plotter.line(0, -t)
    plotter.line(-3 * t, 0)
    plotter.line(0, t)
    plotter.line(t * 0.25, 0)
    plotter.line(0, -t * 0.25)
    plotter.line(t * 0.75, 0)
    plotter.line(0, t * 1.25)
    plotter.line(-3 * t, 0)
    plotter.line(0, -t)
    plotter.line(t, 0)
    plotter.line(0, -t)
    plotter.line(t, -t)
    plotter.move(-t, 0)


def e(h, plotter, t, w):
    # E
    plotter.line(h, 0)
    plotter.line(0, w)
    plotter.line(-t, 0)
    plotter.line(0, -2 * t)
    plotter.line(-t, 0)
    plotter.line(0, t)
    plotter.line(-t, 0)
    plotter.line(0, -t)
    plotter.line(-t, 0)
    plotter.line(0, 2 * t)
    plotter.line(-t, 0)
    plotter.line(0, -w)


def l(h, plotter, t, w):
    # L
    plotter.line(h, 0)
    plotter.line(0, t)
    plotter.line(-(h - t), 0)
    plotter.line(0, 2 * t)
    plotter.line(-t, 0)
    plotter.line(0, -w)

import six

from . import *

robot = Vernie()

robot.say('type commands')


def confirmation(_):
    robot.say("ok")


while True:
    # noinspection PyUnresolvedReferences
    cmd = six.moves.input("> ")
    robot.interpret_command(cmd, confirmation)

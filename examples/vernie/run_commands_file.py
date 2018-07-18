import sys

from . import *

robot = Vernie()

robot.say("commands from file")


def confirmation(command):
    robot.say(command[0])


with open(os.path.join(os.path.dirname(__file__), "vernie.commands")) as fhd:
    for cmd in fhd.readlines():
        sys.stdout.write("%s" % cmd)
        robot.interpret_command(cmd, confirmation)

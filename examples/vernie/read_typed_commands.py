from . import *

robot = Vernie()

robot.say('type commands')


def confirmation(_):
    robot.say("ok")


while True:
    cmd = input("> ")
    robot.interpret_command(cmd, confirmation)

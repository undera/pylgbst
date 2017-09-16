from vernie import *

robot = Vernie()

robot.say('type commands')


def confirmation(cmd):
    robot.say("ok")


while True:
    # noinspection PyUnresolvedReferences
    cmd = six.moves.input("COMMAND >")
    robot.interpret_command(cmd, confirmation)

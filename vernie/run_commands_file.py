from vernie import *

robot = Vernie()

robot.say("commands from file")


def confirmation(cmd):
    robot.say(cmd[0])


with open("vernie.commands") as fhd:
    for cmd in fhd.readlines():
        sys.stdout.write("%s" % cmd)
        robot.interpret_command(cmd, confirmation)

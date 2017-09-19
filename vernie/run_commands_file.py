from vernie import *

robot = Vernie()

robot.say("commands from file")


def confirmation(command):
    robot.say(command[0])


with open("vernie.commands") as fhd:
    for cmd in fhd.readlines():
        sys.stdout.write("%s" % cmd)
        robot.interpret_command(cmd, confirmation)

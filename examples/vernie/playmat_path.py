from . import *

robot = Vernie()

robot.say("Hello")

robot.move(FORWARD)
robot.move(FORWARD)
robot.turn(RIGHT)
robot.move(FORWARD)
robot.turn(LEFT)
robot.move(FORWARD)
robot.turn(RIGHT)
robot.move(BACKWARD)
robot.move(BACKWARD)
robot.turn(LEFT)
robot.move(FORWARD)
robot.move(FORWARD)
robot.turn(RIGHT)
robot.move(FORWARD)
robot.turn(RIGHT)
robot.move(FORWARD, 3)
robot.turn(LEFT)
robot.turn(LEFT)
robot.move(BACKWARD, 2)

robot.say("Goodbye")

from examples.automata import Automata

from pylgbst.peripherals import *


# this program is written by Sofia in early 2019

def action_by_color(color):
    if color == COLOR_BLUE:
        bot.forward()
    if color == COLOR_RED:
        bot.backward()
    if color == COLOR_WHITE:
        bot.right()
    if color == COLOR_YELLOW:
        bot.left()


def read_color():
    bot.feed_tape()
    color = bot.get_color()
    print(COLORS[color])
    return color


bot = Automata()
number = 0
color = None
while color != COLOR_NONE:
    color = read_color()
    number = number + 1
    action_by_color(color)

print(number)

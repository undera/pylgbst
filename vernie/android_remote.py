"""
To use it, install this android app:
   https://play.google.com/store/apps/details?id=com.mscino.sensornode
Then open app on phone and choose "Stream" => "Stream live data (XML)".
Check the "Accelerometer" option and put your IP address into corresponding filed.
Specify port there as 8999, and enable streaming. Then run this script on computer.
"""
import logging
import socket
import time

from vernie import Vernie

host = ''
port = 8999
running = True


def on_btn(pressed):
    global running
    if pressed:
        running = False


def decode_xml(messageString):
    parts = messageString.split("</")
    xxx = float(parts[1][parts[1].rfind('>') + 1:])
    yyy = float(parts[2][parts[2].rfind('>') + 1:])
    zzz = float(parts[3][parts[3].rfind('>') + 1:])
    return ranged(xxx), ranged(yyy), ranged(zzz)


def ranged(param):
    return float(param / 10)


udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
udp_sock.settimeout(0)

logging.basicConfig(level=logging.INFO)
robot = Vernie()
robot.button.subscribe(on_btn)
robot.motor_AB.stop()

try:
    udp_sock.bind((host, port))
    time.sleep(1)

    while running:
        message = ""
        while True:
            try:
                data = udp_sock.recv(8192)
                message = data
            except KeyboardInterrupt:
                raise
            except:
                break

        if not message:
            time.sleep(0.05)
            continue

        messageString = message.decode("utf-8")
        a, b, c = decode_xml(messageString)
        sa = int(10 * (c + b / 2.0)) / 10.0
        sb = int(10 * (c - b / 2.0)) / 10.0
        logging.info("SpeedA=%s, SpeedB=%s", sa, sb)
        robot.motor_AB.constant(sa, sb, async=True)
        time.sleep(0.5)
finally:
    robot.motor_AB.stop()
    udp_sock.close()

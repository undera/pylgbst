# coding=utf-8
import hashlib
import os
import re
import subprocess
import sys
import traceback

from pylgbst import *
from pylgbst.comms import DebugServerConnection

try:
    import gtts


    def say(text):
        return
        if isinstance(text, str):
            text = text.decode("utf-8")
        md5 = hashlib.md5(text.encode('utf-8')).hexdigest()
        fname = "/tmp/%s.mp3" % md5
        if not os.path.exists(fname):
            myre = re.compile('[[A-Za-z]', re.UNICODE)
            lang = 'en' if myre.match(text) else 'ru'

            logging.getLogger('requests').setLevel(logging.getLogger('').getEffectiveLevel())
            tts = gtts.gTTS(text=text, lang=lang, slow=False)
            tts.save(fname)

        with open(os.devnull, 'w') as fnull:
            subprocess.call("mplayer %s" % fname, shell=True, stderr=fnull, stdout=fnull)
except BaseException:
    def say(text):
        sys.stdout.write("%s\n", text)

forward = FORWARD = right = RIGHT = 1
backward = BACKWARD = left = LEFT = -1
straight = STRAIGHT = 0

SPEECH_LANG_MAP = {
    'en': {
        'ready': "Vernie the Robot is ready.",
        "commands help": "Available commands are: "
                         "forward, backward, turn left, turn right, "
                         "head left, head right, head straight and say",
        "finished": "Thank you! Robot is now turning off"
    },
    "ru": {
        "ready": "Робот Веернии 01 готов к работе",
        "type commands": "печатайте команды",
        "ok": "хорошо",
        "commands help": "Доступные команды это: вперёд, назад, поворот влево, поворот вправо, "
                         "голову влево, голову вправо, голову прямо, скажи",
        "Finished": "Робот завершает работу. Спасибо!",
        "commands from file": "Исполняю команды из файла",
    }
}

VERNIE_TO_MOTOR_DEGREES = 2.6
VERNIE_SINGLE_MOVE = 430


class Vernie(MoveHub):
    def __init__(self, language='en'):
        try:
            conn = DebugServerConnection()
        except BaseException:
            logging.debug("Failed to use debug server: %s", traceback.format_exc())
            conn = BLEConnection().connect()

        super(Vernie, self).__init__(conn)
        self.language = language

        while True:
            required_devices = (self.color_distance_sensor, self.motor_external)
            if None not in required_devices:
                break
            log.debug("Waiting for required devices to appear: %s", required_devices)
            time.sleep(1)

        self._head_position = 0
        self.motor_external.subscribe(self._external_motor_data)

        self._reset_head()
        self.say("ready")
        time.sleep(1)

    def say(self, phrase):
        if phrase in SPEECH_LANG_MAP[self.language]:
            phrase = SPEECH_LANG_MAP[self.language][phrase]
        say(phrase)

    def _external_motor_data(self, data):
        log.debug("External motor position: %s", data)
        self._head_position = data

    def _reset_head(self):
        self.motor_external.timed(1, -0.2)
        self.head(RIGHT, angle=45)

    def head(self, direction=RIGHT, angle=25, speed=0.1):
        if direction == STRAIGHT:
            angle = -self._head_position
            direction = 1

        self.motor_external.angled(direction * angle, speed)

    def turn(self, direction, degrees=90, speed=0.3):
        #self.head(STRAIGHT, speed=0.5)
        #self.head(direction, 35, 1)
        self.motor_AB.angled(int(VERNIE_TO_MOTOR_DEGREES * degrees), speed * direction, -speed * direction)
        #self.head(STRAIGHT, speed=0.5)

    def move(self, direction, distance=1, speed=0.2):
        #self.head(STRAIGHT, speed=0.5)
        self.motor_AB.angled(distance * VERNIE_SINGLE_MOVE, speed * direction, speed * direction)

    def interpret_command(self, cmd, confirm):
        cmd = cmd.strip().lower().split(' ')
        if cmd[0] in ("head", "голова", "голова"):
            if cmd[-1] in ("right", "вправо", "направо"):
                confirm(cmd)
                self.head(RIGHT)
            elif cmd[-1] in ("left", "влево", "налево"):
                confirm(cmd)
                self.head(LEFT)
            else:
                confirm(cmd)
                self.head(STRAIGHT)
        elif cmd[0] in ("say", "скажи", "сказать"):
            say(' '.join(cmd[1:]))
        elif cmd[0] in ("end", "конец"):
            self.say("finished")
            raise KeyboardInterrupt()
        elif cmd[0] in ("forward", "вперёд", "вперед"):
            try:
                dist = int(cmd[-1])
            except BaseException:
                dist = 1
            confirm(cmd)
            self.move(FORWARD, distance=dist)
        elif cmd[0] in ("backward", "назад"):
            try:
                dist = int(cmd[-1])
            except BaseException:
                dist = 1
            confirm(cmd)
            self.move(BACKWARD, distance=dist)
        elif cmd[0] in ("turn", "поворот", 'повернуть'):
            if cmd[-1] in ("right", "вправо", "направо"):
                confirm(cmd)
                self.turn(RIGHT)
            elif cmd[-1] in ("left", "влево", "налево"):
                confirm(cmd)
                self.turn(LEFT)
            else:
                confirm(cmd)
                self.turn(RIGHT, degrees=180)
        else:
            self.say("Unknown command")
            self.say("commands help")

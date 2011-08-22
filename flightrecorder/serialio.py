#   serialio.py  Flytec and Brauniger serial I/O functions
#   Copyright (C) 2011  Tom Payne <twpayne@gmail.com>
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import os
import select
import termios
import time
import tty


from errors import TimeoutError, WriteError


logger = logging.getLogger(__name__)


class SerialIO(object):

    def __init__(self, filename, speed=tty.B57600):
        try:
            self.filename = filename
            logger.info('opening %r' % filename)
            self.fd = os.open(filename, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
            tty.setraw(self.fd)
            attr = tty.tcgetattr(self.fd)
            attr[tty.ISPEED] = attr[tty.OSPEED] = speed
            tty.tcsetattr(self.fd, tty.TCSAFLUSH, attr)
        except termios.error:
            raise IOError

    def set_speed(self, speed):
        attr = tty.tcgetattr(self.fd)
        attr[tty.ISPEED] = attr[tty.OSPEED] = speed
        tty.tcsetattr(self.fd, tty.TCSAFLUSH, attr)

    def read(self, timeout=1, n=1024):
        if select.select([self.fd], [], [], timeout) == ([], [], []):
            raise TimeoutError
        data = os.read(self.fd, n)
        logger.debug('%.3f read %r (%d bytes)' % (time.time(), data, len(data)))
        return data

    def readn(self, n, timeout=1):
        data = ''
        while len(data) < n:
            data += self.read(timeout, n - len(data))
        return data

    def write(self, line):
        logger.debug('%.3f write %r (%d bytes)' % (time.time(), line, len(line)))
        if os.write(self.fd, line) != len(line):
            raise WriteError

    def flush(self):
        tty.tcflush(self.fd, tty.TCIOFLUSH)

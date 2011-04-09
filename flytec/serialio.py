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
import tty


from .errors import TimeoutError


class SerialIO(object):

    def __init__(self, filename):
        logging.info('opening %r' % filename)
        self.fd = os.open(filename, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        tty.setraw(self.fd)
        attr = tty.tcgetattr(self.fd)
        attr[tty.ISPEED] = attr[tty.OSPEED] = tty.B57600
        tty.tcsetattr(self.fd, tty.TCSAFLUSH, attr)

    def read(self):
        if select.select([self.fd], [], [], 1) == ([], [], []):
            raise TimeoutError
        return os.read(self.fd, 1024)

    def write(self, line):
        if os.write(self.fd, line) != len(line):
            raise WriteError

    def flush(self):
        tty.tcflush(self.fd, tty.TCIOFLUSH)

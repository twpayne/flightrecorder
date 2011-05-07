#   flightrecorder.py  Flight recorder generic functions
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


from glob import glob
import re
import os

from .errors import TimeoutError
import fifty20
from .fifty20 import Fifty20
import flymaster
from .flymaster import Flymaster
from .serialio import SerialIO
import sixty15
from .sixty15 import MockSixty15IO, Sixty15


DEVICE_GLOBS = {
        'Darwin': (
            '/dev/cu.PL2303*',
            '/dev/cu.usbserial*',),
        'FreeBSD': (
            '/dev/cuad*',),
        'Linux': (
            '/dev/ttyUSB*',)}

class FlightRecorder(object):

    SUPPORTED_INSTRUMENTS = Fifty20.SUPPORTED_INSTRUMENTS + Flymaster.SUPPORTED_INSTRUMENTS + Sixty15.SUPPORTED_INSTRUMENTS

    def __new__(self, device=None, instrument=None):
        if device:
            devices = (device,)
        else:
            device_globs = DEVICE_GLOBS.get(os.uname()[0], ())
            devices = list(filename for device_glob in device_globs for filename in sorted(glob(device_glob)))
        if instrument is not None and instrument not in FlightRecorder.SUPPORTED_INSTRUMENTS:
            raise RuntimeError # FIXME
        for device in devices:
            if device == 'mock-6015':
                return Sixty15(MockSixty15IO())
            try:
                io = SerialIO(device)
            except IOError:
                continue
            if instrument in Fifty20.SUPPORTED_INSTRUMENTS:
                return Fifty20(io)
            elif instrument in Flymaster.SUPPORTED_INSTRUMENTS:
                return Flymaster(io)
            elif instrument in Sixty15.SUPPORTED_INSTRUMENTS:
                return Sixty15(io)
            elif instrument is None:
                try:
                    io.write('PBRSNP,'.encode('nmea_sentence'))
                    line = io.read(0.2)
                    while line.find('\x11' if line[0] == '\x13' else '\n') == -1:
                        line += io.read()
                    if re.match('\x13\$PBRSNP,[^,]*,[^,]*,[^,]*,[^,]*\*[0-9A-F]{2}\r\n\x11\Z', line):
                        return Fifty20(io, line)
                    if re.match('\$PBRSNP,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*\*[0-9A-F]{2}\r\n\Z', line):
                        return Flymaster(io, line)
                except TimeoutError:
                    io.write('ACT_BD_00\r\n')
                    line = io.read(0.2)
                    while line.find('\n') == -1:
                        line += io.read()
                    if re.match('(Brauniger IQ-Basic|Flytec 6015)\r\n\Z', line):
                        return Sixty15(io, line)
        raise RuntimeError # FIXME

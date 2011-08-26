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
import logging
import re
import os

from errors import TimeoutError
from fifty20 import Fifty20
from flymaster import Flymaster
from serialio import SerialIO
from sixty15 import Sixty15


logger = logging.getLogger(__name__)


DEVICE_GLOBS = {
        'Darwin': (
            '/dev/cu.PL2303*',
            '/dev/cu.usbserial*',),
        'FreeBSD': (
            '/dev/cuad*',),
        'Linux': (
            '/dev/ttyUSB*',)}


class FlightRecorder(object):

    SUPPORTED_MODELS = Fifty20.SUPPORTED_MODELS + Flymaster.SUPPORTED_MODELS + Sixty15.SUPPORTED_MODELS

    def __new__(self, device=None, model=None):
        if device:
            devices = (device,)
        else:
            device_globs = DEVICE_GLOBS.get(os.uname()[0], ())
            devices = list(filename for device_glob in device_globs for filename in sorted(glob(device_glob)))
        if model is not None and model not in FlightRecorder.SUPPORTED_MODELS:
            raise RuntimeError # FIXME
        for device in devices:
            try:
                io = SerialIO(device)
            except IOError:
                continue
            if model in Fifty20.SUPPORTED_MODELS:
                return Fifty20(io)
            elif model in Flymaster.SUPPORTED_MODELS:
                return Flymaster(io)
            elif model in Sixty15.SUPPORTED_MODELS:
                return Sixty15(io)
            elif model is None:
                try:
                    try:
                        line = 'PBRSNP,'.encode('nmea_sentence')
                        logger.info('write %r' % line)
                        io.write(line)
                        line = io.read(0.2)
                        while line.find('\x11' if line[0] == '\x13' else '\n') == -1:
                            line += io.read()
                        logger.info('readline %r' % line)
                        if re.match('\x13\$PBRSNP,[^,]*,[^,]*,[^,]*,[^,]*\*[0-9A-F]{2}\r\n\x11\Z', line):
                            return Fifty20(io, line)
                        if re.match('\$PBRSNP,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*,[^,]*\*[0-9A-F]{2}\r\n\Z', line):
                            return Flymaster(io, line)
                    except TimeoutError:
                        line = 'ACT_BD_00\r\n'
                        logger.info('write %r' % line)
                        io.write(line)
                        line = io.read(0.2)
                        while line.find('\n') == -1:
                            line += io.read()
                        logger.info('readline %r' % line)
                        if re.match('(Brauniger IQ-Basic|Flytec 6015)\r\n\Z', line):
                            logger.info('read %r' % line)
                            return Sixty15(io, line)
                except TimeoutError:
                    pass
        raise TimeoutError

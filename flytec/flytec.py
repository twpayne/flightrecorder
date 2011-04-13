#   flytec.py  Flytec and Brauniger generic functions
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
import os


from .errors import TimeoutError
from .fifty20 import Fifty20
from .serialio import SerialIO
from .sixty15 import MockSixty15IO, Sixty15


DEVICE_GLOBS = {
        'Darwin': (
            '/dev/cu.PL2303*',
            '/dev/cu.usbserial*',),
        'FreeBSD': (
            '/dev/cuad*',),
        'Linux': (
            '/dev/ttyUSB*',)}


def Flytec(device=None):
    if device:
        devices = (device,)
    else:
        device_globs = DEVICE_GLOBS.get(os.uname()[0], ())
        devices = list(filename for device_glob in device_globs for filename in sorted(glob(device_glob)))
    for device in devices:
        if device == 'mock-6015':
            return Sixty15(MockSixty15IO())
        try:
            io = SerialIO(device)
        except IOError:
            continue
        for klass in Sixty15, Fifty20:
            try:
                return klass(io)
            except TimeoutError:
                pass
    return None

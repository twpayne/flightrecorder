#   base.py  Flight recorder base class
#   Copyright (C) 2013  Tom Payne <twpayne@gmail.com>
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
import struct

from base import FlightRecorderBase
from common import simplerepr
from serialio import TimeoutError


logger = logging.getLogger(__name__)


class Format(object):

    def __init__(self, elements):
        self.fmt = ''.join(fmt for fmt, key in elements)
        self.keys = [key for fmt, key in elements]
        self.size = struct.calcsize(self.fmt)

    def unpack(self, target, buf):
        values = struct.unpack_from(self.fmt, buf)
        for key, value in zip(self.keys, values):
            if key is not None:
                setattr(target, key, value)


class Block(object):

    def __init__(self, data, fmt):
        self.data = data
        fmt.unpack(self, data)

    __repr__ = simplerepr


class Ascent(FlightRecorderBase):

    DEV_DRV_STATUS_RES_FORMAT = Format((
        ('>B', 'message_id'),
        ('I', 'device_id'),
        ('B', 'hw_version_major'),
        ('B', 'hw_version_minor'),
        ('B', 'code_version_major'),
        ('B', 'code_version_minor'),
        ('B', 'battery_voltage'),  # FIXME 1 byte but range is 0 to 0xFFFF
        ('H', 'non_empty_sectors'),
        ('B', 'hour'),
        ('B', 'minute'),
        ('B', 'second'),
        ('B', 'day'),
        ('B', 'month'),
        ('B', 'year'),
    ))

    DEV_DRV_LOG_COMMAND_FORMAT = Format((
        ('>B', 'message_id'),
        ('B', 'command_id'),
        ('H', 'flight_number'),
        ))

    DEV_DRV_LIST_TRACKS_FORMAT = Format((
        ('>B', 'message_id'),
        ('H', 'block_number'),
        ('B', 'block_size'),
        ('H', 'number_of_logs'),
        ('H', 'flight_number'),
        ('B', 'hour'),
        ('B', 'minute'),
        ('B', 'day'),
        ('B', 'month'),
        ('B', 'year'),
        ('H', 'duration'),  # FIXME units not specified
        ('H', 'start_altitude'),
        ('H', 'end_altitude'),
        ('H', 'max_altitude'),
        ('H', 'max_distance'),  # FIXME units not specified
        ('h', 'max_lift'),  # FIXME units not specified
        ('h', 'avg_lift'),  # FIXME units not specified
        ('h', 'max_sink'),  # FIXME units not specified
        ('b', 'max_temperature'),  # FIXME units not specified
        ('b', 'min_temperature'),  # FIXME units not specified
        ('H', 'launch_latitude_integer'),
        ('H', 'launch_latitude_fraction'),
        ('H', 'launch_longitude_integer'),
        ('H', 'launch_longitude_fraction'),
        ('B', 'launch_gps_bit'),  # FIXME meaning not specified
        ('H', 'landing_latitude_integer'),
        ('H', 'landing_latitude_fraction'),
        ('H', 'landing_longitude_integer'),
        ('H', 'landing_longitude_fraction'),
        ('B', 'landing_gps_bit'),  # FIXME meaning not specified
        ))

    def __init__(self, io):
        self.io = io
        self.buf = ''

    def angle(self, integer, fraction):
        degrees, minutes = divmod(integer, 100)
        return degrees + (10000 * minutes + fraction) / 600000.0

    def idev_drv_list_tracks(self):
        timeout = 1
        fmt = self.DEV_DRV_LIST_TRACKS_FORMAT
        self.io.write('\x03\x05')
        while True:
            while len(self.buf) < 4:
                self.buf += self.io.read(timeout)
            message_id, block_number, block_size = \
                struct.unpack_from('>BHB', self.buf)
            while len(self.buf) < 4 + block_size:
                self.buf += self.io.read(timeout)
            data = self.buf[:4 + block_size]
            block = Block(self.buf, fmt)
            block.launch_latitude = self.angle(block.launch_latitude_integer,
                    block.launch_latitude_fraction)
            block.launch_longitude = self.angle(block.launch_longitude_integer,
                    block.launch_longitude_fraction)
            block.landing_latitude = self.angle(block.landing_latitude_integer,
                    block.landing_latitude_fraction)
            block.landing_longitude = self.angle(block.landing_longitude_integer,
                    block.landing_longitude_fraction)
            if 4 + block_size != fmt.size:
                logger.warning('block size is %d bytes, but format requires ' +
                               '%d bytes', block_size, fmt.size - 4)
            self.buf = self.buf[4 + block_size:]
            yield block
            if block.block_number == 0:
                break
        if self.buf != '':
            logger.warning('%d extra bytes in buffer: %r',
                    len(self.buf), self.buf)
            self.buf = ''

    def dev_drv_list_tracks(self):
        return list(self.idev_drv_list_tracks())

    def read_track_logs(self, flight_number):
        timeout = 1
        self.io.write(struct.pack('>BBH', 3, 5, flight_number))
        try:
            while True:
                self.buf += self.io.read(timeout)
        except TimeoutError:
            pass
        return self.buf


if __name__ == '__main__':
    from serialio import SerialIO
    logging.basicConfig(level=logging.DEBUG)
    s = SerialIO('/dev/cu.usbmodem411')
    a = Ascent(s)
    for block in a.dev_drv_list_tracks():
        print repr(block)

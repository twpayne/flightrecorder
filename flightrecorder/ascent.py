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

    SUPPORTED_MODELS = ['Ascent']

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
        ('H', 'duration'),  # minutes
        ('H', 'start_altitude'),  # meters
        ('H', 'end_altitude'),  # meters
        ('H', 'max_altitude'),  # meters
        ('H', 'max_distance'),  # decimeters
        ('h', 'max_lift'),  # decimeters/second
        ('h', 'avg_lift'),  # decimeters/second
        ('h', 'max_sink'),  # decimeters/second
        ('B', 'max_temperature'),  # fahrenheit
        ('B', 'min_temperature'),  # fahrenheit
        ('H', 'launch_latitude_integer'),  # ddmm
        ('H', 'launch_latitude_fraction'),  # 0.mmmm
        ('H', 'launch_longitude_integer'),  # ddmm
        ('H', 'launch_longitude_fraction'),  # 0.mmmm
        ('B', 'launch_gps_bit'),  # bit0 = E, bit1 = S
        ('H', 'landing_latitude_integer'),  # ddmm
        ('H', 'landing_latitude_fraction'),  # 0.mmmm
        ('H', 'landing_longitude_integer'),  # ddmm
        ('H', 'landing_longitude_fraction'),  # 0.mmmm
        ('B', 'landing_gps_bit'),  # bit0 = E, bit1 = S
    ))

    def __init__(self, io):
        self.io = io
        self.manufacturer = 'Ascent'
        self.model = 'Ascent'
        self.pilot_name = None

    @property
    def dev_drv_status_res(self):
        if self._dev_drv_status_res is None:
            self._dev_drv_status_res = self.get_dev_drv_status_res()
        return self._dev_drv_status_res

    @property
    def serial_number(self):
        return self.dev_drv_status_res.device_id

    @property
    def software_version(self):
        return '%d.%d' % (self.dev_drv_status_res.code_version_major, self.dev_drv_status_res.code_version_minor)

    def angle(self, ddmm, mmmm):
        degrees, minutes = divmod(ddmm, 100)
        return degrees + (10000 * minutes + mmmm) / 600000.0

    def idev_drv_list_tracks(self):
        fmt = self.DEV_DRV_LIST_TRACKS_FORMAT
        self.io.write('\x03\x05')
        while True:
            block = Block(self.io.readn(85), fmt)
            assert block.message_id == 5
            # FIXME assert block_number
            # FIXME assert block_size
            block.launch_latitude = self.angle(block.launch_latitude_integer,
                                               block.launch_latitude_fraction)
            if block.launch_gps_bit & 1:
                block.launch_latitude = -block.launch_latitude
            block.launch_longitude = self.angle(block.launch_longitude_integer,
                                                block.launch_longitude_fraction)
            if block.launch_gps_bit & 2 == 0:
                block.launch_longitude = -block.launch_longitude
            block.landing_latitude = self.angle(block.landing_latitude_integer,
                                                block.landing_latitude_fraction)
            if block.landing_gps_bit & 1:
                block.landing_latitude = -block.landing_latitude
            block.landing_longitude = self.angle(block.landing_longitude_integer,
                                                 block.landing_longitude_fraction)
            if block.landing_gps_bit & 2 == 0:
                block.landing_longitude = -block.landing_longitude
            yield block
            if block.block_number == 0:
                break

    def get_dev_drv_list_tracks(self):
        return list(self.idev_drv_list_tracks())

    def get_dev_drv_status_res(self):
        fmt = self.DEV_DRV_STATUS_RES_FORMAT
        self.io.write('\x01')
        block = Block(self.io.readn(fmt.size), fmt)
        assert block.message_id == 2
        return block

    def read_track_logs(self, flight_number):
        self.io.write(struct.pack('>BBH', 3, 5, flight_number))
        try:
            while True:
                self.buf += self.io.read()
        except TimeoutError:
            pass
        return self.buf


if __name__ == '__main__':
    from serialio import SerialIO
    logging.basicConfig(level=logging.DEBUG)
    s = SerialIO('/dev/cu.usbmodem641')
    a = Ascent(s)
    if True:
        print repr(a.dev_drv_status_res())
    if True:
        for block in a.dev_drv_list_tracks():
            print repr(block)

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


import datetime
import logging
import struct

from base import FlightRecorderBase
from common import Track, simplerepr
from serialio import TimeoutError
from utc import UTC


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

    DEV_DRV_UPLOAD_SECTOR_HEADER_FORMAT = Format((
        ('>B', 'message_id'),
        ('H', 'block_number'),
        ('B', 'block_size'),
    ))

    LOG_DATA_FLASH_HEADER_FORMAT = Format((
        ('>B', 'header_type'),
        ('H', 'flight_number'),
        ('I', 'internal_memory_storage_value'),
        ('H', 'data_size'),
    ))

    LOG_RECORD_TIME_FORMAT = Format((
        ('>B', 'record_type'),
        ('B', 'hour'),
        ('B', 'minute'),
        ('B', 'second'),
        ('B', 'day'),
        ('B', 'month'),
        ('B', 'year'),
    ))

    LOG_RECORD_LOCATION_FORMAT = Format((
        ('>B', 'record_type'),
        ('H', 'latitude_integer'),
        ('H', 'latitude_fraction'),
        ('H', 'longitude_integer'),
        ('H', 'longitude_fraction'),
        ('H', 'elevation'),
        ('H', 'ground_speed'),
    ))

    def __init__(self, io):
        self.io = io
        self._dev_drv_status_res = None
        self._manufacturer = 'Ascent'
        self._model = 'Ascent'
        self._pilot_name = None
        self._tracks = None

    @property
    def dev_drv_status_res(self):
        if self._dev_drv_status_res is None:
            self._dev_drv_status_res = self.get_dev_drv_status_res()
        return self._dev_drv_status_res

    @property
    def manufacturer(self):
        return self._manufacturer

    @property
    def model(self):
        return self._model

    @property
    def pilot_name(self):
        return self._pilot_name

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
        while True:
            self.io.write('\x03\x05')
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
            logging.debug('%r', block)
            yield block
            if block.block_number == 0:
                break

    def dev_drv_list_tracks(self):
        tracks = []
        for block in list(self.idev_drv_list_tracks()):
            tracks.append(Track(
                datetime=datetime.datetime(block.year + 2000, block.month, block.day, block.hour, block.minute, 0, tzinfo=UTC()),
                duration=datetime.timedelta(minutes=block.duration),
                avg_lift=float(block.avg_lift) / 10,
                end_altitude=block.end_altitude,
                fight_number=block.flight_number,
                landing_latitude=block.landing_latitude,
                landing_longitude=block.landing_longitude,
                launch_latitude=block.launch_latitude,
                launch_longitude=block.launch_longitude,
                max_altitude=block.max_altitude,
                max_distance=block.max_distance,
                max_lift=float(block.max_lift) / 10,
                max_sink=float(block.max_sink) / 10,
                max_temperature=5 * (float(block.max_temperature) - 32) / 9,
                min_temperature=5 * (float(block.min_temperature) - 32) / 9,
                number_of_logs=block.number_of_logs))
        return tracks

    def get_dev_drv_status_res(self):
        fmt = self.DEV_DRV_STATUS_RES_FORMAT
        self.io.write('\x01')
        block = Block(self.io.readn(fmt.size), fmt)
        assert block.message_id == 2
        return block

    def read_track_logs(self, flight_number):
        self.io.write(struct.pack('>BBH', 3, 3, flight_number))
        block = Block(self.io.readn(4), self.DEV_DRV_UPLOAD_SECTOR_HEADER_FORMAT)
        logging.debug('%r', block)
        assert block.message_id == 4
        n = 256 if block.block_size == 0 else block.block_size
        buf = self.io.readn(n)
        log_data_flash_header = Block(buf[:9], self.LOG_DATA_FLASH_HEADER_FORMAT)
        logging.debug('%r', log_data_flash_header)
        data = buf[9:]
        while block.block_number != 0:
            self.io.write(struct.pack('>BBH', 3, 3, flight_number))
            block = Block(self.io.readn(4), self.DEV_DRV_UPLOAD_SECTOR_HEADER_FORMAT)
            logging.debug('%r', block)
            if block.message_id != 4:
                break
            n = 256 if block.block_size == 0 else block.block_size
            data += self.io.readn(n)
        i = 0
        last_time = None
        locations = None
        while i < len(data):
            if '\xf8' <= data[i] and data[i] <= '\xfb':
                assert locations is not None
                j = i + self.LOG_RECORD_LOCATION_FORMAT.size
                location_record = Block(data[i:j], self.LOG_RECORD_LOCATION_FORMAT)
                latitude = self.angle(location_record.latitude_integer,
                                      location_record.latitude_fraction)
                if location_record.record_type & 1:
                    latitude = -latitude
                longitude = self.angle(location_record.longitude_integer,
                                       location_record.longitude_fraction)
                if location_record.record_type & 2 == 0:
                    longitude = -longitude
                locations.append((latitude, longitude, location_record.elevation))
                i = j
            elif data[i] == '\xfe':
                j = i + self.LOG_RECORD_TIME_FORMAT.size
                time_record = Block(data[i:j], self.LOG_RECORD_TIME_FORMAT)
                time = datetime.datetime(time_record.year + 2000, time_record.month, time_record.day, time_record.hour, time_record.minute, time_record.second)
                i = j
                if last_time != None:
                    timedelta = time - last_time
                    logging.debug('timedelta=%r, len(locations)=%d', timedelta, len(locations))
                last_time = time
                locations = []
            else:
                assert False
        return None

    def tracks(self):
        if self._tracks is None:
            self._tracks = self.dev_drv_list_tracks()
        return self._tracks


if __name__ == '__main__':
    from serialio import SerialIO
    logging.basicConfig(level=logging.DEBUG)
    s = SerialIO('/dev/cu.usbmodem621')
    a = Ascent(s)
    if True:
        logging.debug('%r', a.dev_drv_status_res)
    if True:
        s = a.read_track_logs(5)
        print repr(s)

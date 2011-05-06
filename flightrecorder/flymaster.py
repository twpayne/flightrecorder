#   Flymaster low-level device functions
#   Copyright (C) 2010  Tom Payne
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


from datetime import datetime, timedelta
import logging
import re
import struct

from .errors import ProtocolError, ReadError, TimeoutError, WriteError
import nmea
from .utc import UTC
from .waypoint import Waypoint


EPOCH = datetime(2000, 1, 1, 0, 0, 0)
PFMDNL_LST_RE = re.compile(r'PFMLST,(\d+),(\d+),(\d+).(\d+).(\d+),(\d+):(\d+):(\d+),(\d+):(\d+):(\d+)\Z')
PFMSNP_RE = re.compile(r'PFMSNP,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\Z')
PFMWPL_RE = re.compile(r'PFMWPL,(\d{3}\.\d{4}),([NS]),(\d{3}\.\d{4}),([EW]),(\d+),([^,]*),([01])\Z')
PFMWPR_RE = re.compile(r'PFMWPR,ACK,([^,]*)\Z')
TRAILING_NULS_RE = re.compile(r'\x00+')



class Packet(object):

    def __init__(self, id, data):
        self.id = id
        self.data = data


class _Struct:

    def __repr__(self):
        return '<%s %r>' % (self.__class__.__name__, self.__dict__)


class SNP(_Struct):

    def __init__(self, instrument, _1, serial_number, firmware_version, _4, _5):
        self.instrument = instrument
        self.serial_number = int(serial_number)
        self.firmware_version = firmware_version


class Tracklog(_Struct):

    def __init__(self, count, index, dt, duration):
        self.count = count
        self.index = index
        self.dt = dt
        self.duration = duration


class FlightInformationRecord(_Struct):

    def __init__(self, data):
        fields = struct.unpack('<BBBBI8s15s15s15s', data[:61])
        self.firmware_version = '%d.%02d' % (fields[0], fields[1])
        self.hardware_version = '%d.%02d' % (fields[2], fields[3])
        self.serial_number = fields[4]
        self.competition_number = TRAILING_NULS_RE.sub('', fields[5])
        self.pilot_name = TRAILING_NULS_RE.sub('', fields[6])
        self.glider_brand = TRAILING_NULS_RE.sub('', fields[7])
        self.glider_model = TRAILING_NULS_RE.sub('', fields[8])


class KeyTrackPositionRecord(_Struct):

    def __init__(self, data):
        fields = struct.unpack('<BiihhI', data)
        self.fix_flag = fields[0]
        self.lat = fields[1]
        self.lon = fields[2]
        self.alt = fields[3]
        self.pressure = fields[4]
        self.dt = EPOCH + timedelta(seconds=fields[5])


class TrackPositionRecordDelta(_Struct):

    def __init__(self, data):
        fields = struct.unpack('<Bbbbbb', data)
        self.fix_flag = fields[0]
        self.lat_offset = fields[1]
        self.lon_offset = fields[2]
        self.alt_offset = fields[3]
        self.pressure_offset = fields[4]
        self.dt_offset = timedelta(seconds=fields[5])


class TrackPositionRecordDeltas(_Struct):

    def __init__(self, data):
        self.tprds = []
        i = 0
        while i < len(data):
            self.tprds.append(TrackPositionRecordDelta(data[i:i + 6]))
            i += 6


class Flymaster(object):

    SUPPORTED_INSTRUMENTS = 'B1 B1NAV F1'.split()

    def __init__(self, io):
        self.io = io
        self._snp = None
        self.buffer = ''

    def readline(self, timeout):
        result = ''
        while True:
            index = self.buffer.find('\n')
            if index == -1:
                result += self.buffer
                self.buffer = self.io.read(timeout)
            else:
                result += self.buffer[0:index + 1]
                self.buffer = self.buffer[index + 1:]
                logging.info('readline %r' % result)
                return result

    def readpacket(self, timeout):
        while True:
            s = None
            while True:
                if len(self.buffer) >= 2:
                    id = struct.unpack('<H', self.buffer[:2])[0]
                    if id == 0xa3a3:
                        logging.info('readpacket %r' % self.buffer[:2])
                        self.buffer = self.buffer[2:]
                        return Packet(id, None)
                    if len(self.buffer) >= 4:
                        length = ord(self.buffer[2])
                        if len(self.buffer) >= 4 + length:
                            s = self.buffer[:4 + length]
                            self.buffer = self.buffer[4 + length:]
                            break
                self.buffer += self.io.read(1024, timeout)
            logging.info('readpacket %r' % s[:length + 4])
            data = s[3:length + 3]
            checksum = length
            for c in data:
                checksum ^= ord(c)
            if checksum != ord(s[length + 3]):
                self.write('\xb2')
                continue
            self.write('\xb1')
            return Packet(id, data)

    def write(self, line):
        logging.info('write %r' % line)
        self.io.write(line)

    def ieach(self, command, re=None, timeout=1):
        self.write(command.encode('nmea_sentence'))
        while True:
            line = self.readline(timeout)
            if re is None:
                yield line
            else:
                m = re.match(line.decode('nmea_sentence'))
                if m is None:
                    raise ProtocolError(line)
                yield m

    def none(self, command):
        self.write(command.encode('nmea_sentence'))

    def one(self, command, re=None, timeout=1):
        for m in self.ieach(command, re, timeout=timeout):
            return m

    def pfmsnp(self):
        return SNP(*self.one('PFMSNP,', PFMSNP_RE).groups())

    def ipfmdnl_lst(self):
        for m in self.ieach('PFMDNL,LST,', PFMDNL_LST_RE):
            count, index, day, month, year, hour, minute, second = map(int, m.groups()[:8])
            dt = datetime(year + 2000, month, day, hour, minute, second, tzinfo=UTC())
            hours, minutes, seconds = map(int, m.groups()[8:11])
            duration = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            yield Tracklog(count, index, dt, duration)
            if index + 1 == count:
                break

    def pfmdnl_lst(self):
        return list(self.ipfmdnl_lst())

    def ipfmdnl(self, tracklog, timeout=1):
        self.write(('PFMDNL,%s,' % tracklog.dt.strftime('%y%m%d%H%M%S')).encode('nmea_sentence'))
        while True:
            packet = self.readpacket(timeout)
            if packet.id == 0xa0a0:
                yield FlightInformationRecord(packet.data)
            elif packet.id == 0xa1a1:
                yield KeyTrackPositionRecord(packet.data)
            elif packet.id == 0xa2a2:
                yield TrackPositionRecordDeltas(packet.data)
            elif packet.id == 0xa3a3:
                break
            else:
                logging.info('unknown packet type %04X' % packet.id)

    def pfmplt(self, pilot_name, competition_number, glider_brand, glider_model):
        self.none('PFMPLT,%s,%s,%s,%s,' % (pilot_name, competition_number, glider_brand, glider_model))

    def ipfmwpl(self):
        try:
            for m in self.ieach('PFMWPL,', PFMWPL_RE):
                lat = float(m.group(1))
                if m.group(2) == 'S':
                    lat = -lat
                lon = float(m.group(3))
                if m.group(4) == 'W':
                    lon = -lon
                yield Waypoint(
                        lat=lat,
                        lon=lon,
                        alt=int(m.group(5)),
                        name=m.group(6).rstrip(),
                        airfield=bool(int(m.group(7))))
        except TimeoutError:
            pass # FIXME

    def pfmwpl(self):
        return list(self.ipfmwpl())

    def pfmwpr(self, waypoint):
        name = waypoint.name.encode('nmea_characters', 'replace')[:17].ljust(17)
        m = self.one('PFMWPR,%02d%06.3f,%s,%03d%06.3f,%s,,%s,%04d,%d' % (
            abs(60 * waypoint.lat) / 60,
            abs(60 * waypoint.lat) % 60,
            'S' if waypoint.lat < 0 else 'N',
            abs(60 * waypoint.lon) / 60,
            abs(60 * waypoint.lon) % 60,
            'W' if waypoint.lon < 0 else 'E',
            name,
            waypoint.alt,
            1 if getattr(waypoint, 'airfield', False) else 0), PFMWPR_RE)
        if not name.startswith(m.group(1)):
            raise ProtocolError

    @property
    def instrument(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.instrument

    @property
    def firmware_version(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.firmware_version

    @property
    def serial_number(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.serial_number

    def to_json(self):
        return dict(firmware_version=self.firmware_version, instrument=self.instrument, serial_number=self.serial_number)

    def waypoints(self):
        return self.pfmwpl()

    def waypoints_upload(self, waypoints):
        for waypoint in waypoints:
            self.pfmwpr(waypoint)

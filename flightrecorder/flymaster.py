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


import datetime
import logging
import re
import struct

from base import FlightRecorderBase
from common import Track, add_igc_filenames
from errors import NotAvailableError, ProtocolError, TimeoutError
import nmea
from utc import UTC
from waypoint import Waypoint


logger = logging.getLogger(__name__)


EPOCH = datetime.datetime(2000, 1, 1, 0, 0, 0)
PBRSNP_RE = re.compile(r'PBRSNP,([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\Z')
PFMCFG_RE = re.compile(r'FMCFG,([A-Z]+):(.*)\Z')
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

    def __init__(self, model, _1, serial_number, software_version, _4, _5):
        self.model = model
        self.serial_number = int(serial_number)
        self.software_version = software_version


class FlightInformationRecord(_Struct):

    def __init__(self, data):
        fields = struct.unpack('<BBBBI8s15s15s15s', data[:61])
        self.software_version = '%d.%02d' % (fields[0], fields[1])
        self.hardware_version = '%d.%02d' % (fields[2], fields[3])
        self.serial_number = fields[4]
        self.competition_id = TRAILING_NULS_RE.sub('', fields[5])
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
        self.dt = EPOCH + datetime.timedelta(seconds=fields[5])


class TrackPositionRecordDelta(_Struct):

    def __init__(self, data):
        fields = struct.unpack('<Bbbbbb', data)
        self.fix_flag = fields[0]
        self.lat_offset = fields[1]
        self.lon_offset = fields[2]
        self.alt_offset = fields[3]
        self.pressure_offset = fields[4]
        self.dt_offset = datetime.timedelta(seconds=fields[5])


class TrackPositionRecordDeltas(list):

    def __init__(self, data):
        i = 0
        while i < len(data):
            self.append(TrackPositionRecordDelta(data[i:i + 6]))
            i += 6


class Flymaster(FlightRecorderBase):

    SUPPORTED_MODELS = 'B1NAV'.split()

    def __init__(self, io, line=None):
        self.io = io
        self._snp = SNP(*PBRSNP_RE.match(line.decode('nmea_sentence')).groups()) if line else None
        self._pfmdnl_lst = None
        self.buffer = ''
        self.waypoint_precision = 15

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
                logger.info('readline %r' % result)
                return result

    def readpacket(self, timeout):
        while True:
            s = None
            while True:
                if len(self.buffer) >= 2:
                    id = struct.unpack('<H', self.buffer[:2])[0]
                    if id == 0xa3a3:
                        logger.info('readpacket %r' % self.buffer[:2])
                        self.buffer = self.buffer[2:]
                        return Packet(id, None)
                    if len(self.buffer) >= 4:
                        length = ord(self.buffer[2])
                        if len(self.buffer) >= 4 + length:
                            s = self.buffer[:4 + length]
                            self.buffer = self.buffer[4 + length:]
                            break
                self.buffer += self.io.read(timeout)
            logger.info('readpacket %r' % s[:length + 4])
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
        logger.info('write %r' % line)
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

    def pfmids(self, civl_id=None, competition_id=None, pilot_name=None):
        self.none('PFMIDS,%s,%s,%s' % tuple(x[:w].ljust(w) if x else '' for x, w in ((civl_id, 7), (competition_id, 7), (pilot_name, 15))))

    def ipfmcfg(self):
        try:
            for m in self.ieach('PFMCFG,', PFMCFG_RE):
                yield m.groups()
        except TimeoutError:
            pass # FIXME

    def pfmcfg(self):
        return dict(self.ipfmcfg())

    def pfmsnp(self):
        return SNP(*self.one('PFMSNP,', PFMSNP_RE).groups())

    def igc_helper(self, packets):
        yield 'AFLYMASTER %s %s\r\n' % (self.model, self.serial_number)
        date, lat, lon, alt, pressure, dt = None, None, None, None, None, None
        for packet in packets:
            if isinstance(packet, FlightInformationRecord):
                yield 'HFPLTPILOT:%s\r\n' % packet.pilot_name
                yield 'HPGTYGLIDERTYPE:%s %s\r\n' % (packet.glider_brand, packet.glider_model)
                yield 'HPCIDCOMPETITIONID:%s\r\n' % packet.competition_id
                yield 'HFRFWFIRMWAREVERSION:%s\r\n' % packet.software_version
                yield 'HFRHWHARDWAREVERSION:%s\r\n' % packet.hardware_version
                yield 'HFFTYFRTYPE:FLYMASTER,%s\r\n' % self.model
            elif isinstance(packet, KeyTrackPositionRecord):
                if packet.dt.date() != date:
                    yield 'HFDTE%s\r\n' % packet.dt.strftime('%d%m%y')
                    date = packet.dt.date()
                lat, lon, alt, pressure, dt = packet.lat, packet.lon, packet.alt, packet.pressure, packet.dt
                yield 'B%s%02d%02d%03d%c%03d%02d%03d%c%c%05d%05d\r\n' % (
                        dt.strftime('%H%M%S'),
                        abs(lat) / 60000, (abs(lat) % 60000) / 1000, abs(lat) % 1000, 'S' if lat < 0 else 'N',
                        abs(lon) / 60000, (abs(lon) % 60000) / 1000, abs(lon) % 1000, 'E' if lon < 0 else 'W',
                        'A' if packet.fix_flag & 0x80 else 'V',
                        Flymaster.pressure_altitude(pressure),
                        alt)
            elif isinstance(packet, TrackPositionRecordDeltas):
                if lat is None:
                    logger.debug('Track position record delta received before key track position record' % packet)
                    continue
                for tprd in packet:
                    lat += tprd.lat_offset
                    lon += tprd.lon_offset
                    alt += tprd.alt_offset
                    pressure += tprd.pressure_offset
                    dt += tprd.dt_offset
                    if dt.date() != date:
                        yield 'HFDTE%s\r\n' % dt.strftime('%d%m%y')
                        date = dt.date()
                    yield 'B%s%02d%02d%03d%c%03d%02d%03d%c%c%05d%05d\r\n' % (
                            dt.strftime('%H%M%S'),
                            abs(lat) / 60000, (abs(lat) % 60000) / 1000, abs(lat) % 1000, 'S' if lat < 0 else 'N',
                            abs(lon) / 60000, (abs(lon) % 60000) / 1000, abs(lon) % 1000, 'E' if lon < 0 else 'W',
                            'A' if tprd.fix_flag & 0x80 else 'V',
                            Flymaster.pressure_altitude(pressure),
                            alt)

    def pfmdnl_lst(self):
        tracks = []
        def igc_lambda(self, dt):
            return lambda: self.igc_helper(self.ipfmdnl(dt))
        for m in self.ieach('PFMDNL,LST,', PFMDNL_LST_RE):
            count, index, day, month, year, hour, minute, second = map(int, m.groups()[:8])
            hours, minutes, seconds = map(int, m.groups()[8:11])
            dt = datetime.datetime(year + 2000, month, day, hour, minute, second, tzinfo=UTC())
            tracks.append(Track(
                index=index,
                datetime=dt,
                duration=datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds),
                _igc_lambda=igc_lambda(self, dt)))
            if index + 1 == count:
                break
        return add_igc_filenames(tracks, 'XFR', self.serial_number)

    def ipfmdnl(self, dt, timeout=1):
        self.write(('PFMDNL,%s,' % dt.strftime('%y%m%d%H%M%S')).encode('nmea_sentence'))
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
                logger.info('unknown packet type %04X' % packet.id)

    def ipfmwpl(self):
        try:
            for m in self.ieach('PFMWPL,', PFMWPL_RE):
                lat = float(m.group(1))
                if m.group(2) == 'S':
                    lat = -lat
                lon = float(m.group(3))
                if m.group(4) == 'W':
                    lon = -lon
                alt = int(m.group(5))
                name = m.group(6)
                airfield = bool(int(m.group(7)))
                yield Waypoint(name, lat, lon, alt, airfield=airfield)
        except TimeoutError:
            pass # FIXME

    def pfmwpl(self):
        return list(self.ipfmwpl())

    def pfmwpr(self, waypoint):
        name = re.sub(r'[^ 0-9A-Z]+', lambda m: ' ' * len(m.group(0)), waypoint.get_id_name().upper())[:16].ljust(16)
        m = self.one('PFMWPR,%02d%06.3f,%s,%03d%06.3f,%s,,%s,%04d,%d' % (
            abs(60 * waypoint.lat) / 60,
            abs(60 * waypoint.lat) % 60,
            'S' if waypoint.lat < 0 else 'N',
            abs(60 * waypoint.lon) / 60,
            abs(60 * waypoint.lon) % 60,
            'W' if waypoint.lon < 0 else 'E',
            name,
            waypoint.alt or 0,
            waypoint.airfield), PFMWPR_RE)
        if name != m.group(1):
            raise ProtocolError
        return name

    @property
    def manufacturer(self):
        return 'Flymaster'

    @property
    def model(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.model

    @property
    def software_version(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.software_version

    @property
    def serial_number(self):
        if self._snp is None:
            self._snp = self.pfmsnp()
        return self._snp.serial_number

    @property
    def pilot_name(self):
        return None

    def set(self, key, value, first=True, last=True):
        if key in ('civl_id', 'competition_id', 'pilot_name'):
            self.pfmids(**{key: value})
        else:
            raise NotAvailableError

    def tracks(self):
        if self._pfmdnl_lst is None:
            self._pfmdnl_lst = self.pfmdnl_lst()
        return self._pfmdnl_lst

    def waypoints(self):
        return self.pfmwpl()

    def waypoint_upload(self, waypoint):
        return self.pfmwpr(waypoint)

    def to_json(self):
        tracks = list(track.to_json() for track in self.tracks())
        waypoints = list(waypoint.to_json() for waypoint in self.waypoints())
        return dict(tracks=tracks, waypoints=waypoints)

    @staticmethod
    def pressure_altitude(pressure):
        return (1.0 - pow(abs((pressure / 10.0) / 1013.25), 0.190284)) * 44307.69

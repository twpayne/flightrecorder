#   sixty15.py  Flytec 6015 and Brauniger IQ Basic functions
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


import datetime
from itertools import chain
import logging
import re
import struct
import time

from base import FlightRecorderBase
from common import Track, add_igc_filenames
from errors import FlashError, NotAvailableError, ProtocolError, ReadError
from utc import UTC
from waypoint import Waypoint


logger = logging.getLogger(__name__)


FA_FORMAT = {}
FA_Owner            = 0x00; FA_FORMAT[FA_Owner]            = '16s'
FA_AC_Type          = 0x01; FA_FORMAT[FA_AC_Type]          = '16s'
FA_AC_ID            = 0x02; FA_FORMAT[FA_AC_ID]            = '16s'
FA_Units            = 0x03; FA_FORMAT[FA_Units]            = 'H'
FA_DiverseFlag      = 0x04; FA_FORMAT[FA_DiverseFlag]      = 'H'
FA_FiltTyp          = 0x05; FA_FORMAT[FA_FiltTyp]          = 'B'
FA_Alt1Diff         = 0x06; FA_FORMAT[FA_Alt1Diff]         = 'l'
FA_VarioDigFk       = 0x07; FA_FORMAT[FA_VarioDigFk]       = 'B'
FA_BFreqRise        = 0x08; FA_FORMAT[FA_BFreqRise]        = 'H'
FA_BFreqSink        = 0x09; FA_FORMAT[FA_BFreqSink]        = 'H'
FA_AudioRise        = 0x0a; FA_FORMAT[FA_AudioRise]        = 'h'
FA_AudioSink        = 0x0b; FA_FORMAT[FA_AudioSink]        = 'h'
FA_SinkAlarm        = 0x0c; FA_FORMAT[FA_SinkAlarm]        = 'h'
FA_FreqGain         = 0x0d; FA_FORMAT[FA_FreqGain]         = 'B'
FA_PitchGain        = 0x0e; FA_FORMAT[FA_PitchGain]        = 'B'
FA_MaxRiseRejection = 0x0f; FA_FORMAT[FA_MaxRiseRejection] = 'H'
FA_VarioMinMaxFk    = 0x10; FA_FORMAT[FA_VarioMinMaxFk]    = 'B'
FA_RecIntervall     = 0x11; FA_FORMAT[FA_RecIntervall]     = 'B'
FA_AudioVolume      = 0x12; FA_FORMAT[FA_AudioVolume]      = 'B'
FA_UTC_Offset       = 0x13; FA_FORMAT[FA_UTC_Offset]       = 'b'
FA_PressOffset      = 0x14; FA_FORMAT[FA_PressOffset]      = 'l'
FA_ThermThreshold   = 0x15; FA_FORMAT[FA_ThermThreshold]   = 'h'
FA_PowerOffTime     = 0x16; FA_FORMAT[FA_PowerOffTime]     = 'B'
FA_StallSpeed       = 0x1a; FA_FORMAT[FA_StallSpeed]       = 'H'
FA_WindWheelGain    = 0x1c; FA_FORMAT[FA_WindWheelGain]    = 'B'
FA_PreThermalThr    = 0x22; FA_FORMAT[FA_PreThermalThr]    = 'h'

FA_MAP = {
        'pilot_name': FA_Owner,
        'glider_type': FA_AC_Type,
        'glider_id': FA_AC_ID,
        'utc_offset': FA_UTC_Offset}

PA_FORMAT = {}
PA_DeviceNr         = 0x00; PA_FORMAT[PA_DeviceNr]         = 'I'
PA_DeviceTyp        = 0x01; PA_FORMAT[PA_DeviceTyp]        = 'B'
PA_SoftVers         = 0x02; PA_FORMAT[PA_SoftVers]         = 'H'
PA_KalibType        = 0x03; PA_FORMAT[PA_KalibType]        = 'B'
PA_Filt1_K          = 0x04; PA_FORMAT[PA_Filt1_K]          = '4B'
PA_Filt2_K          = 0x05; PA_FORMAT[PA_Filt2_K]          = '4B'
PA_Filt4_K          = 0x06; PA_FORMAT[PA_Filt4_K]          = '4B'
PA_AudioHyst        = 0x07; PA_FORMAT[PA_AudioHyst]        = '4B'
PA_AudioRsThrFaktor = 0x08; PA_FORMAT[PA_AudioRsThrFaktor] = '4B'
PA_BattLevel1       = 0x09; PA_FORMAT[PA_BattLevel1]       = '10B'
PA_BattLevel2       = 0x0a; PA_FORMAT[PA_BattLevel2]       = '10B'
PA_BattLevel3       = 0x0b; PA_FORMAT[PA_BattLevel3]       = '10B'
PA_AltiDiff_FLA     = 0x0c; PA_FORMAT[PA_AltiDiff_FLA]     = 'l'
PA_Vario_FLA        = 0x0d; PA_FORMAT[PA_Vario_FLA]        = 'h'
PA_Speed_FLA        = 0x0e; PA_FORMAT[PA_Speed_FLA]        = 'H'
PA_MemoStartDelay   = 0x0f; PA_FORMAT[PA_MemoStartDelay]   = 'B'
PA_Vario_FLE        = 0x10; PA_FORMAT[PA_Vario_FLE]        = 'h'
PA_Speed_FLE        = 0x11; PA_FORMAT[PA_Speed_FLE]        = 'H'


VALID_CHARS = list(chain(
    (0x20, 0x26, 0x28, 0x29),
    xrange(0x2d, 0x3b),
    xrange(0x3c, 0x3f),
    xrange(0x41, 0x5b),
    (0x5f,),
    xrange(0x61, 0x7b)))
INVALID_CHARS_RE = re.compile(r'[^%s]+' % ''.join('\\x%02x' % c for c in VALID_CHARS))


FLASH_RESPONSE_RE = re.compile(r'(S007Flash6015_V1F8|S0056015Wait39|S004Erase_4C|S003Done16|S004Error_32|S005NotReady74)')


class Sixty15(FlightRecorderBase):

    SUPPORTED_MODELS = '6015 IQ-BASIC'.split()

    ATTRIBUTES = {
            'Flytec 6015': {'manufacturer': 'Flytec', 'model': '6015'},
            'IQ-Basic GPS': {'manufacturer': 'Brauniger', 'model': 'IQ-Basic'}}

    def __init__(self, io, line=None):
        self.io = io
        self.buffer = ''
        self._bd = line.rstrip() if line else None
        self._serial_number = None
        self._manufacturer = None
        self._model = None
        self._software_version = None
        self._pilot_name = None
        self._tracks = None
        self._waypoints = None
        self.waypoint_precision = 1

    def readline(self, timeout=1):
        while True:
            index = self.buffer.find('\r\n')
            if index == -1:
                data = self.io.read(timeout)
                if len(data) == 0:
                    raise ReadError
                self.buffer += data
            else:
                line = self.buffer[:index + 2]
                self.buffer = self.buffer[index + 2:]
                logger.info('readline %r' % line)
                return line

    def write(self, line):
        logger.info('write %r' % line)
        self.io.write(line)

    def act1x(self, x, table):
        self.write('ACT_%02X_00\r\n' % x)
        while True:
            line = self.readline()
            if line == ' Done\r\n':
                break
            index, size = map(int, re.split(r'\s*;\s*', line))
            if index not in table:
                logger.warning('field %d not found in table' % index)
            elif struct.calcsize(table[index]) != size:
                logger.error('field %d expected size %d, got %d' % (index, struct.calcsize(table[index]), size))
            else:
                logger.info('field %d size matches' % index)

    def act10(self):
        self.act1x(0x10, FA_FORMAT)

    def act11(self):
        self.act1x(0x11, PA_FORMAT)

    def act20(self):
        self.write('ACT_20_00\r\n')
        line = self.readline(0.5)
        if re.match('\A\s*No\s+Data\s*\r\n\Z', line):
            return []
        tracks = []
        def igc_lambda(self, index):
            return lambda: self.iact21(index)
        while True:
            if line == ' Done\r\n':
                break
            fields = re.split(r'\s*;\s*', line)
            index = int(fields[0])
            year, month, day = (int(x) for x in fields[1].split('.'))
            hour, minute, second = (int(x) for x in fields[2].split(':'))
            hours, minutes, seconds = (int(x) for x in fields[4].split(':'))
            tracks.append(Track(
                    index=index,
                    datetime=datetime.datetime(year + 2000, month, day, hour, minute, second, tzinfo=UTC()),
                    utc_offset=int(fields[3]),
                    duration=datetime.timedelta(seconds=3600 * hours + 60 * minutes + seconds),
                    altitude_offset=int(fields[5]),
                    altitude_max=int(fields[6]),
                    altitude_min=int(fields[7]),
                    vario_max=float(fields[8]),
                    vario_min=float(fields[9]),
                    speed_max=float(fields[10]),
                    pilot_name=fields[11].strip(),
                    glider_type=fields[12].strip(),
                    glider_id=fields[13].strip(),
                    _igc_lambda=igc_lambda(self, index)))
            line = self.readline(0.5)
        return add_igc_filenames(tracks, self.manufacturer[:3].upper(), self.serial_number)

    def iact21(self, index):
        self.write('ACT_21_%02X\r\n' % index)
        while True:
            line = self.readline()
            yield line
            if line.startswith('G'):
                break

    def act22(self, index):
        self.write('ACT_22_00\r\n')
        line = self.readline()
        if line == 'ACT_22_00 Done\r\n':
            return True
        elif line == 'ACT_22_00 Fail\r\n':
            return False
        else:
            raise ProtocolError('unexpected response %r' % line)

    def act30(self):
        self.write('ACT_30_00\r\n')
        line = self.readline(2)
        if line != ' Done\r\n':
            raise ProtocolError('unexpected response %r' % line)

    def iact31(self):
        self.write('ACT_31_00\r\n')
        line = self.readline()
        if line == 'No Data\r\n':
            return
        while True:
            if line == ' Done\r\n':
                break
            m = re.match(r'\A(.*?);([NS])\s+(\d+)\'(\d+\.\d+);([EW])\s+(\d+)\'(\d+\.\d+);\s*(\d+);\s*(\d+)\r\n', line)
            if m:
                name = m.group(1)
                lat = int(m.group(3)) + float(m.group(4)) / 60.0
                if m.group(2) == 'S':
                    lat = -lat
                lon = int(m.group(6)) + float(m.group(7)) / 60.0
                if m.group(5) == 'W':
                    lon = -lon
                alt = int(m.group(8))
                radius = int(m.group(9))
                yield Waypoint(name, lat, lon, alt, radius=radius)
            else:
                raise ProtocolError('unexpected response %r' % line)
            line = self.readline()

    def act31(self):
        return list(self.iact31())

    def act32(self, waypoint):
        self.write('ACT_32_00\r\n')
        name = INVALID_CHARS_RE.sub('', waypoint.get_id_name())[:16].ljust(16)
        lat_hemi = 'N' if waypoint.lat > 0 else 'S'
        lat_deg, lat_min = divmod(abs(60 * waypoint.lat), 60)
        lon_hemi = 'E' if waypoint.lon > 0 else 'W'
        lon_deg, lon_min = divmod(abs(60 * waypoint.lon), 60)
        self.write('%s;%s  %2d\'%6.3f;%s %3d\'%6.3f;%6d;%6d\r\n' % (
            name,
            lat_hemi, lat_deg, lat_min,
            lon_hemi, lon_deg, lon_min,
            waypoint.alt or 0,
            waypoint.radius or 400))
        line = self.readline()
        if line == ' Done\r\n':
            return name
        elif line == 'full list\r\n':
            raise RuntimeError # FIXME
        elif line == 'Syntax Error\r\n':
            raise ProtocolError('syntax error')
        elif line == 'already exist\r\n':
            return name

    def act82(self):
        self.write('ACT_82_00\r\n')
        line = self.readline(0.1)
        if line != ' Done\r\n':
            raise ProtocolError('unexpected response %r' % line)

    def actbd(self):
        self.write('ACT_BD_00\r\n')
        return self.readline().strip()

    def rxa(self, x, parameter, format):
        self.write('R%cA_%02X\r\n' % (x, parameter))
        line = self.readline(0.2)
        m = re.match(r'\AR%cA_%02X_((?:[0-9A-F]{2})*)\r\n\Z' % (x, parameter), line)
        if m:
            return struct.unpack(format, ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(1))))
        elif line == 'No Par\r\n':
            return None
        else:
            raise ProtocolError('unexpected response %r' % line)

    def rfa(self, parameter):
        return self.rxa('F', parameter, FA_FORMAT[parameter])

    def rpa(self, parameter):
        return self.rxa('P', parameter, PA_FORMAT[parameter])

    def wfa(self, parameter, value):
        format = FA_FORMAT[parameter]
        m = re.match(r'(\d+)s\Z', format)
        if m:
            width = int(m.group(1))
            value = INVALID_CHARS_RE.sub('', value)[:width].ljust(width)
        command = 'WFA_%02X_%s\r\n' % (parameter, ''.join('%02X' % ord(c) for c in struct.pack(format, value)))
        self.write(command)
        line = self.readline(0.1)
        if line == command:
            pass
        elif line == 'No Par\r\n':
            raise ProtocolError('there are no data defined for this parameter number')
        elif line == 'not ready\r\n':
            raise ProtocolError('missing the action $82')
        else:
            raise ProtocolError('Unexpected response %r' % line)

    def read_flash_response(self, expected='S003Done16', timeout=1):
        while True:
            m = FLASH_RESPONSE_RE.match(self.buffer)
            if m:
                response = m.group(1)
                self.buffer = self.buffer[len(m.group(1)):]
                logger.info('read %r' % response)
                if expected and response != expected:
                    raise FlashError('expected %r, got %r' % (expected, response))
                return response
            else:
                data = self.io.read(timeout)
                if len(data) == 0:
                    raise ReadError
                self.buffer += data

    def flash(self, model, srf):
        if model != '6015':
            raise RuntimeError # FIXME
        while True:
            self.write('S007FlyProg_6015AA')
            response = self.read_flash_response(None)
            if response == 'S007Flash6015_V1F8':
                break
            elif response == 'S0056015Wait39':
                time.sleep(1)
            else:
                raise FlashError('unexpected response %r' % response)
        self.write('S004Erase_4C')
        self.read_flash_response('S004Erase_4C')
        self.read_flash_response()
        for i, record in enumerate(srf.records):
            self.write(record)
            self.read_flash_response()
            yield (i + 1, len(srf.records))

    @property
    def manufacturer(self):
        if self._bd is None:
            self._bd = self.actbd()
        return self.ATTRIBUTES[self._bd]['manufacturer']

    @property
    def model(self):
        if self._bd is None:
            self._bd = self.actbd()
        return self.ATTRIBUTES[self._bd]['model']

    @property
    def serial_number(self):
        if self._serial_number is None:
            self._serial_number = self.rpa(PA_DeviceNr)[0]
        return self._serial_number

    @property
    def software_version(self):
        if self._software_version is None:
            value = self.rpa(PA_SoftVers)[0]
            self._software_version = '%d.%d.%02d' % (value / 1000, (value / 100) % 10, value % 100)
        return self._software_version

    @property
    def pilot_name(self):
        if self._pilot_name is None:
            self._pilot_name = self.rfa(FA_Owner)[0].strip()
        return self._pilot_name

    def get(self, key):
        if not key in FA_MAP:
            raise NotAvailableError
        return self.rfa(FA_MAP[key])[0]

    def set(self, key, value, first=True, last=True):
        if not key in FA_MAP:
            raise NotAvailableError
        if first:
            self.act82()
        if key == FA_Owner:
            self._pilot_name = None
        self.wfa(FA_MAP[key], value)

    def tracks(self):
        if self._tracks is None:
            self._tracks = self.act20()
        return self._tracks

    def waypoints(self):
        return self.iact31()

    def waypoint_remove(self, name=None):
        if name:
            raise NotAvailableError
        else:
            self.act30()

    def waypoint_upload(self, waypoint):
        return self.act32(waypoint)

    def to_json(self):
        fa = dict((key, self.rfa(key)) for key in FA_FORMAT.keys())
        pa = dict((key, self.rpa(key)) for key in PA_FORMAT.keys())
        tracks = list(track.to_json(True) for track in self.tracks())
        waypoints = list(waypoint.to_json() for waypoint in self.waypoints())
        return dict(fa=fa, pa=pa, tracks=tracks, waypoints=waypoints)

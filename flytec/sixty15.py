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


from collections import deque
import datetime
import logging
import re
import struct

from .common import Track, add_igc_filenames
from .errors import ProtocolError, ReadError, TimeoutError, WriteError
from .utils import UTC


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

PA_FORMAT = {}
PA_DeviceNr         = 0x00; PA_FORMAT[PA_DeviceNr]         = 'H' # FIXME inconsistent specification
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
PA_BattLevel3       = 0x0b; PA_FORMAT[PA_BattLevel2]       = '10B'
PA_AltiDiff_FLA     = 0x0c; PA_FORMAT[PA_AltiDiff_FLA]     = 'l'
PA_Vario_FLA        = 0x0d; PA_FORMAT[PA_Vario_FLA]        = 'h'
PA_Speed_FLA        = 0x0e; PA_FORMAT[PA_Speed_FLA]        = 'H'
PA_MemoStartDelay   = 0x0f; PA_FORMAT[PA_MemoStartDelay]   = 'B'
PA_Vario_FLE        = 0x10; PA_FORMAT[PA_Vario_FLE]        = 'h'
PA_Speed_FLE        = 0x11; PA_FORMAT[PA_Speed_FLE]        = 'H'


class MockSixty15IO(object):

    def __init__(self):
        self.filename = 'mock'
        self.lines = deque()
        self.fa = [None] * (FA_PreThermalThr + 1)
        self.fa[FA_Owner] = ['%-16s' % 'Chrigel Maurer']
        self.fa[FA_AC_Type] = ['%-16s' % 'Advance Omega']
        self.fa[FA_AC_ID] = ['%-16s' % 1]
        self.pa = [None] * (PA_Speed_FLA + 1)
        self.pa[PA_DeviceNr] = [1234]
        self.pa[PA_DeviceTyp] = [0]
        self.pa[PA_SoftVers] = [5678]
        self.tracks = []
        self.tracks.append((
            (0,  9, 11, 16, 12, 43,  3, 1,  0,  8, 53, -161, 978, 452, 3.49, -2.90, 1.38, 'not-set', 'not set', 'not set'), (
            'AFLY000A 00010\r\n',
            'HFDTE091009\r\n',
            'HFFXA010\r\n',
            'HFPLTPILOT:not set	\r\n',
            'HFGTYGLIDERTYPE: not set	\r\n',
            'HFGIDGLIDERID: not set	\r\n',
            'HFDTM100GPSDATUM:WGS84\r\n',
            'HFRFWFIRMWAREVERSION: 1.1.07 Ger\r\n',
            'HFRHWHARDWAREVERSION:1.00\r\n',
            'HFFTYFRTYPE:Brauniger,IQ-Basic GPS\r\n',
            'HFGPS:FASTRAX,IT321,20\r\n',
            'HFPRSPRESSALTSENSOR:INTERSEMA,MS5401BM,12000\r\n',
            'HFTZNUTCOFFSET: 1\r\n',
            'HFATS1013.3\r\n',
            'I033638FXA3940SIU4143TAS\r\n',
            'F08320109122627\r\n',
            'B0832014700785N00818451EA005730033000904000\r\n',
            'F0832330912142627\r\n',
            'E083233STA\r\n',
            'B0832334700785N00818451EA005330032700005000\r\n',
            'B0832044700785N00818451EA003280032900405000\r\n',
            'B0832094700784N00818451EA003710032700405000\r\n',
            'B0832004700784N00818451EA003330032700505000\r\n',
            'B0838144700842N00818464EA003940044900106000\r\n',
            'B0838194700842N00818464EA003940044900106000\r\n',
            'GED0E339A2CDFC90374F664B36BA80B6DA5503AA490D896D0BE5F817012D9F997\r\n')))
        self.tracks.append((
            (1,  9, 10,  9,  8, 43, 27, 1,  0,  6, 19,    0, 580, 233, 1.90, -2.25, 0.77, 'not-set', 'not-set', 'not-set'), ('G\r\n',)))

    def write(self, line):
        if line == 'ACT_10_00\r\n':
            for key in sorted(FA_FORMAT.keys()):
                self.lines.append('%6d; %6d\r\n' % (key, struct.calcsize(FA_FORMAT[key])))
            self.lines.append('Done\r\n')
            return
        if line == 'ACT_11_00\r\n':
            for key in sorted(PA_FORMAT.keys()):
                self.lines.append('%6d; %6d\r\n' % (key, struct.calcsize(PA_FORMAT[key])))
            self.lines.append('Done\r\n')
            return
        if line == 'ACT_20_00\r\n':
            for track in self.tracks:
                self.lines.append('%6d; %02d.%02d.%02d; %02d:%02d:%02d; %8d; %02d:%02d:%02d; %8d; %8d; %8d; %8.2f; %8.2f; %8.2f;%16s;%16s;%16s\r\n' % track[0])
            self.lines.append('Done\r\n')
            return
        if line == 'ACT_22_00\r\n':
            self.tracks = []
            self.lines.append('ACT_22_00 Done\r\n')
        m = re.match(r'\AACT_21_([0-9A-F]{2})\r\n\Z', line)
        if m:
            self.lines.extend(self.tracks[int(m.group(1), 16)][1])
            return
        m = re.match(r'\ARFA_([0-9A-F]{2})\r\n\Z', line)
        if m:
            index = int(m.group(1), 16)
            if self.fa[index] is None:
                self.lines.append('No Par\r\n')
            else:
                self.lines.append('RFA_%02X_%s\r\n' % (index, ''.join('%02X' % ord(c) for c in struct.pack('<' + FA_FORMAT[index], *self.fa[index]))))
            return
        m = re.match(r'\ARPA_([0-9A-F]{2})\r\n\Z', line)
        if m:
            index = int(m.group(1), 16)
            if self.pa[index] is None:
                self.lines.append('No Par\r\n')
            else:
                self.lines.append('RPA_%02X_%s\r\n' % (index, ''.join('%02X' % ord(c) for c in struct.pack('<' + PA_FORMAT[index], *self.pa[index]))))
            return
        logging.error('invalid or unimplemented command %r' % line)

    def read(self, timeout):
        return self.lines.popleft()

    def flush(self):
        raise NotImplementedError


class Sixty15(object):

    def __init__(self, io):
        self.io = io
        self.buffer = ''
        self.serial_number = self.rpa(PA_DeviceNr)[0]
        self.manufacturer = self.rpa(PA_DeviceTyp)[0]
        self.model = ['6015', 'IQ Basic'][self.manufacturer]
        self.software_version = self.rpa(PA_SoftVers)[0]
        self.pilot_name = self.rfa(FA_Owner)[0].strip()

    def readline(self, timeout=1):
        line = ''
        while True:
            index = self.buffer.find('\r\n')
            if index == -1:
                line += self.buffer
                self.buffer = self.io.read(timeout)
                logging.debug('read %r' % self.buffer)
                if len(self.buffer) == 0:
                    raise ReadError
            else:
                line += self.buffer[:index + 2]
                self.buffer = self.buffer[index + 2:]
                logging.info('readline %r' % line)
                return line

    def write(self, line):
        logging.info('write %r' % line)
        self.io.write(line)

    def act1x(self, x, table):
        self.write('ACT_%02X_00\r\n' % x)
        while True:
            line = self.readline()
            if line == 'Done\r\n':
                break
            index, size = map(int, re.split(r'\s*;\s*', line))
            if index not in table:
                logging.warning('field %d not found in table' % index)
            elif struct.calcsize(table[index]) != size:
                logging.error('field %d expected size %d, got %d' % (index, struct.calcsize(table[index]), size))
            else:
                logging.info('field %d size matches' % index)

    def act10(self):
        self.act1x(0x10, FA_FORMAT)

    def act11(self):
        self.act1x(0x11, PA_FORMAT)

    def act20(self):
        self.write('ACT_20_00\r\n')
        tracks = []
        def igc(self, index):
            return lambda: self.iact21(index)
        while True:
            line = self.readline(0.5)
            if line == 'Done\r\n':
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
                    igc=igc(self, index)))
        return add_igc_filenames(tracks, self.manufacturer, self.serial_number)

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

    def rxa(self, x, parameter, format):
        self.write('R%cA_%02X\r\n' % (x, parameter))
        line = self.readline(0.1)
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

    def to_json(self):
        return {
            'manufacturer': ['Flytec', 'Brauniger'][self.manufacturer],
            'model': self.model,
            'pilot_name': self.pilot_name,
            'serial_number': self.serial_number,
            'software_version': self.software_version}

    def check(self):
        self.act10()
        self.act11()

    tracks = act20

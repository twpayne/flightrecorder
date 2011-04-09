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
import select
import struct
import tty

from .errors import ProtocolError, ReadError, TimeoutError, WriteError
from .utils import UTC


PA_DeviceNr = 0x00
PA_DeviceTyp = 0x01
PA_SoftVers = 0x02
PA_KalibType = 0x03
PA_Filt1_K = 0x04
PA_Filt2_K = 0x05
PA_Filt4_K = 0x06
PA_AudioHyst = 0x07
PA_AudioRsThrFaktor = 0x8
PA_BattLevel1 = 0x09
PA_BattLevel2 = 0x0a
PA_BattLevel2 = 0x0b
PA_AltiDiff_FLA = 0x0c
PA_Vario_FLA = 0x0d
PA_Speed_FLA = 0x0e
PA_MemoStartDelay = 0x0f
PA_Vario_FLE = 0x10
PA_Speed_FLE = 0x11

PA_FORMAT = ['<I', 'B', '<I', 'B', '4B', '4B', '4B', '4B', '4B', '10C', '10C', '10C', '<l', '<i', 'B', '<i', '<I']


class Flight(object):

    def __init__(self, line):
        fields = re.split(r'\s*;\s*', line)
        self.number = int(fields[0])
        year, month, day = (int(x) for x in fields[1].split('.'))
        hour, minute, second = (int(x) for x in fields[2].split(':'))
        self.datetime = datetime.datetime(year + 2000, month, day, hour, minute, second, tzinfo=UTC())
        self.utc_offset = int(fields[3])
        hours, minutes, seconds = (int(x) for x in fields[4].split(':'))
        self.duration = datetime.timedelta(seconds=3600 * hours + 60 * minutes + seconds)
        self.altitude_offset = int(fields[5])
        self.altitude_max = int(fields[6])
        self.altitude_min = int(fields[7])
        self.vario_max = float(fields[8])
        self.vario_min = float(fields[9])
        self.speed_max = float(fields[10])
        self.pilot_name = fields[11].strip()
        self.glider_type = fields[12].strip()
        self.glider_id = fields[13].strip()

    def to_json(self):
        minutes, seconds = divmod(self.duration.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return {
                'date': self.datetime.strftime('%Y-%m-%dT%H:%M:%SZ'),
                'utc_offset': self.utc_offset,
                'duration': '%02d:%02d:%02d' % (hours, minutes, seconds),
                'altitude_offset': self.altitude_offset,
                'altitude_max': self.altitude_max,
                'altitude_min': self.altitude_min,
                'vario_max': self.vario_max,
                'vario_min': self.vario_min,
                'speed_max': self.speed_max,
                'pilot_name': self.pilot_name,
                'glider_type': self.glider_type,
                'glider_id': self.glider_id}


class SerialIO(object):

    def __init__(self, filename):
        logging.info('opening %r' % filename)
        self.fd = os.open(filename, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        tty.setraw(self.fd)
        attr = tty.tcgetattr(self.fd)
        attr[tty.ISPEED] = attr[tty.OSPEED] = tty.B57600
        tty.tcsetattr(self.fd, tty.TCSAFLUSH, attr)

    def readline(self):
        line = ''
        while True:
            index = self.buffer.find('\r\n')
            if index == -1:
                line += self.buffer
                if select.select([self.fd], [], [], 1) == ([], [], []):
                    raise TimeoutError
                self.buffer = os.read(self.fd, 1024)
                logging.debug('read %r' % self.buffer)
                if len(self.buffer) == 0:
                    raise ReadError
            else:
                line += self.buffer[:index + 2]
                self.buffer = self.buffer[index + 2:]
                return line

    def write(self, line):
        if os.write(self.fd, line) != len(line):
            raise WriteError


class MockIO(object):

    def __init__(self):
        self.lines = deque()
        self.fa = [None] * 18
        self.fa[PA_DeviceNr] = [1234]
        self.fa[PA_DeviceTyp] = [0]
        self.flights = []
        self.flights.append((
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
        self.flights.append((
            (1,  9, 10,  9,  8, 43, 27, 1,  0,  6, 19,    0, 580, 233, 1.90, -2.25, 0.77, 'not-set', 'not-set', 'not-set'), ('G')))

    def write(self, line):
        m = re.match(r'\ARPA_([0-9A-F]{2})\r\n\Z', line)
        if m:
            index = int(m.group(1), 16)
            if self.fa[index] is None:
                self.lines.append('No Par\r\n')
            else:
                self.lines.append('RPA_%02X_%s\r\n' % (index, ''.join('%02X' % ord(c) for c in struct.pack(PA_FORMAT[index], *self.fa[index]))))
            return
        if line == 'ACT_20_00\r\n':
            for flight in self.flights:
                self.lines.append('%6d; %02d.%02d.%02d; %02d:%02d:%02d; %8d; %02d:%02d:%02d; %8d; %8d; %8d; %8.2f; %8.2f; %8.2f;%16s;%16s;%16s\r\n' % flight[0])
            self.lines.append('Done\r\n')
            return
        m = re.match(r'\AACT_21_([0-9A-F]{2})\r\n\Z', line)
        if m:
            index = int(m.group(1), 16)
            self.lines.extend(l for l in self.flights[index][1])
            return

    def readline(self):
        return self.lines.popleft()


class Sixty15(object):

    def __init__(self, io):
        self.io = io
        self.buffer = ''
        self.manufacturer = self.rpa(PA_DeviceTyp)[0]
        self.manufacturer_name = ['Flytec', 'Brauniger'][self.manufacturer]
        self.model = ['6015', 'IQ Basic'][self.manufacturer]
        self.serial_number = self.rpa(PA_DeviceNr)[0]

    def readline(self):
        line = self.io.readline()
        logging.info('readline %r' % line)
        return line

    def write(self, line):
        logging.info('write %r' % line)
        self.io.write(line)

    def rpa(self, parameter):
        self.write('RPA_%02X\r\n' % parameter)
        line = self.readline()
        m = re.match(r'\ARPA_%02X_((?:[0-9A-F]{2})*)\r\n\Z' % parameter, line)
        if m:
            return struct.unpack(PA_FORMAT[parameter], ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(1))))
        elif line == 'No Par\r\n':
            return None
        else:
            raise ProtocolError('unexpected response %r' % line)

    def flight_book(self):
        self.write('ACT_20_00\r\n')
        flights = []
        while True:
            line = self.readline()
            if line == 'Done\r\n':
                break
            flights.append(Flight(line))
        date, index = None, 0
        for flight in reversed(flights):
            if flight.datetime.date() == date:
		index += 1
            else:
		index = 1
            flight.igc_filename = '%s-%s-%s-%02d.IGC' % (flight.datetime.strftime('%Y-%m-%d'), ['FLY', 'BRA'][self.manufacturer], self.serial_number, index)
            date = flight.datetime.date()
        return flights

    def get_igc_flight(self, flight):
        lines = []
        self.write('ACT_21_%02X\r\n' % flight.number)
        while True:
            line = self.readline()
            lines.append(line)
            if line.startswith('G'):
                break
        return lines

#   fifty20.py  Flytec 5020/5030/6020/6030 and Brauniger Galileo/Competino/Compeo/Competino+/Compeo+ functions
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
import logging
import re

from .common import Track, add_igc_filenames, MANUFACTURER_NAME
from .errors import ProtocolError, ReadError, TimeoutError, WriteError
import nmea
from .utc import UTC


MANUFACTURER = {}
for model in '5020 5030 6020 6030'.split(' '):
    MANUFACTURER[model] = 0
for model in 'COMPEO COMPEO+ COMPETINO COMPETINO+ GALILEO'.split(' '):
    MANUFACTURER[model] = 1

XON = '\021'
XOFF = '\023'

PBRMEMR_RE = re.compile(r'\APBRMEMR,([0-9A-F]+),([0-9A-F]+(?:,[0-9A-F]+)*)\Z')
PBRRTS_RE1 = re.compile(r'\APBRRTS,(\d+),(\d+),0+,(.*)\Z')
PBRRTS_RE2 = re.compile(r'\APBRRTS,(\d+),(\d+),(\d+),([^,]*),(.*?)\Z')
PBRSNP_RE = re.compile(r'\APBRSNP,([^,]*),([^,]*),([^,]*),([^,]*)\Z')
PBRTL_RE = re.compile(r'\APBRTL,(\d+),(\d+),(\d+).(\d+).(\d+),(\d+):(\d+):(\d+),(\d+):(\d+):(\d+)\Z')
PBRWPS_RE = re.compile(r'\APBRWPS,(\d{2})(\d{2}\.\d{3}),([NS]),(\d{3})(\d{2}\.\d{3}),([EW]),([^,]*),([^,]*),(\d+)\Z')


class Route:

    def __init__(self, index, name, routepoints):
        self.index = index
        self.name = name
        self.routepoints = routepoints


class Routepoint:

    def __init__(self, short_name, long_name):
        self.short_name = short_name
        self.long_name = long_name


class SNP:

    def __init__(self, model, pilot_name, serial_number, software_version):
        self.model = model
        self.pilot_name = pilot_name
        self.serial_number = serial_number
        self.software_version = software_version


class Waypoint:

    def __init__(self, lat, lon, short_name, long_name, alt):
        self.lat = lat
        self.lon = lon
        self.short_name = short_name
        self.long_name = long_name
        self.alt = alt


class Fifty20:

    def __init__(self, io):
        self.io = io
        self.buffer = ''
        snp = self.pbrsnp()
        self.manufacturer = MANUFACTURER[snp.model]
        self.model = snp.model
        self.serial_number = int(snp.serial_number)
        self.software_version = snp.software_version
        self.pilot_name = snp.pilot_name.strip()

    def readline(self, timeout=1):
        if self.buffer == '':
            self.buffer = self.io.read(timeout)
        if self.buffer[0] == XON:
            self.buffer = self.buffer[1:]
            logging.debug('read XON')
            return XON
        elif self.buffer[0] == XOFF:
            self.buffer = self.buffer[1:]
            logging.debug('read XOFF')
            return XOFF
        else:
            line = ''
            while True:
		index = self.buffer.find('\n')
		if index == -1:
                    line += self.buffer
                    self.buffer = self.io.read(timeout)
		else:
                    line += self.buffer[:index + 1]
                    self.buffer = self.buffer[index + 1:]
                    logging.info('readline %r' % line)
                    return line

    def write(self, line):
        logging.info('write %r' % line)
        self.io.write(line)

    def ieach(self, command, re=None, timeout=1):
        try:
            self.write(nmea.encode(command))
            if self.readline(timeout) != XOFF:
                raise ProtocolError
            while True:
		line = self.readline(timeout)
		if line == XON:
                    break
		elif re is None:
                    yield line
		else:
                    m = re.match(nmea.decode(line))
                    if m is None:
                        raise ProtocolError(line)
                    yield m
        except:
            self.io.flush()
            raise

    def none(self, command, timeout):
        for m in self.ieach(command, None, timeout):
            raise ProtocolError(m)

    def one(self, command, re=None, timeout=1):
        result = None
        for m in self.ieach(command, re, timeout):
            if not result is None:
                raise ProtocolError(m)
            result = m
        return result

    def pbrconf(self):
        self.none('PBRCONF,')

    def ipbrigc(self):
        return self.ieach('PBRIGC,')

    def pbrmemr(self, address, length):
        result = []
        first, last = address, address + length
        while first < last:
            m = self.one('PBRMEMR,%04X' % first, PBRMEMR_RE)
            # FIXME check returned address
            data = list(int(i, 16) for i in m.group(2).split(','))
            result.extend(data)
            first += len(data)
        return result[:length]

    def ipbrrts(self):
        for l in self.ieach('PBRRTS,'):
            l = nmea.decode(l)
            m = PBRRTS_RE1.match(l)
            if m:
		index, count, name = int(m.group(1)), int(m.group(2)), m.group(3)
		if count == 1:
                    yield Route(index, name, [])
		else:
                    routepoints = []
            else:
		m = PBRRTS_RE2.match(l)
		if m:
                    index, count, routepoint_index = (int(i) for i in m.groups()[0:3])
                    routepoint_short_name = m.group(4)
                    routepoint_long_name = m.group(5)
                    routepoints.append(Routepoint(routepoint_short_name, routepoint_long_name))
                    if routepoint_index == count - 1:
                        yield Route(index, name, routepoints)
		else:
                    raise ProtocolError(m)

    def pbrrts(self):
        return list(self.ipbrrts())

    def pbrsnp(self):
        return SNP(*self.one('PBRSNP,', PBRSNP_RE, 0.2).groups())

    def pbrtl(self):
        tracks = []
        def igc(self, index):
            return lambda: self.ipbrtr(index)
        for m in self.ieach('PBRTL,', PBRTL_RE, 0.5):
            index = int(m.group(2))
            day, month, year, hour, minute, second = (int(i) for i in m.groups()[2:8])
            hours, minutes, seconds = (int(i) for i in m.groups()[8:11])
            tracks.append(Track(
                count=int(m.group(1)),
                index=index,
                datetime=datetime.datetime(year + 2000, month, day, hour, minute, second, tzinfo=UTC()),
                duration=datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds),
                igc=igc(self, index)))
        return add_igc_filenames(tracks, self.manufacturer, self.serial_number)

    def ipbrtr(self, index):
        return self.ieach('PBRTR,%02d' % index)

    def pbrtr(self, index):
        return list(self.ipbrtr(index))

    def ipbrwps(self):
        for m in self.ieach('PBRWPS,', PBRWPS_RE):
            lat = int(m.group(1)) + float(m.group(2)) / 60
            if m.group(3) == 'S':
                lat *= -1
            lon = int(m.group(4)) + float(m.group(5)) / 60
            if m.group(6) == 'W':
                lon *= -1
            short_name = m.group(7)
            long_name = m.group(8)
            alt = int(m.group(9))
            yield Waypoint(lat, lon, short_name, long_name, alt)

    def pbrwps(self):
        return list(self.ipbrwps())

    def pbrwpx(self, name=None):
        if name:
            self.zero('PBRWPX,%-17s' % name)
        else:
            self.zero('PBRWPX,')

    def to_json(self):
        return {
            'manufacturer': MANUFACTURER_NAME[self.manufacturer],
            'model': self.model,
            'pilot_name': self.pilot_name,
            'serial_number': self.serial_number,
            'software_version': self.software_version}

    tracks = pbrtl

    def check(self):
        # FIXME
        pass

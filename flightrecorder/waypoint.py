#    waypoint.py  Waypoint functions
#    Copyright (C) 2011  Tom Payne
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.


import logging
import re


logger = logging.getLogger(__name__)


class WaypointError(RuntimeError):
    pass


class Waypoint(object):

    def __init__(self, name, lat, lon, alt, airfield=None, color=None, id=None, radius=None):
        id2, alt2, airfield2 = None, None, None
        if id is not None:
            m = re.match('([A-Z]\d{2})(\d{3})?', id)
            if m:
                id2 = m.group(1)
                if m.group(2):
                    alt2 = 10 * int(m.group(2))
                if id.startswith('A'):
                    airfield2 = True
        id3, alt3, name3, airfield3 = None, None, None, None
        if name is not None:
            m = re.match('([A-Z]\d{2})(\d{3})?(?:\s+(.*))?\Z', name)
            if m:
                id3 = m.group(1)
                if id3.startswith('A'):
                    airfield3 = True
                if m.group(2):
                    alt3 = 10 * int(m.group(2))
                name3 = m.group(3) or ''
                if re.search('attero|goal|land', name, re.I):
                    airfield3 = True
        for n in (name3, name):
            if n is not None:
                self.name = n.rstrip()
                break
        else:
            self.name = ''
        for i in (id2, id3, id):
            if i is not None:
                self.id = i
                break
        else:
            self.id = ''
        self.lat = lat
        self.lon = lon
        for a in (alt, alt2, alt3):
            if a is not None:
                self.alt = a
                break
        else:
            self.alt = None
        for a in (airfield, airfield2, airfield3):
            if a is not None:
                self.airfield = a
                break
        else:
            self.airfield = False
        self.color = color
        self.radius = radius
        self.device_name = name

    def get_id(self):
        if re.match('[A-Z]\d{2}\Z', self.id):
            return '%s%s' % (self.id, '%03d' % (self.alt / 10) if self.alt else '')
        else:
            return self.id

    def get_id_name(self):
        if re.match('[A-Z]\d{2}\Z', self.id):
            return '%s%s%s' % (self.id, '%03d' % (self.alt / 10) if self.alt else '', ' %s' % self.name if self.name else '')
        else:
            return '%s%s' % (self.id, ' %s' % self.name if self.name else '')

    def to_json(self):
        return self.__dict__.copy()


def dump(waypoints, file, format='formatgeo'):
    if format == 'compegps':
        file.write(u'G  WGS 84\r\n')
        file.write(u'U  1\r\n')
        for waypoint in waypoints:
            file.write((u'W  %6s A %.10f\u00ba%s %.10f\u00ba%s 27-MAR-62 00:00:00 %f %s\r\n' % (
                    waypoint.get_id(),
                    abs(waypoint.lat),
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lon),
                    'W' if waypoint.lon < 0 else 'E',
                    waypoint.alt or -9999.0,
                    waypoint.name)).encode('iso-8859-1'))
            color = None if waypoint.color is None else int(waypoint.color[1:], 16)
            file.write(u'w Waypoint,0,-1.0,16777215,%s,1,7,%s\r\n' % (
                    '' if color is None else str(((color & 0xff) << 16) + (color & 0xff00) + (color >> 16)),
                    '' if waypoint.radius is None else str(waypoint.radius)))
    elif format == 'formatgeo':
        file.write(u'$FormatGEO\r\n')
        for waypoint in waypoints:
            file.write(u'%-6s    %s %02d %02d %05.2f    %s %03d %02d %05.2f  %4d  %s\r\n' % (
                    waypoint.get_id(),
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lat),
                    (60 * abs(waypoint.lat)) % 60,
                    (3600 * abs(waypoint.lat)) % 60,
                    'W' if waypoint.lon < 0 else 'E',
                    abs(waypoint.lon),
                    (60 * abs(waypoint.lon)) % 60,
                    (3600 * abs(waypoint.lon)) % 60,
                    waypoint.alt or 0,
                    waypoint.name))
    elif format == 'oziexplorer':
        file.write(u'OziExplorer Waypoint File Version 1.0\r\n')
        file.write(u'WGS 84\r\n')
        file.write(u'Reserved 2\r\n')
        file.write(u'Reserved 3\r\n')
        for i, waypoint in enumerate(waypoints):
            color = None if waypoint.color is None else int(waypoint.color[1:], 16)
            file.write(u'%d,%s,%f,%f,,,1,,%s,,%s,,,%s,%s\r\n' % (
                    i + 1,
                    waypoint.get_id(),
                    waypoint.lat,
                    waypoint.lon,
                    '%d' % (((color & 0xff) << 16) + (color & 0xff00) + (color >> 16)) if color is not None else '',
                    waypoint.name,
                    '' if waypoint.radius is None else str(waypoint.radius),
                    '-777' if waypoint.alt is None else str(waypoint.alt / 0.3048)))
    elif format == 'seeyou':
        file.write(u'title,code,country,latitude,longitude,elevation,style,direction,length,frequency,description\r\n')
        for waypoint in waypoints:
            file.write(u'"%s","%s",,%02d%06.3f%s,%03d%06.3f%s,%s,,,,,\r\n' % (
                    waypoint.name,
                    waypoint.get_id(),
                    abs(waypoint.lat),
                    (60 * abs(waypoint.lat)) % 60,
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lon),
                    (60 * abs(waypoint.lon)) % 60,
                    'W' if waypoint.lon < 0 else 'E',
                    '' if waypoint.alt is None else '%fm' % waypoint.alt))


def load(fp, encoding='iso-8859-1'):
    lines = list(line.rstrip() for line in fp.read().decode(encoding).splitlines())
    projs = {}
    waypoints = []
    # FIXME horrible hack to remove byte order mark and new B line from CompeGPS files
    if len(lines) >= 1 and re.search(r'B\s+UTF-8\Z', lines[0]):
        lines = lines[1:]
    if len(lines) >= 2 and re.match(r'\AG\s+WGS\s+84\s*\Z', lines[0]) and re.match(r'\AU\s+1\s*\Z', lines[1]):
        for line in lines[2:]:
            if not line:
                continue
            m = re.match(r'\AW\s+(\S+)\s+A\s+(\d+\.\d+).*([NS])\s+(\d+\.\d+).*([EW])\s+\S+\s+\S+\s+(-?\d+(?:\.\d+))(?:\s+(.*))?\Z', line)
            if m:
                id = m.group(1)
                lat = float(m.group(2))
                if m.group(3) == 'S':
                    lat = -lat
                lon = float(m.group(4))
                if m.group(5) == 'W':
                    lon = -lon
                alt = float(m.group(6))
                name = m.group(7) or ''
                waypoints.append(Waypoint(name, lat, lon, alt if alt > 0 else None, id=id))
                continue
            m = re.match(r'\AW\s+(\S+)\s+(\d+)([CDEFGHJKLMNPQRSTUVWX])\s+(\d+)\s+(\d+)\s+\d{2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(-?\d+(?:\.\d+))(?:\s+(.*))?\Z', line)
            if m:
                from pyproj import Proj
                id = m.group(1)
                zone = m.group(2)
                if zone not in projs:
                    projs[zone] = Proj(proj='utm', zone=zone, ellps='WGS84')
                x, y = int(m.group(4)), int(m.group(5))
                if m.group(3) < 'N':
                    y -= 10000000
                lon, lat = projs[zone](x, y, inverse=True)
                name = m.group(7)
                waypoints.append(Waypoint(name, lat, lon, alt if alt > 0 else None, id=id))
                continue
            m = re.match('\Aw\s+[^,]*,[^,]*,-?\d+(?:\.\d+)?,[^,]*,(\d*),[^,]*,[^,]*,[^,]*(?:,(-?\d+(?:\.\d+)?))?', line)
            if m and len(waypoints) > 0:
                waypoint = waypoints[-1]
                if m.group(1):
                    color = int(m.group(1))
                    waypoint.color = '#%02x%02x%02x' % (color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff)
                if m.group(2):
                    waypoint.radius = float(m.group(2))
                continue
            m = re.match(r'\Az', line)
            if m:
                continue
            logger.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 1 and re.match(r'\A\$FormatGEO\s*\Z', lines[0]):
        for line in lines[1:]:
            if not line:
                continue
            m = re.match(r'\A(\S+)\s+([NS])\s+(\d+)\s+(\d+)\s+(\d+\.\d+)\s+([EW])\s+(\d+)\s+(\d+)\s+(\d+\.\d+)\s+(-?\d+)(?:\s+(.*))?\Z', line)
            if m:
                id = m.group(1)
                lon = int(m.group(7)) + int(m.group(8)) / 60.0 + float(m.group(9)) / 3600.0
                if m.group(2) == 'S':
                    lat = -lat
                lat = int(m.group(3)) + int(m.group(4)) / 60.0 + float(m.group(5)) / 3600.0
                if m.group(6) == 'W':
                    lon = -lon
                alt = int(m.group(10))
                name = m.group(11)
                waypoints.append(Waypoint(name, lat, lon, alt, id=id))
                continue
            logger.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 1 and re.match(r'\A\$FormatUTM\s*\Z', lines[0]):
        for line in lines[1:]:
            if not line:
                continue
            m = re.match(r'\A(\S+)\s+(\d+)([A-Z])\s+(\d+)\s+(\d+)\s+(-?\d+)(?:\s+(.*))?\Z', line)
            if m:
                from pyproj import Proj
                id = m.group(1)
                zone = m.group(2)
                if zone not in projs:
                    projs[zone] = Proj(proj='utm', zone=zone, ellps='WGS84')
                x, y = int(m.group(4)), int(m.group(5))
                if m.group(3) < 'N':
                    y -= 10000000
                lon, lat = projs[zone](x, y, inverse=True)
                alt = int(m.group(6))
                name = m.group(7)
                waypoints.append(Waypoint(name, lat, lon, alt, id=id))
                continue
            logger.warning('unrecognized waypoint %r' % line)
    elif len(lines) > 1 and re.match(r'\Atitle,code,country,latitude,longitude,elevation,style,direction,length,frequency,description', lines[0], re.I):
        columns = re.split(r'\s*,\s*', lines[0].rstrip().lower())
        for line in lines[1:]:
            if not line:
                continue
            try:
                fields = dict((columns[i], value) for (i, value) in enumerate(re.split(r'\s*,\s*', line.rstrip())))
                m = re.match(r'\A(\d\d)(\d\d\.\d\d\d)([NS])\Z', fields['latitude'])
                if not m:
                    raise WaypointError
                lat = int(m.group(1)) + float(m.group(2)) / 60.0
                if m.group(3) == 'S':
                    lat = -lat
                m = re.match(r'\A(\d\d\d)(\d\d\.\d\d\d)([EW])\Z', fields['longitude'])
                if not m:
                    raise WaypointError
                lon = int(m.group(1)) + float(m.group(2)) / 60.0
                if m.group(3) == 'W':
                    lon = -lon
                m = re.match(r'\A(\d+(?:\.\d*)?)(m|ft)\Z', fields['elevation'])
                if not m:
                    raise WaypointError
                alt = float(m.group(1))
                if m.group(2) == 'ft':
                    alt *= 0.3048
                id = fields['code']
                if id[0] == '"' and id[-1] == '"':
                    id = id[1:-1]
                name = fields['title']
                if name[0] == '"' and name[-1] == '"':
                    name = name[1:-1]
                waypoints.append(Waypoint(name, lat, lon, alt, id=id))
            except WaypointError:
                logger.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 4 and re.match(r'\AOziExplorer\s+Waypoint\s+File\s+Version\s+\d+\.\d+\Z', lines[0]) and re.match(r'\AWGS\s+84\s*\Z', lines[1]):
        for line in lines[4:]:
            if not line:
                continue
            fields = re.split(r'\s*,\s*', line)
            id = fields[1]
            lat = float(fields[2])
            lon = float(fields[3])
            if fields[9]:
                color = int(fields[9])
                color = '#%02x%02x%02x' % (color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff)
            else:
                color = None
            name = re.sub(r'\xd1', ',', fields[10])
            if len(fields) > 13 and fields[13] and float(fields[13]) > 0.0:
                radius = float(fields[13])
            else:
                radius = None
            alt = 0.3048 * float(fields[14]) if fields[14] != '-777' else None
            waypoints.append(Waypoint(name, lat, lon, alt, color=color, id=id, radius=radius))
    else:
        logger.error('unrecognised waypoint format %r' % lines[0])
    return waypoints


if __name__ == '__main__':
    import sys
    dump(load(sys.stdin), sys.stdout, format='compegps')

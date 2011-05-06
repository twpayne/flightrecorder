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


class WaypointError(RuntimeError):
    pass


class Waypoint(object):

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_json(self):
        return self.__dict__.copy()


def dump(waypoints, file, format='oziexplorer'):
    if format == 'compegps':
        file.write(u'G  WGS 84\r\n')
        file.write(u'U  1\r\n')
        for waypoint in waypoints:
            file.write(u'W  %6s A %f\u00ba%s %f\u00ba%s 01-JAN-70 00:00:00 %f %s\r\n' % (
                    waypoint.id,
                    abs(waypoint.lat),
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lon),
                    'W' if waypoint.lon < 0 else 'E',
                    waypoint.alt or 0,
                    getattr(waypoint, 'name', '')))
            color = int(waypoint.color[1:], 16)
            file.write(u'w Waypoint,0,-1.0,16777215,%d,1,7,,%f,\r\n' % (
                    ((color & 0xff) << 16) + (color & 0xff00) + (color >> 16),
                    waypoint.radius))
    elif format == 'formatgeo':
        file.write(u'$FormatGEO\r\n')
        for waypoint in waypoints:
            file.write(u'%-6s    %s %02d %02d %05.2f    %s %03d %02d %05.2f  %4d  %s\r\n' % (
                    waypoint.id,
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lat),
                    (60 * abs(waypoint.lat)) % 60,
                    (3600 * abs(waypoint.lat)) % 60,
                    'W' if waypoint.lon < 0 else 'E',
                    abs(waypoint.lon),
                    (60 * abs(waypoint.lon)) % 60,
                    (3600 * abs(waypoint.lon)) % 60,
                    waypoint.alt or 0,
                    getattr(waypoint, 'name', '')))
    elif format == 'oziexplorer':
        file.write(u'OziExplorer Waypoint File Version 1.0\r\n')
        file.write(u'WGS 84\r\n')
        file.write(u'Reserved 2\r\n')
        file.write(u'Reserved 3\r\n')
        for i, waypoint in enumerate(waypoints):
            color = int(waypoint.color[1:], 16) if hasattr(waypoint, 'color') else None
            file.write(u'%d,%s,%f,%f,,,1,,%s,,%s,,,%s,%s\r\n' % (
                    i + 1,
                    getattr(waypoint, 'id', getattr(waypoint, 'name', '')[:6]),
                    waypoint.lat,
                    waypoint.lon,
                    '%d' % (((color & 0xff) << 16) + (color & 0xff00) + (color >> 16)) if color is not None else '',
                    getattr(waypoint, 'name', ''),
                    '%f' % waypoint.radius if hasattr(waypoint, 'radius') else '',
                    '-777' if waypoint.alt is None else '%f' % (waypoint.alt / 0.3048)))
    elif format == 'seeyou':
        file.write(u'title,code,country,latitude,longitude,elevation,style,direction,length,frequency,description\r\n')
        for waypoint in waypoints:
            file.write(u'"%s","%s",,%02d%06.3f%s,%03d%06.3f%s,%s,,,,,"%s"\r\n' % (
                    waypoint.name,
                    waypoint.id,
                    abs(waypoint.lat),
                    (60 * abs(waypoint.lat)) % 60,
                    'S' if waypoint.lat < 0 else 'N',
                    abs(waypoint.lon),
                    (60 * abs(waypoint.lon)) % 60,
                    'W' if waypoint.lon < 0 else 'E',
                    '' if waypoint.alt is None else '%fm' % waypoint.alt,
                    getattr(waypoint, 'description', '')))


def load(fp, encoding='iso-8859-1'):
    lines = list(line.rstrip() for line in fp.read().decode(encoding).splitlines())
    projs = {}
    waypoints = []
    if len(lines) >= 2 and re.match(r'\AG\s+WGS\s+84\s*\Z', lines[0]) and re.match(r'\AU\s+1\s*\Z', lines[1]):
        for line in lines[2:]:
            m = re.match(r'\AW\s+(\S+)\s+A\s+(\d+\.\d+).*([NS])\s+(\d+\.\d+).*([EW])\s+\d{2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(-?\d+(?:\.\d+))(?:\s+(.*))?\Z', line)
            if m:
                lat = float(m.group(2))
                if m.group(3) == 'S':
                    lat = -lat
                lon = float(m.group(4))
                if m.group(5) == 'W':
                    lon = -lon
                waypoint_properties = {}
                for key, index in {'id': 1, 'name': 7}.items():
                    if m.group(index):
                        waypoint_properties[key] = m.group(index)
                waypoint = Waypoint(lat=lat, lon=lon, alt=float(m.group(6)), **waypoint_properties)
                waypoints.append(waypoint)
                continue
            m = re.match(r'\AW\s+(\S+)\s+(\d+)([CDEFGHJKLMNPQRSTUVWX])\s+(\d+)\s+(\d+)\s+\d{2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2}\s+\d{2}:\d{2}:\d{2}\s+(-?\d+(?:\.\d+))(?:\s+(.*))?\Z', line)
            if m:
                from pyproj import Proj
                zone = m.group(2)
                if zone not in projs:
                    projs[zone] = Proj(proj='utm', zone=zone, ellps='WGS84')
                x, y = int(m.group(4)), int(m.group(5))
                if m.group(3) < 'N':
                    y -= 10000000
                lon, lat = projs[zone](x, y, inverse=True)
                waypoint_properties = {}
                for key, index in {'id': 1, 'name': 7}.items():
                    if m.group(index):
                        waypoint_properties[key] = m.group(index)
                waypoint = Waypoint(lat=lat, lon=lon, alt=float(m.group(6)), **waypoint_properties)
                waypoints.append(waypoint)
                continue
            m = re.match('\Aw\s+[^,]*,[^,]*,-?\d+(?:\.\d+)?,[^,]*,(\d+),[^,]*,[^,]*,[^,]*(?:,(-?\d+(?:\.\d+)?))?', line)
            if m and len(waypoints) > 0:
                waypoint = waypoints[-1]
                color = int(m.group(1))
                waypoint.color = '#%02x%02x%02x' % (color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff)
                if m.group(2):
                    waypoint.radius = float(m.group(2))
                continue
            logging.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 1 and re.match(r'\A\$FormatGEO\s*\Z', lines[0]):
        for line in lines[1:]:
            m = re.match(r'\A(\S+)\s+([NS])\s+(\d+)\s+(\d+)\s+(\d+\.\d+)\s+([EW])\s+(\d+)\s+(\d+)\s+(\d+\.\d+)\s+(-?\d+)\s+(.*)\Z', line)
            if m:
                lon = int(m.group(7)) + int(m.group(8)) / 60.0 + float(m.group(9)) / 3600.0
                if m.group(2) == 'S':
                    lat = -lat
                lat = int(m.group(3)) + int(m.group(4)) / 60.0 + float(m.group(5)) / 3600.0
                if m.group(6) == 'W':
                    lon = -lon
                waypoint_properties = {}
                for key, index in {'id': 1, 'name': 11}.items():
                    if m.group(index):
                        waypoint_properties[key] = m.group(index)
                waypoint = Waypoint(lat=lat, lon=lon, alt=int(m.group(10)), **waypoint_properties)
                waypoints.append(waypoint)
                continue
            logging.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 1 and re.match(r'\A\$FormatUTM\s*\Z', lines[0]):
        for line in lines[1:]:
            m = re.match(r'\A(\S+)\s+(\d+)([A-Z])\s+(\d+)\s+(\d+)\s+(-?\d+)\s+(.*)\Z', line)
            if m:
                from pyproj import Proj
                zone = m.group(2)
                if zone not in projs:
                    projs[zone] = Proj(proj='utm', zone=zone, ellps='WGS84')
                x, y = int(m.group(4)), int(m.group(5))
                if m.group(3) < 'N':
                    y -= 10000000
                lon, lat = projs[zone](x, y, inverse=True)
                waypoint_properties = {}
                for key, index in {'id': 1, 'name': 7}.items():
                    if m.group(index):
                        waypoint_properties[key] = m.group(index)
                waypoint = Waypoint(lat=lat, lon=lon, alt=int(m.group(6)), **waypoint_properties)
                waypoints.append(waypoint)
                continue
            logging.warning('unrecognized waypoint %r' % line)
    elif len(lines) > 1 and re.match(r'\Atitle,code,country,latitude,longitude,elevation,style,direction,length,frequency,description', lines[0], re.I):
        columns = re.split(r'\s*,\s*', lines[0].rstrip().lower())
        for line in lines[1:]:
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
                waypoint_properties = {}
                for key, value in {'description': 'description', 'id': 'code', 'name': 'title'}.items():
                    if fields[value]:
                        m = re.match(r'\A"(.*)"\Z', fields[value])
                        waypoint_properties[key] = m.group(1) if m else fields[value]
                waypoint = Waypoint(lat=lat, lon=lon, alt=alt, **waypoint_properties)
                waypoints.append(waypoint)
            except WaypointError:
                logging.warning('unrecognized waypoint %r' % line)
    elif len(lines) >= 4 and re.match(r'\AOziExplorer\s+Waypoint\s+File\s+Version\s+\d+\.\d+\Z', lines[0]) and re.match(r'\AWGS\s+84\s*\Z', lines[1]):
        for line in lines[4:]:
            fields = re.split(r'\s*,\s*', line)
            alt = 0.3048 * float(fields[14]) if fields[14] != '-777' else None
            waypoint_properties = {'id': fields[1], 'name': re.sub(r'\xd1', ',', fields[10])}
            if fields[9]:
                color = int(fields[9])
                waypoint_properties['color'] = '#%02x%02x%02x' % (color & 0xff, (color >> 8) & 0xff, (color >> 16) & 0xff)
            if len(fields) > 13 and fields[13] and float(fields[13]) > 0.0:
                waypoint_properties['radius'] = float(fields[13])
            waypoint = Waypoint(lat=float(fields[2]), lon=float(fields[3]), alt=alt, **waypoint_properties)
            waypoints.append(waypoint)
    else:
        logging.error('unrecognised waypoint format %r' % lines[0])
    return waypoints


if __name__ == '__main__':
    import sys
    dump(load(sys.stdin), sys.stdout)

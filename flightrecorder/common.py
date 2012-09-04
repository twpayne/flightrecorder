#   common.py  Flytec and Brauniger common functions
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


class CTR(object):

    def __init__(self, name, warning_distance, remark, ctrpoints):
        self.name = name
        self.warning_distance = warning_distance
        self.remark = remark
        self.ctrpoints = ctrpoints

    def to_json(self):
        json = {}
        json['name'] = self.name
        json['warning_distance'] = self.warning_distance
        json['remark'] = self.remark
        json['points'] = [ctrpoint.to_json() for ctrpoint in self.ctrpoints]
        return json


class CTRPoint(object):

    def __init__(self, type, lat, lon, radius=None, clockwise=None):
        self.type = type
        self.lat = lat
        self.lon = lon
        self.radius = radius
        self.clockwise = clockwise

    def to_json(self):
        json = {}
        json['type'] = self.type
        json['lat'] = self.lat
        json['lon'] = self.lon
        if self.type == 'C':
            json['radius'] = self.radius
        elif self.type in ('T', 'Z'):
            json['clockwise'] = self.clockwise
        return json



class Track(object):

    def __init__(self, **kwargs):
        self._igc = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    @property
    def igc(self):
        if self._igc is None:
            self._igc = []
            for line in self._igc_lambda():
                yield line
                self._igc.append(line)
        else:
            for line in self._igc:
                yield line

    def to_json(self, igc=False):
        json = {}
        for key, value in self.__dict__.items():
            if key.startswith('_'):
                continue
            elif key == 'datetime':
                value = value.strftime('%Y-%m-%dT%H:%M:%SZ')
            elif key == 'duration':
                minutes, seconds = divmod(value.seconds, 60)
                hours, minutes = divmod(minutes, 60)
                value = '%02d:%02d:%02d' % (hours, minutes, seconds)
            json[key] = value
        if igc:
            json['igc'] = list(self.igc)
        return json


def add_igc_filenames(tracks, manufacturer, serial_number):
    date, index = None, 0
    for track in reversed(tracks):
        if track.datetime.date() == date:
            index += 1
        else:
            index = 1
        track.igc_filename = '%s-%s-%d-%02d.IGC' % (track.datetime.strftime('%Y-%m-%d'), manufacturer, serial_number, index)
        date = track.datetime.date()
    return tracks

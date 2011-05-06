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
        track.igc_filename = '%s-%s-%d-%02d.IGC' % (track.datetime.strftime('%Y-%m-%d'), ['FLY', 'BRA'][manufacturer], serial_number, index)
        date = track.datetime.date()
    return tracks

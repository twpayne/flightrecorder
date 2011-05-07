#   base.py  Flight recorder base class
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


class FlightRecorderBase(object):

    @property
    def manufacturer(self):
        raise NotImplementedError

    @property
    def model(self):
        raise NotImplementedError

    @property
    def serial_number(self):
        raise NotImplementedError

    @property
    def software_version(self):
        raise NotImplementedError

    @property
    def pilot_name(self):
        raise NotImplementedError

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, first=True, last=True):
        raise NotImplementedError

    def tracks(self):
        raise NotImplementedError

    def waypoints(self):
        raise NotImplementedError

    def waypoints_delete(self, name=None):
        raise NotImplementedError

    def waypoints_upload(self, waypoints):
        raise NotImplementedError

    def to_json(self):
        raise NotImplementedError

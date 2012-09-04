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


from errors import NotAvailableError


class FlightRecorderBase(object):

    @property
    def manufacturer(self):
        raise NotAvailableError

    @property
    def model(self):
        raise NotAvailableError

    @property
    def serial_number(self):
        raise NotAvailableError

    @property
    def software_version(self):
        raise NotAvailableError

    @property
    def pilot_name(self):
        raise NotAvailableError

    def ctri(self):
        raise NotAvailableError

    def ctrs(self):
        raise NotAvailableError

    def ctr_upload(self, ctr, warning_distance):
        raise NotAvailableError

    def flash(self, model, srf):
        raise NotAvailableError

    def get(self, key):
        raise NotAvailableError

    def set(self, key, value, first=True, last=True):
        raise NotAvailableError

    def tracks(self):
        raise NotAvailableError

    def waypoints(self):
        raise NotAvailableError

    def waypoint_remove(self, name=None):
        raise NotAvailableError

    def waypoint_upload(self, waypoint):
        raise NotAvailableError

    def to_json(self):
        raise NotAvailableError

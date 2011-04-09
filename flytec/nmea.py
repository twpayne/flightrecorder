#   nmea.py  NMEA codec
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


import re


ENCODE_RE = re.compile('\\A[\x20-\x7f]{1,79}\\Z')
DECODE_RE = re.compile('\\A\\$(.{1,79})\\*([0-9A-F]{2})\r\n\\Z')


class Error(RuntimeError):
    pass


class EncodeError(Error):
    pass


class DecodeError(Error):
    pass


def encode(input):
    if not ENCODE_RE.match(input):
        raise EncodeError(input)
    checksum = 0
    for c in input:
        checksum ^= ord(c)
    return '$%s*%02X\r\n' % (input, checksum)


def decode(input):
    m = DECODE_RE.match(input)
    if not m:
        raise DecodeError(input)
    checksum = 0
    for c in m.group(1):
        checksum ^= ord(c)
    if checksum != ord(m.group(2).decode('hex')):
        raise DecodeError(input)
    return m.group(1)

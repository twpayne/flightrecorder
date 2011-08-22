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


from codecs import Codec, CodecInfo
import codecs
import re


NMEA_ENCODE_RE = re.compile('\\A[\x20-\x7e]{1,79}\\Z')
NMEA_DECODE_RE = re.compile('\\A\\$(.{1,79})\\*([0-9A-F]{2})\r\n\\Z')
NMEA_INVALID_CHAR_RE = re.compile('[^\x20-\x7e]+')


class NMEAError(UnicodeError):
    pass


class NMEASentenceCodec(Codec):

    def decode(self, input, errors='strict'):
        if errors != 'strict':
            raise NotImplementedError
        if not input:
            return ('', 0)
        m = NMEA_DECODE_RE.match(input)
        if not m:
            raise NMEAError(input)
        checksum = 0
        for c in m.group(1):
            checksum ^= ord(c)
        if checksum != ord(m.group(2).decode('hex')):
            raise NMEAError(input)
        return (m.group(1), len(input))

    def encode(self, input, errors='strict'):
        if errors != 'strict':
            raise NotImplementedError
        if not input:
            return ('', 0)
        if not NMEA_ENCODE_RE.match(input):
            raise NMEAError(input)
        checksum = 0
        for c in input:
            checksum ^= ord(c)
        return ('$%s*%02X\r\n' % (input, checksum), len(input))


class NMEACharacterCodec(object):

    def decode(self, input, errors='strict'):
        return (unicode(input), len(input))

    def encode(self, input, errors='strict'):
        if errors == 'replace':
            return (NMEA_INVALID_CHAR_RE.sub(lambda m: '?' * len(m.group()), input), len(input))
        elif errors == 'strict':
            if NMEA_INVALID_CHAR_RE.search(input):
                raise UnicodeError
            return (input, len(input))
        else:
            raise NotImplementedError


def nmea_search(encoding):
    if encoding == 'nmea_sentence':
        codec = NMEASentenceCodec()
        return CodecInfo(codec.encode, codec.decode, name=encoding)
    if encoding == 'nmea_characters':
        codec = NMEACharacterCodec()
        return CodecInfo(codec.encode, None, name=encoding)
    return None


codecs.register(nmea_search)

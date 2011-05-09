#   firmware.py  Flytec and Brauniger firmware functions
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


import logging
import re
import string
from itertools import cycle, izip


VIGENERE_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
VIGENERE_KEY = 'Verna12Mry34st'


class Vigenere(object):

    def __init__(self, alphabet, key):
        self.alphabet = alphabet
        self.indices = dict((v, i) for i, v in enumerate(self.alphabet))
        self.key = key
        self.reset()

    def encode(self, s):
        return ''.join(self.alphabet[(self.indices[c] + self.indices[k]) % len(self.alphabet)] for c, k in izip(s, self.ikey))

    def decode(self, s):
        return ''.join(self.alphabet[(self.indices[c] - self.indices[k]) % len(self.alphabet)] for c, k in izip(s, self.ikey))

    def reset(self):
        self.ikey = cycle(self.key)


S0_RE = re.compile(r'S0([0-9A-F]{2})0000((?:[0-9A-F]{2})+)([0-9A-F]{2})\Z')
S1_RE = re.compile(r'S(1)([0-9A-F]{2})([0-9A-F]{4})((?:[0-9A-F]{2})+)([0-9A-F]{2})\Z')
S2_RE = re.compile(r'S(2)([0-9A-F]{2})([0-9A-F]{6})((?:[0-9A-F]{2})+)([0-9A-F]{2})\Z')
S3_RE = re.compile(r'S(3)([0-9A-F]{2})([0-9A-F]{8})((?:[0-9A-F]{2})+)([0-9A-F]{2})\Z')
S5_RE = re.compile(r'S503([0-9A-F]{4})([0-9A-F]{2})\Z')
S7_RE = re.compile(r'S705([0-9A-F]{8})([0-9A-F]{2})\Z')
S8_RE = re.compile(r'S804([0-9A-F]{6})([0-9A-F]{2})\Z')
S9_RE = re.compile(r'S903([0-9A-F]{4})([0-9A-F]{2})\Z')


class SRecordError(RuntimeError):

    def __init__(self, line):
        self.line = line


class SRecordFile(object):

    def __init__(self, lines):
        self.header = None
        self.data = {}
        self.starting_executing_address = None
        for line in lines:
            line = line.rstrip()
            m = S0_RE.match(line)
            if m:
                length = int(m.group(1), 16)
                data = ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(2)))
                checksum = int(m.group(3), 16) # FIXME check
                if length != len(data) + 3:
                    logging.error('length mismatch %d, %d, %r' % (length, len(data), data))
                    raise SRecordError(line)
                self.header = data
                continue
            m = S1_RE.match(line) or S2_RE.match(line) or S3_RE.match(line)
            if m:
                i = int(m.group(1))
                length = int(m.group(2), 16)
                address = int(m.group(3), 16)
                data = ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(4)))
                checksum = int(m.group(5), 16)
                print repr(dict(i=i, length=length, address=address, data=data, len_data=len(data)))
                if length != 2 + i + len(data):
                    raise SRecordError(line)
                self.data[address] = data
                continue
            m = S5_RE.match(line)
            if m:
                address = int(m.group(1), 16)
                checksum = int(m.group(2), 16)
                if address != len(self.srecords):
                    raise SRecordError(line)
                continue
            m = S7_RE.match(line) or S8_RE.match(line) or S9_RE.match(line)
            if m:
                address = int(m.group(1), 16)
                checksum = int(m.group(2), 16)
                self.starting_executing_address = address
                continue
            logging.error('invalid S-record %r' % line)


def decode(file):
    vigenere = Vigenere(VIGENERE_ALPHABET, VIGENERE_KEY)
    for line in file:
        yield vigenere.decode(line.rstrip())


if __name__ == '__main__':
    import sys
    print SRecordFile(sys.stdin.readlines()).__dict__

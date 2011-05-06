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


import string
from itertools import cycle, izip


VIGENERE_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
VIGENERE_KEY = 'Verna12Mrt34st'


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


def decode(file):
    vigenere = Vigenere(VIGENERE_ALPHABET, VIGENERE_KEY)
    for line in file:
        yield vigenere.decode(line.rstrip())


if __name__ == '__main__':
    import sys
    for line in decode(sys.stdin):
        print line

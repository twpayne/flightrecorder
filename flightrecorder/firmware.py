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
import select
import string
import struct
from itertools import cycle, izip
import zipfile


VIGENERE_ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
VIGENERE_KEY = 'Verna12Mry34st'


class VigenereError(RuntimeError):
    pass


class Vigenere(object):

    def __init__(self, alphabet, key):
        self.alphabet = alphabet
        self.indices = dict((v, i) for i, v in enumerate(self.alphabet))
        self.key = key
        self.reset()

    def encode(self, s):
        try:
            return ''.join(self.alphabet[(self.indices[c] + self.indices[k]) % len(self.alphabet)] for c, k in izip(s, self.ikey))
        except KeyError:
            raise VigenereError

    def decode(self, s):
        try:
            return ''.join(self.alphabet[(self.indices[c] - self.indices[k]) % len(self.alphabet)] for c, k in izip(s, self.ikey))
        except KeyError:
            raise VigenereError

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
        self.records = list(line.rstrip() for line in lines)
        for record in self.records:
            m = S0_RE.match(record)
            if m:
                length = int(m.group(1), 16)
                data = ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(2)))
                checksum = int(m.group(3), 16) # FIXME check
                if length != len(data) + 3:
                    raise SRecordError(record)
                self.header = data
                continue
            m = S1_RE.match(record) or S2_RE.match(record) or S3_RE.match(record)
            if m:
                i = int(m.group(1))
                length = int(m.group(2), 16)
                address = int(m.group(3), 16)
                data = ''.join(chr(int(x, 16)) for x in re.findall(r'..', m.group(4)))
                checksum = int(m.group(5), 16)
                if length != 2 + i + len(data):
                    raise SRecordError(record)
                self.data[address] = data
                continue
            m = S5_RE.match(record)
            if m:
                address = int(m.group(1), 16)
                checksum = int(m.group(2), 16)
                if address != len(self.srecords):
                    raise SRecordError(record)
                continue
            m = S7_RE.match(record) or S8_RE.match(record) or S9_RE.match(record)
            if m:
                address = int(m.group(1), 16)
                checksum = int(m.group(2), 16)
                self.starting_executing_address = address
                continue
            raise SRecordError(record)

    def pages(self):
        data_offset, data, data_length = None, [], 0
        for address in sorted(self.data.keys()):
            if data_offset is None:
                data_offset = address & ~0xff
            fill_length = address - data_offset - data_length
            if fill_length > 0:
                data.append('\xff' * fill_length)
                data_length += fill_length
            elif fill_length != 0:
                raise SRecordError
            data.append(self.data[address])
            data_length += len(self.data[address])
        incomplete = data_length & 0xff
        if incomplete:
            data.append('\xff' * (size - incomplete))
            data_length += incomplete
        data = ''.join(data)
        for i in xrange(0, data_length >> 8):
            yield ((data_offset >> 8) + i, data[256 * i:256 * (i + 1)])


class M32C87Error(RuntimeError):

    def __init__(self, message=None):
        self.message = message


class M32C87(object):

    # Status register (SRD)
    WSM_READY = 0x80
    ERASE_ERROR = 0x20
    PROGRAM_ERROR = 0x10
    BLOCK_ERROR = 0x08

    # Status register 1 (SRD1)
    BOOT_UPDATE_COMPLETE = 0x80
    CHECKSUM_MATCH = 0x10
    DATA_RECEIVE_TIMEOUT = 0x02

    def __init__(self, io):
        self.io = io

    def sleep(self, timeout):
        select.select([], [], [], timeout)

    def initialize(self):
        for i in xrange(0, 16):
            self.io.write('\x00')
            self.sleep(0.02)
        self.sleep(0.05)
        if self.io.readn(1) != '\xb0':
            raise M32C87Error('initialize')

    def set_speed(self, speed):
        c = {tty.B9600: '\xb0', tty.B19200: '\xb1', tty.B38400: '\xb2', tty.B57600: '\xb3', tty.B115200: '\xb4'}[speed]
        self.io.write(c)
        self.io.set_speed(speed)
        self.sleep(0.05)
        if self.io.readn(1) != c:
            raise M32C87Error('set_speed')

    def command(self, value, format='', args=(), output=None):
        self.io.write(struct.pack('>B' + format, value, *args))
        if output:
            return struct.unpack('>' + output, self.io.readn(struct.calcsize(output)))

    def check_id(self):
        pass # FIXME

    def lock(self):
        self.command('\x75')

    def unlock(self):
        self.command('\x7a')

    def erase(self):
        self.command('\xa7', 'B', ('\xd0',))
        if status_register_check(M32C87.ERASE_ERROR):
            raise M32C87Error('erase')

    def status_register_read(self):
        return self.command('\x70', '', (), 'BB')

    def status_register_check(self, bits):
        while True:
            srd = self.status_register_read()
            if srd[0] & M32C87.WSM_READY:
                return bool(srd[0] & bits)
            self.sleep(0.05)

    def status_register_clear(self):
        self.command('\x50')
        self.sleep(0.05)

    def page_write(self, page, data):
        self.command('\x41', 'H256s', (page, data))
        self.sleep(0.05)
        if self.status_register_check(M32C87.PROGRAM_ERROR):
            raise M32C87Error('page_write')

    # FIXME delete member functions below this line

    def page_erase(self, page):
        self.command(0x20, 'HB', (page, 0xd0))

    def page_erase_all_unlocked(self):
        self.command('\xa7', 'B', ('\xd0',))

    def page_read(self, page):
        return self.command('\xff', 'H', (page,), '256s')[0]

    def page_lock_get(self, page):
        return self.command('\x71', 'H', (page,), 'B')[0]

    def page_lock_set(self, page, value):
        self.command('\x77', 'HB', (page, 0xd0))

    def check_data_get(self):
        return self.command('\xfd', '', (), 'H')[0]


def decode(file):
    vigenere = Vigenere(VIGENERE_ALPHABET, VIGENERE_KEY)
    for line in file:
        yield vigenere.decode(line.rstrip())


def firmware_model(filename):
    for pattern, model in (('5020|CTINO', '5020'), ('6015', '6015')):
        if re.search(pattern, filename, re.I):
            return model
    return '6020'


def firmware(file):
    try:
        zf = zipfile.ZipFile(file, 'r')
        for zi in zf.infolist():
            try:
                yield (firmware_model(zi.filename), SRecordFile(decode(zf.open(zi))))
            except (VigenereError, SRecordError):
                continue
    except zipfile.BadZipfile:
        pass
    file.seek(0)
    m = re.search(r'[%s]{18,}\s+([%s]+\s+){128,}' % (VIGENERE_ALPHABET, VIGENERE_ALPHABET), file.read(), re.M)
    if m:
        try:
            yield (firmware_model(file.name), SRecordFile(decode(m.group().splitlines())))
        except (VigenereError, SRecordError):
            pass
    try:
        file.seek(0)
        yield (firmware_model(file.name), SRecordFile(file))
    except SRecordError:
        pass


if __name__ == '__main__':
    import sys
    if False:
        for model, srf in firmware(open(sys.argv[1])):
            print model, srf.header, len(srf.data)
    if True:
        from serialio import SerialIO
        import tty
        model = '5020'
        logging.basicConfig(level=logging.DEBUG)
        io = SerialIO('/dev/ttyUSB0', tty.B9600)
        m32c87 = M32C87(io)
        m32c87.initialize()
        m32c87.set_speed(tty.B19200 if model == '5020' else tty.B57600)
        sys.exit()
        m32c87.unlock()
        m32c87.erase()
        for address, page in srf.pages():
            m32c87.page_write(address, page)
        m32c87.lock()

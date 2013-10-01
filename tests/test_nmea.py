#!/usr/bin/python


import os.path
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import flightrecorder.nmea as nmea
nmea  # suppress pyflakes warning


class NMEATestCase(unittest.TestCase):

    def testEncode(self):
        self.assertEquals('PBRSNP,'.encode('nmea_sentence'), '$PBRSNP,*21\r\n')
        self.assertEquals('PBRTL,'.encode('nmea_sentence'), '$PBRTL,*74\r\n')

    def testEncodeError(self):
        self.assertRaises(UnicodeError, lambda: ('A' * 80).encode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '\0'.encode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '\x1f'.encode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '\x80'.encode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '\xff'.encode('nmea_sentence'))

    def testDecode(self):
        self.assertEquals('$PBRSNP,*21\r\n'.decode('nmea_sentence'), 'PBRSNP,')
        self.assertEquals('$PBRTL,*74\r\n'.decode('nmea_sentence'), 'PBRTL,')

    def testDecodeError(self):
        self.assertRaises(UnicodeError, lambda: 'PBRSNP,*21\r\n'.decode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '$PBRSNP,21\r\n'.decode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '$PBRSNP,*2\r\n'.decode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '$PBRSNP,*21\n'.decode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '$PBRSNP,*21\r'.decode('nmea_sentence'))
        self.assertRaises(UnicodeError, lambda: '$PBRSNP,*20\r\n'.decode('nmea_sentence'))


if __name__ == '__main__':
    unittest.main()

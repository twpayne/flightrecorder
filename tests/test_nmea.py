#!/usr/bin/python


import unittest

import flytec.nmea as nmea


class NMEATestCase(unittest.TestCase):

    def testEncode(self):
        self.assertEquals(nmea.encode('PBRSNP,'), '$PBRSNP,*21\r\n')
        self.assertEquals(nmea.encode('PBRTL,'), '$PBRTL,*74\r\n')

    def testEncodeError(self):
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode(''))
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode('A' * 80))
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode('\0'))
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode('\x1f'))
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode('\x80'))
        self.assertRaises(nmea.EncodeError, lambda: nmea.encode('\xff'))

    def testDecode(self):
        self.assertEquals(nmea.decode('$PBRSNP,*21\r\n'), 'PBRSNP,')
        self.assertEquals(nmea.decode('$PBRTL,*74\r\n'), 'PBRTL,')

    def testDecodeError(self):
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('PBRSNP,*21\r\n'))
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('$PBRSNP,21\r\n'))
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('$PBRSNP,*2\r\n'))
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('$PBRSNP,*21\n'))
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('$PBRSNP,*21\r'))
        self.assertRaises(nmea.DecodeError, lambda: nmea.decode('$PBRSNP,*20\r\n'))


if __name__ == '__main__':
    unittest.main()

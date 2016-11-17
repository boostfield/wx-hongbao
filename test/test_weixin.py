#! /usr/bin/env python3

import base
import os
import unittest
import main
import weixin

FAIL = 'FAIL'
SUCCESS = 'SUCCESS'
OPENID = 'oenW2wz47W1RisML5QijHzwRz34M'

class TC(unittest.TestCase):
    def test_dump_file(self):
        qrcode_file = 'qrcode'
        ticket = weixin.get_unlimit_qrcode_ticket(1)
        file = weixin.dump_qrcode(ticket, qrcode_file)
        self.assertIsNotNone(file)
        self.assertTrue(os.path.exists(file))
        os.remove(file)

    def test_weixin_encrypt(self):
        msg = weixin.Message()
        msg.name = 'abc'

        encode = msg.encrypt()
        print(encode.xml())

        s = msg.decrypt(b'WwUvsf+IhdcB222lnlPnYLgsCDXV+mahmY4/0vcN2IexQls4XXJyafckWg4YjMrvIr+Twq8IzU0GMzJh+MMr+lNqD2VWoMaiMRIOAIzIus40AaVIetQDNjSfC8ehIPFG')
        print(s)
        

if __name__ == '__main__':
    unittest.main()

#! /usr/bin/env python3

import sys
import os
import unittest
import tempfile
import json
cdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cdir, '..'))
import main
import service

FAIL = 'FAIL'
SUCCESS = 'SUCCESS'
OPENID = 'oenW2wz47W1RisML5QijHzwRz34M'

class TestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, main.app.config['DATABASE'] = tempfile.mkstemp()
        main.app.config['TESTING'] = True
        main.init_db()
        main.app.logger.setLevel('DEBUG')
        self.app = main.app.test_client()
        service.db = main.connect_db()

    def tearDown(self):
        os.close(self.db_fd)
        os.unlink(main.app.config['DATABASE'])

    def login(self, openid):
        self.app.post('/test/login?openid={}'.format(openid))

    def logout(self):
        self.app.post('/test/logout')

    def test_pay_not_login(self):
        rsp = self.app.post('/pay')
        self.assertEqual('302 FOUND', rsp.status)

    def test_pay_illegal_money(self):
        self.login(OPENID)
        rsp = self.app.post('/pay', environ_base={'REMOTE_ADDR':'127.0.0.1'})
        rsp = main.get_json_object(rsp)
        self.assertEqual(FAIL, rsp['ret'])

        rsp = self.app.post('/pay', environ_base={'REMOTE_ADDR':'127.0.0.1'}, data='{"money":"10"}')
        rsp = main.get_json_object(rsp)
        self.assertEqual(FAIL, rsp['ret'])

    def test_pay_success(self):
        self.login(OPENID)
        rsp = self.app.post('/pay', data='{"money": 10}', environ_base={'REMOTE_ADDR':'127.0.0.1'})
        rsp = main.get_json_object(rsp)
        self.assertEqual(SUCCESS, rsp['ret'])
        with main.connect_db() as db:
            service.db = db
            pay = service.find_user_pays(OPENID)[0]
            self.assertEqual(10, pay['money'])
            self.assertEqual(OPENID, pay['openid'])
            self.assertEqual('PREPAY', pay['state'])

    def test_create_user(self):
        openid = '123456'
        service.create_user({ 'openid': openid })
        user = service.find_user(openid)
        self.assertEqual(openid, user['openid'])

    def test_update_user_pay(self):
        pay = dict(openid=OPENID, money=10, trade_no='123', ip='0.0.0.0', state='OK')
        service.save_user_pay(pay)
        saved_pay = service.find_user_pays(OPENID)[0]
        self.assertEqual(OPENID, saved_pay['openid'])
        self.assertEqual(pay['money'], saved_pay['money'])
        self.assertEqual(pay['trade_no'], saved_pay['trade_no'])

        saved_pay['money'] = 100
        saved_pay['state'] = FAIL
        service.update_user_pay(saved_pay)
        saved_pay = service.find_user_pays(OPENID)[0]
        self.assertEqual(OPENID, saved_pay['openid'])
        self.assertEqual(100, saved_pay['money'])
        self.assertEqual(pay['trade_no'], saved_pay['trade_no'])
        self.assertEqual(FAIL, saved_pay['state'])
        
        #args = (pay['openid'], pay['money'], pay['trade_no'], pay['ip'], pay['state'], pay.get('prepay_id'), pay.get('error_msg'))


if __name__ == '__main__':
    unittest.main()

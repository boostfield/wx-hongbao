#! /usr/bin/env python3

import os
import base
import unittest
import tempfile
import json
import main
import service
import weixin

FAIL = 'FAIL'
SUCCESS = 'SUCCESS'
OPENID = 'oenW2wz47W1RisML5QijHzwRz34M'

class TestCase(unittest.TestCase):
    def setUp(self):
        main.app.config['TESTING'] = True
        main.app.logger.setLevel('DEBUG')
        self.app = main.app.test_client()
        main.init_db()
        service.db = main.connect_db()

    def tearDown(self):
        service.db.close()
        pass

    def login(self, openid):
        self.app.post('/test/login?openid={}'.format(openid))

    def logout(self):
        self.app.post('/test/logout')

    def getsession(self):
        rsp = self.app.post('/test/session')
        return json.loads(rsp.data.decode('utf-8'))

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
        pay = service.find_user_pays(OPENID)[0]
        self.assertEqual(10, pay['money'])
        self.assertEqual(OPENID, pay['openid'])
        self.assertEqual('PREPAY', pay['state'])

    def test_create_user(self):
        openid = '123456'
        service.create_user(openid)
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
        
    def test_find_user_all_bill(self):
        bill = service.find_user_bill(OPENID)
        self.assertEqual([], bill)

        user_pay = dict(openid=OPENID, money=1, trade_no='no1', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)

        bill = service.find_user_bill(OPENID)
        self.assertEqual([(1, None)], bill)

        user_pay = dict(openid=OPENID, money=2, trade_no='no2', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)
        user_pay = dict(openid=OPENID, money=3, trade_no='no3', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)
        user_pay = dict(openid=OPENID, money=4, trade_no='no4', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)

        sys_pay = dict(openid=OPENID, money=1, billno='bill1', user_pay_id=1, state='OK')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=2, billno='bill2', user_pay_id=2, state='OK')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=3, billno='bill3', user_pay_id=3, state='OK')
        service.save_sys_pay(sys_pay)

        bill = service.find_user_bill(OPENID)
        self.assertEqual([(1, 1), (2, 2), (3, 3), (4, None)], bill)

    # 用户未注册时自主订阅
    def test_user_subscribe(self):
        msg = weixin.Message()
        msg.ToUserName = 'server'
        msg.FromUserName = OPENID
        msg.CreateTime = weixin.now()
        msg.MsgType = 'event'
        msg.Event = 'subscribe'

        self.assertEqual({}, self.getsession())
        rsp = self.app.post('/callback', data=msg.xml())
        self.assertEqual(SUCCESS, rsp.data.decode('utf-8'))

        user = service.find_user(OPENID)
        self.assertEqual(OPENID, user['openid'])
        self.assertEqual({'openid': OPENID}, self.getsession())

        event = service.find_events(OPENID, 'subscribe')[0]
        self.assertEqual(OPENID, event['openid'])
        self.assertEqual('subscribe', event['type'])
        
    # 用户未注册时分销订阅
    def test_user_follow_subscribe(self):
        msg = weixin.Message()
        msg.ToUserName = 'server'
        msg.FromUserName = OPENID
        msg.CreateTime = weixin.now()
        msg.MsgType = 'event'
        msg.Event = 'subscribe'
        msg.EventKey = 'qrscene_2'

        self.assertEqual({}, self.getsession())
        rsp = self.app.post('/callback', data=msg.xml())
        self.assertEqual(SUCCESS, rsp.data.decode('utf-8'))

        user = service.find_user(OPENID)
        self.assertEqual(OPENID, user['openid'])
        self.assertEqual(2, user['agent'])
        self.assertEqual({'openid': OPENID}, self.getsession())

        event = service.find_events(OPENID, 'follow')[0]
        self.assertEqual(OPENID, event['openid'])
        self.assertEqual('follow', event['type'])
        self.assertEqual('2', event['info'])
        
        
    def test_get_share_qrcode(self):
        service.create_user(OPENID)
        self.login(OPENID)
        rsp = self.app.get('/share/qrcode')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(SUCCESS, rsp['ret'])
        self.assertIn('ticket', rsp)


if __name__ == '__main__':
    unittest.main()

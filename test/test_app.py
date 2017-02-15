#! /usr/bin/env python3

import os
import base
import unittest
import json
import main
import weixin
from common import now
from base import anything
from service import Service

FAIL = 'FAIL'
SUCCESS = 'SUCCESS'
OPENID = 'oenW2wz47W1RisML5QijHzwRz34M'

class TC(unittest.TestCase):
    def setUp(self):
        main.app.config['TESTING'] = True
        main.app.logger.setLevel('DEBUG')
        self.app = main.app.test_client()
        main.init_db()
        self.db = main.connect_db()
        self.service = Service(self.db)

    def tearDown(self):
        self.db.close()

    def login(self, openid):
        self.app.post('/api/test/login?openid={}'.format(openid))

    def logout(self):
        self.app.post('/api/test/logout')

    def getsession(self):
        rsp = self.app.post('/api/test/session')
        return json.loads(rsp.data.decode('utf-8'))

    def test_pay_not_login(self):
        rsp = self.app.post('/api/pay')
        self.assertEqual('302 FOUND', rsp.status)

    def test_pay_illegal_money(self):
        self.login(OPENID)
        rsp = self.app.post('/api/pay', environ_base={'REMOTE_ADDR':'127.0.0.1'})
        rsp = main.get_json_object(rsp)
        self.assertEqual(FAIL, rsp['ret'])

        rsp = self.app.post('/api/pay', environ_base={'REMOTE_ADDR':'127.0.0.1'}, data='{"money":"10"}')
        rsp = main.get_json_object(rsp)
        self.assertEqual(FAIL, rsp['ret'])

    def test_pay_success(self):
        self.login(OPENID)
        rsp = self.app.post('/api/pay', data='{"money": 100}', environ_base={'REMOTE_ADDR':'127.0.0.1'})
        rsp = main.get_json_object(rsp)
        self.assertEqual(SUCCESS, rsp['ret'])
        pay = self.service.find_user_pays(OPENID)[0]
        self.assertEqual(100, pay['money'])
        self.assertEqual(OPENID, pay['openid'])
        self.assertEqual('PREPAY', pay['state'])

    def test_create_user(self):
        openid = '123456'
        self.service.create_user(openid)
        user = self.service.find_user(openid)
        self.assertEqual(openid, user['openid'])

    def test_update_user_pay(self):
        pay = dict(openid=OPENID, money=10, trade_no='123', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(pay)
        saved_pay = self.service.find_user_pays(OPENID)[0]
        self.assertEqual(OPENID, saved_pay['openid'])
        self.assertEqual(pay['money'], saved_pay['money'])
        self.assertEqual(pay['trade_no'], saved_pay['trade_no'])

        saved_pay['money'] = 100
        saved_pay['state'] = FAIL
        self.service.update_user_pay(saved_pay)
        saved_pay = self.service.find_user_pays(OPENID)[0]
        self.assertEqual(OPENID, saved_pay['openid'])
        self.assertEqual(100, saved_pay['money'])
        self.assertEqual(pay['trade_no'], saved_pay['trade_no'])
        self.assertEqual(FAIL, saved_pay['state'])
        
    def test_find_user_all_bill(self):
        bill = self.service.find_user_bill(OPENID)
        self.assertEqual((), bill)

        user_pay = dict(openid=OPENID, money=1, trade_no='no1', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)

        bill = self.service.find_user_bill(OPENID)
        self.assertEqual(((1, None),), bill)

        user_pay = dict(openid=OPENID, money=2, trade_no='no2', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid=OPENID, money=3, trade_no='no3', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid=OPENID, money=4, trade_no='no4', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)

        sys_pay = dict(openid=OPENID, money=1, billno='bill1', user_pay_id=1, state='OK', type='RETURN')
        self.service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=2, billno='bill2', user_pay_id=2, state='OK', type='RETURN')
        self.service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=3, billno='bill3', user_pay_id=3, state='OK', type='RETURN')
        self.service.save_sys_pay(sys_pay)

        bill = self.service.find_user_bill(OPENID)
        self.assertEqual(((1, 1), (2, 2), (3, 3), (4, None)), bill)

    # 用户未注册时自主订阅
    def test_user_subscribe(self):
        msg = weixin.Message()
        msg.ToUserName = 'server'
        msg.FromUserName = OPENID
        msg.CreateTime = now()
        msg.MsgType = 'event'
        msg.Event = 'subscribe'

        self.assertEqual({}, self.getsession())
        rsp = self.app.post('/api/callback', data=msg.xml())
        self.assertEqual(SUCCESS, rsp.data.decode('utf-8'))

        user = self.service.find_user(OPENID)
        self.assertEqual(OPENID, user['openid'])
        self.assertEqual({'openid': OPENID}, self.getsession())

        event = self.service.find_events(OPENID, 'subscribe')[0]
        self.assertEqual(OPENID, event['openid'])
        self.assertEqual('subscribe', event['type'])
        
    # 用户未注册时分销订阅
    def test_user_follow_subscribe(self):
        self.service.create_user('user0')
        self.service.create_user('user1')
        msg = weixin.Message()
        msg.ToUserName = 'server'
        msg.FromUserName = OPENID
        msg.CreateTime = now()
        msg.MsgType = 'event'
        msg.Event = 'subscribe'
        msg.EventKey = 'qrscene_1'

        self.assertEqual({}, self.getsession())
        rsp = self.app.post('/api/callback', data=msg.xml())
        self.assertEqual(SUCCESS, rsp.data.decode('utf-8'))

        user = self.service.find_user(OPENID)
        self.assertEqual(OPENID, user['openid'])
        self.assertEqual(1, user['agent'])
        self.assertEqual({'openid': OPENID}, self.getsession())

        event = self.service.find_events(OPENID, 'follow')[0]
        self.assertEqual(OPENID, event['openid'])
        self.assertEqual('follow', event['type'])
        self.assertEqual('1', event['info'])
        
    def test_get_share_qrcode(self):
        self.service.create_user(OPENID)
        self.login(OPENID)
        rsp = self.app.get('/api/share/qrcode')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(SUCCESS, rsp['ret'])
        self.assertIn('qrcode', rsp)
        
        print(rsp)

    def test_find_unshared_profit(self):
        self.service.create_user(OPENID)
        self.service.create_user('user1')
        self.service.create_user('user2', 1)

        user_pay = dict(openid='user0', money=1000, trade_no='no4', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state='OK')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=FAIL)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state='PREPAY')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)

        sys_pay = dict(openid='user2', money=3, billno='bill3', state='OK', type='SHARE')
        self.service.save_sys_pay(sys_pay)
        sys_pay = dict(openid='user2', money=3, billno='bill3', state='OK', type='SHARE')
        self.service.save_sys_pay(sys_pay)

        self.service.save_share(5, 1, 1)
        self.service.save_share(6, 2, 1)

        profit = self.service.find_unshared_profit()
        expect = [
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=7, money=1000),
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=8, money=1000),
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=9, money=1000)
            ]
        self.assertEqual(expect, profit)

    def test_find_follower_num(self):
        self.service.create_user(OPENID)
        self.service.create_user('user1')
        self.service.create_user('user2', 1)
        self.service.create_user('user3', 1)
        self.service.create_user('user4', 1)
        self.assertEqual(3, self.service.find_follower_num(OPENID)) 
        
    def test_find_agent_bill(self):
        self.service.create_user(OPENID)
        self.service.create_user('user1')
        self.service.create_user('user2', 1)

        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=FAIL)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state='PREPAY')
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        self.service.save_user_pay(user_pay)

        sys_pay = dict(openid='user2', money=50, billno='bill3', state='OK', type='SHARE')
        self.service.save_sys_pay(sys_pay)
        sys_pay = dict(openid='user2', money=50, billno='bill3', state='OK', type='SHARE')
        self.service.save_sys_pay(sys_pay)

        self.service.save_share(5, 1, 50)
        self.service.save_share(6, 2, 50)

        expect = [
            dict(openid='user2', user_pay_id=9, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=8, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=7, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=6, money=1000, timestamp=anything(), shared_money=50, shared_timestamp=anything(), sys_pay_id=2),
            dict(openid='user2', user_pay_id=5, money=1000, timestamp=anything(), shared_money=50, shared_timestamp=anything(), sys_pay_id=1)
            ]
        self.assertEqual(expect, self.service.find_agent_bill(OPENID))

        self.login(OPENID)
        rsp = self.app.get('/api/agent/account')
        rsp = json.loads(rsp.data.decode('utf-8'))
        expect = dict(ret=SUCCESS, msg='ok', follower_num=1, page=0, pagesize=50, total_bill_num=5,
                      shared_bill_num=2, total_income=250, shared_income=100,
                      bills=[
                          dict(income=50, shared=False, share_time=None, time=anything()),
                          dict(income=50, shared=False, share_time=None, time=anything()),
                          dict(income=50, shared=False, share_time=anything(), time=anything()),
                          dict(income=50, shared=True, share_time=anything(), time=anything()),
                          dict(income=50, shared=True, share_time=anything(), time=anything())
                          ])
        self.assertEqual(expect, rsp)
        
    def test_find_user_last_income(self):
        self.service.create_user(OPENID)
        self.login(OPENID)

        rsp = self.app.get('/api/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(None, rsp['money'])

        sys_pay = dict(openid=OPENID, money=50, billno='bill3', state=SUCCESS, type='RETURN')
        self.service.save_sys_pay(sys_pay)
        rsp = self.app.get('/api/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(50, rsp['money'])

        sys_pay = dict(openid=OPENID, money=100, billno='bill3', state=SUCCESS, type='SHARE')
        self.service.save_sys_pay(sys_pay)
        rsp = self.app.get('/api/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(50, rsp['money'])

        sys_pay['type'] = ['RETURN']
        self.service.update_sys_pay(sys_pay)
        rsp = self.app.get('/api/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(100, rsp['money'])

        sys_pay = dict(openid=OPENID, money=60, billno='bill3', state=FAIL, type='RETURN')
        self.service.save_sys_pay(sys_pay)
        rsp = self.app.get('/api/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(100, rsp['money'])


    def test_weixin_check_sign(self):
        msg = weixin.Message()
        msg.appid = 'wx9fb7ef78c47f8ef2'
        msg.bank_type = 'CFT'
        msg.cash_fee = 1
        msg.fee_type = 'CNY'
        msg.is_subscribe = 'Y'
        msg.mch_id = '1405637602'
        msg.nonce_str = 'cde59accdf7f445d9a9aed0857731364'
        msg.openid = 'oenW2wz47W1RisML5QijHzwRz34M'
        msg.out_trade_no = '20161112162257357'
        msg.result_code = 'SUCCESS'
        msg.return_code = 'SUCCESS'
        msg.time_end = '20161112162302'
        msg.total_fee = 1
        msg.trade_type = 'JSAPI'
        msg.transaction_id = '4007282001201611129539346065'
        msg.sign = '701DA5F1F043518ACA4B150BD0C38722'
        self.assertTrue(msg.check_sign())

if __name__ == '__main__':
    unittest.main()

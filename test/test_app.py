#! /usr/bin/env python3

import os
import base
import unittest
import tempfile
import json
import main
import service
import weixin
from base import anything

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

        sys_pay = dict(openid=OPENID, money=1, billno='bill1', user_pay_id=1, state='OK', type='RETURN')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=2, billno='bill2', user_pay_id=2, state='OK', type='RETURN')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid=OPENID, money=3, billno='bill3', user_pay_id=3, state='OK', type='RETURN')
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

    def test_find_unshared_profit(self):
        service.create_user(OPENID)
        service.create_user('user1')
        service.create_user('user2', 1)

        user_pay = dict(openid='user0', money=1000, trade_no='no4', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state='OK')
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=FAIL)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state='PREPAY')
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)

        sys_pay = dict(openid='user2', money=3, billno='bill3', state='OK', type='SHARE')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid='user2', money=3, billno='bill3', state='OK', type='SHARE')
        service.save_sys_pay(sys_pay)

        service.save_share(5, 1, 1)
        service.save_share(6, 2, 1)

        profit = service.find_unshared_profit()
        expect = [
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=7, money=1000),
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=8, money=1000),
            dict(agent=1, agent_openid=OPENID, openid='user2', user_pay_id=9, money=1000)
            ]
        self.assertEqual(expect, profit)

    def test_find_follower_num(self):
        service.create_user(OPENID)
        service.create_user('user1')
        service.create_user('user2', 1)
        service.create_user('user3', 1)
        service.create_user('user4', 1)
        self.assertEqual(3, service.find_follower_num(OPENID)) 
        
    def test_find_agent_bill(self):
        service.create_user(OPENID)
        service.create_user('user1')
        service.create_user('user2', 1)

        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user1', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=FAIL)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state='PREPAY')
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)
        user_pay = dict(openid='user2', money=1000, trade_no='no4', ip='0.0.0.0', state=SUCCESS)
        service.save_user_pay(user_pay)

        sys_pay = dict(openid='user2', money=50, billno='bill3', state='OK', type='SHARE')
        service.save_sys_pay(sys_pay)
        sys_pay = dict(openid='user2', money=50, billno='bill3', state='OK', type='SHARE')
        service.save_sys_pay(sys_pay)

        service.save_share(5, 1, 50)
        service.save_share(6, 2, 50)

        expect = [
            dict(openid='user2', user_pay_id=9, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=8, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=7, money=1000, timestamp=anything(), shared_money=None, shared_timestamp=anything(), sys_pay_id=None),
            dict(openid='user2', user_pay_id=6, money=1000, timestamp=anything(), shared_money=50, shared_timestamp=anything(), sys_pay_id=2),
            dict(openid='user2', user_pay_id=5, money=1000, timestamp=anything(), shared_money=50, shared_timestamp=anything(), sys_pay_id=1)
            ]
        self.assertEqual(expect, service.find_agent_bill(OPENID))

        self.login(OPENID)
        rsp = self.app.get('/agent/account')
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
        service.create_user(OPENID)
        self.login(OPENID)

        rsp = self.app.get('/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(None, rsp['money'])

        sys_pay = dict(openid=OPENID, money=50, billno='bill3', state=SUCCESS, type='RETURN')
        service.save_sys_pay(sys_pay)
        rsp = self.app.get('/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(50, rsp['money'])

        sys_pay = dict(openid=OPENID, money=100, billno='bill3', state=SUCCESS, type='SHARE')
        service.save_sys_pay(sys_pay)
        rsp = self.app.get('/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(50, rsp['money'])

        sys_pay = dict(openid=OPENID, money=60, billno='bill3', state=FAIL, type='RETURN')
        service.save_sys_pay(sys_pay)
        rsp = self.app.get('/income/last')
        rsp = json.loads(rsp.data.decode('utf-8'))
        self.assertEqual(50, rsp['money'])

if __name__ == '__main__':
    unittest.main()

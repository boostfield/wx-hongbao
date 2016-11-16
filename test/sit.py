#! /usr/bin/env python3

import base
import json
import unittest
import weixin
import main
import strategy
import threading
from threading import Thread
from unittest.mock import MagicMock
from common import randstr

SUCCESS = 'SUCCESS'
strategy.STRATEGY_FILES_HOME = '../strategies'

class TC(unittest.TestCase):
    def setUp(self):
        main.app.config['TESTING'] = True
        main.app.logger.setLevel('DEBUG')
        main.init_db()
        weixin.make_order = MagicMock(side_effect=self.weixin_make_order_mock)
        self.client_vars = {}
        self.thread2client = {}

    def tearDown(self):
        pass

    def register(self, client, openid):
        weixin.get_web_auth_access_token = MagicMock(return_value=dict(openid=openid))
        client.get('/api/auth/redirect')
        
    def weixin_make_order_mock(self, order):
        result = weixin.Message()
        result.return_code = SUCCESS
        result.result_code = SUCCESS
        result.prepay_id = randstr()
        client = self.thread2client[threading.current_thread()]
        self.client_vars[client] = order.out_trade_no
        return result
        
    def _pay(self, client, money):
        data = dict(money=money)
        data = json.dumps(data)
        rsp = client.post('/api/pay', environ_base={'REMOTE_ADDR':'127.0.0.1'}, data=data)
        return rsp, self.client_vars[client]

    def pay(self, client, money):
        rsp, trade_no = self._pay(client, money)
        return json.loads(rsp.data.decode('utf-8')), trade_no
        
    def _notify_pay(self, client, **kws):
        result = dict(return_code=SUCCESS, result_code=SUCCESS, send_listid=randstr())
        weixin.send_redpack = MagicMock(return_value=weixin.Message(result))

        notify = weixin.Message(kws)
        notify.sign()
        return client.post('/api/pay/notify', data=notify.xml())

    def notify_pay(self, client, **kws):
        rsp = self._notify_pay(client, **kws)
        return weixin.Message(rsp.data)
    
    def follow_register(self, client, openid, agent_id):
        data = weixin.Message(dict(FromUserName=openid, MsgType='event', Event='subscribe', EventKey='qrscene_%d' % agent_id))
        client.post('/api/callback', data=data.xml())
        
    def do_pay(self, client, openid, times):
        self.thread2client[threading.current_thread()] = client
        for i in range(times):
            rsp, trade_no = self.pay(client, 100)
            rsp = self.notify_pay(client, return_code=SUCCESS, result_code=SUCCESS, openid=openid, out_trade_no=trade_no)
        
    def start_pay(self, *args):
        th = Thread(target=self.do_pay, args=args)
        th.start()
        return th
    
    def test(self):
        clients = []
        for i in range(50):
            client = main.app.test_client()
            openid = 'user%d' % i
            self.register(client, openid)
            clients.append((client, openid))

        for i in range(50):
            client = main.app.test_client()
            openid = 'follower%d' % i
            self.follow_register(client, openid, i + 1)
            clients.append((client, openid))

        threads = []
        for client, openid in clients:
            th = self.start_pay(client, openid, 100)
            threads.append(th)

        for th in threads:
            th.join()

if __name__ == '__main__':
    unittest.main()

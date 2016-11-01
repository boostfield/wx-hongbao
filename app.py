#! /usr/bin/python
# -*- encoding: utf-8 -*-

from __future__ import print_function
import time
from datetime import datetime
import logging
import json
import flask
import uuid
from flask import Flask
from flask import request
from flask import url_for
from flask import redirect
app = Flask(__name__)

import weixin
from weixin import MessageReceived
from weixin import OrderMessage

handler = logging.FileHandler('/tmp/flask.log')
app.logger.addHandler(handler)
app.config.from_pyfile('conf/config.py')

def print_req(req, printer):
    printer(req.method)
    printer(req.url)
    printer(req.headers)
    printer(req.environ)
    printer(req.form)
    printer(req.data)

def randstr():
    return uuid.uuid4().hex

@app.route('/')
def print_request():
    print_req(request, print)
    return 'ok'

@app.route('/test')
def test():
    weixin.a = 'okjk'
    return weixin.a

@app.route('/callback')
def auth():
    return request.args.get('echostr')

@app.route('/callback', methods=['POST'])
def callback():
    print_req(request, app.logger.warning)
    recv_msg = MessageReceived(request.data)
    reply_msg = weixin.RepliedMessage()

    reply_msg.ToUserName = recv_msg.FromUserName
    reply_msg.FromUserName = recv_msg.ToUserName
    reply_msg.CreateTime = int(time.time()) 
    reply_msg.MsgType = 'text'
    reply_msg.Content = weixin.oauth2_url(app.config['RESTFUL_ROOT'] + '/auth/redirect')

    return reply_msg.xml()

# 用户在网页端授权后回调至此位置
@app.route('/auth/redirect')
def auth_redirect():
    print_req(request, app.logger.warning)
    access_token = weixin.get_web_auth_access_token(request.args.get('code'))
    app.logger.warning(access_token)
    return redirect(app.config['WEB_ROOT'])

@app.route('/access_token')
def get_access_token():
    return weixin.get_access_token()

@app.route('/menu/create', methods=['POST'])
def create_menu():
    weixin.create_menu()
    return 'ok'

@app.route('/jsapi/sign')
def get_jsapi_sign():
    url = request.args.get('url')   # 当前需要执行jsapi的url
    if url is None:
        return 'fuck you'

    return json.dumps(weixin.get_jsapi_sign(url))

def _build_mch_billno():
    now = datetime.now()
    timestr = now.strftime('%Y%m%d%H%M%S%f')[0:-3]
    app.config['MCH_ID'] + timestr


# DOC: https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_7
@app.route('/pay/notify', methods=['POST'])
def process_pay_result():
    pay_result = MessageReceived(request.data)
    if pay_result.return_code == 'SUCCESS':
        redpack = weixin.RedPack()
        redpack.nonce_str = randstr()
        redpack.mch_billno = _build_mch_billno()
        redpack.mch_id = app.config['MCH_ID']
        redpack.wxappid = app.config['APP_ID']
        redpack.send_name = app.config['MCH_NAME']
        redpack.re_openid = pay_result.openid
        redpack.total_amount = 1000
        redpack.total_num = 1
        redpack.wishing = 'hello bitch'
        redpack.client_ip = app.config['LOCAL_IP']
        redpack.act_name = app.config['REDPACK_ACTIVE_NAME']
        redpack.remark = app.config['REDPACK_REMARK']
        redpack.sign()

        # weixin.send_redpack(redpack)
        xml = redpack.xml()
        print(xml)
        return redpack.xml()

    return 'ok'


@app.route('/pay', methods=['POST'])
def receive_tax():
    openid = 'oenW2wz47W1RisML5QijHzwRz34M'        # todo: openid from session

    order = OrderMessage()
    order.mch_id = app.config['MCH_ID']
    order.body = 'game-tax'
    order.out_trade_no = ''
    order.total_fee = 1000
    order.spbill_create_ip = request.environ['REMOTE_ADDR']
    order.notify_url = app.config['RESTFUL_ROOT'] + '/pay/notify'
    order.trade_type = 'JSAPI'
    order.openid = openid
    
    app.logger.warning(order.xml())

    result = weixin.make_order(order)
    app.logger.warning(result)
    result = json.loads(result)
    return json.dumps(weisin.get_pay_sign(result['prepay_id']))

    return 


if __name__ == '__main__':
    app.config.from_pyfile('conf/test.config.py')
    app.run('0.0.0.0', debug=True)

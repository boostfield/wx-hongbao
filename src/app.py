#! /usr/bin/python
# -*- encoding: utf-8 -*-

from __future__ import print_function
import time
import logging
import json
import flask
from flask import Flask
from flask import request
app = Flask(__name__)

import weixin
from weixin import MessageReceived
from weixin import MessageReplied
from weixin import OrderMessage

handler = logging.FileHandler('/tmp/flask.log')
app.logger.addHandler(handler)

def print_req(req, printer):
    printer(req.method)
    printer(req.url)
    printer(req.headers)
    printer(req.environ)
    printer(req.form)
    printer(req.data)

@app.route('/')
def print_request():
    print_req(request, print)
    return 'ok'

@app.route('/callback')
def auth():
    return request.args.get('echostr')

@app.route('/callback', methods=['POST'])
def callback():
    print_req(request, app.logger.warning)
    recv_msg = MessageReceived(request.data)
    reply_msg = MessageReplied()

    reply_msg.ToUserName = recv_msg.FromUserName
    reply_msg.FromUserName = recv_msg.ToUserName
    reply_msg.CreateTime = int(time.time()) 
    reply_msg.MsgType = 'text'
    reply_msg.Content = weixin.oauth2_url('http://test.boostfield.com/api/auth/redirect')

    return reply_msg.xml()

# 用户在网页端授权后回调至此位置
@app.route('/auth/redirect')
def auth_redirect():
    print_req(request, app.logger.warning)
    access_token = weixin.get_web_auth_access_token(request.args.get('code'))
    app.logger.warning(access_token)
    return flask.redirect('http://test.boostfield.com')

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

@app.route('/pay', methods=['POST'])
def receive_tax():
    openid = 'oenW2wz47W1RisML5QijHzwRz34M'        # todo: openid from session

    order = OrderMessage()
    order.mch_id = None
    order.body = 'game-tax'
    order.out_trade_no = ''
    order.total_fee = 1000
    order.spbill_create_ip = request.environ['REMOTE_ADDR']
    order.notify_url = 'http://test.boostfield.com/api/pay/notify/'
    order.trade_type = 'JSAPI'
    order.openid = openid
    
    app.logger.warning(order.xml())

    result = weixin.make_order(order)
    app.logger.warning(result)

    return result


if __name__ == '__main__':
    app.run('0.0.0.0', debug=True)

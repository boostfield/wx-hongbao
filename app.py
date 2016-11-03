#! /usr/bin/python
# -*- encoding: utf-8 -*-
from __future__ import print_function
import os
import time
import sqlite3
from datetime import datetime
from logging import Formatter, FileHandler
import json
import uuid
from flask import Flask, request, redirect, session, g
import service
import weixin
from weixin import MessageReceived
from weixin import OrderMessage

app = Flask(__name__)
app.config.from_pyfile('conf/config.py')
app.config['CWD'] = os.path.dirname(__file__)

handler = FileHandler(app.config['LOG_FILE'])
handler.setFormatter(Formatter(app.config['LOG_FORMAT']))
app.logger.addHandler(handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
weixin.logger = app.logger

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with connect_db() as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

def print_req(req, printer):
    printer(req.method)
    printer(req.url)
    printer(req.headers)
    printer(req.environ)
    printer(req.form)
    printer(req.data)

def randstr():
    return uuid.uuid4().hex

def _timestamp_str():
    now = datetime.now()
    return now.strftime('%Y%m%d%H%M%S%f')[0:-3]

def _build_mch_billno():
    return app.config['MCH_ID'] + _timestamp_str()

@app.before_request
def before_request():
    g.db = connect_db()
    service.db = g.db

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/')
def print_request():
    print_req(request, print)
    return 'fuck'

@app.route('/debug', methods=['POST'])
def wx_debug_helper():
    print_req(request, app.logger.info)
    return 'ok'

@app.route('/test')
def test():
    weixin.a = 'fuck qky'
    return weixin.a

@app.route('/callback')
def auth():
    return request.args.get('echostr')

def weixin_oauth2_url():
    return weixin.oauth2_url(app.config['RESTFUL_ROOT'] + '/auth/redirect')

@app.route('/callback', methods=['POST'])
def callback():
    recv_msg = MessageReceived(request.data)
    reply_msg = weixin.RepliedMessage()

    reply_msg.ToUserName = recv_msg.FromUserName
    reply_msg.FromUserName = recv_msg.ToUserName
    reply_msg.CreateTime = int(time.time()) 
    reply_msg.MsgType = 'text'
    reply_msg.Content = weixin_oauth2_url()

    return reply_msg.xml()

# 用户在网页端授权后回调至此位置
@app.route('/auth/redirect')
def auth_redirect():
    app.logger.info(request.args)
    openid = session.get('openid')
    if openid is None:
        access_token = weixin.get_web_auth_access_token(request.args.get('code'))
        app.logger.info(access_token)
        openid = access_token['openid']

    # 记录用户登录信息
    user = service.find_user(openid)
    if user is None:
        service.create_user({ 'openid': openid })
        app.logger.info('register a new user, openid: %s', openid)
    service.record_login(openid)
    app.logger.info('user: %s logined', openid)

    session['openid'] = openid
    return redirect(app.config['WEB_ROOT'] + '/index.html')

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


# DOC: https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_7
@app.route('/pay/notify', methods=['POST'])
def process_pay_result():
    app.logger.info('pay notified: %s', request.data)

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

        weixin.send_redpack(redpack)
        xml = redpack.xml()
        return xml

    reply = RepliedMessage()
    reply.return_code = 'SUCCESS'
    reply.return_msg = 'OK'
    return reply.xml()

@app.route('/pay', methods=['POST'])
def receive_tax():
    openid = 'oenW2wz47W1RisML5QijHzwRz34M'#session.get('openid')
    if openid is None:
        return redirect(weixin_oauth2_url())

    order = OrderMessage()
    order.appid = app.config['APP_ID']
    order.nonce_str = randstr()
    order.mch_id = app.config['MCH_ID']
    order.body = 'game-tax'
    order.out_trade_no = _timestamp_str()
    order.total_fee = 1
    order.spbill_create_ip = request.environ['REMOTE_ADDR']
    order.notify_url = app.config['RESTFUL_ROOT'] + '/pay/notify'
    order.trade_type = 'JSAPI'
    order.openid = openid
    order.sign()
    
    app.logger.info(order.xml())

    result = weixin.make_order(order)
    if result.return_code == 'FAIL':
        return { 'return_code': 'FAIL' }

    # todo: save pay info to db
    app.logger.info(result.xml())
    pay_sign = weixin.get_pay_sign(result.prepay_id)
    app.logger.warning(pay_sign)
    return json.dumps(pay_sign)

if __name__ == '__main__':
    app.config.from_pyfile('conf/test.config.py')
    app.run('0.0.0.0', debug=True)

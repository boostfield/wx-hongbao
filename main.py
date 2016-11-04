from __future__ import print_function
import os
import time
import sqlite3
from datetime import datetime
from logging import Formatter, FileHandler
import json
import uuid
from flask import Flask, request, redirect, session, g, abort
import service

app = Flask(__name__)
app.config.from_pyfile('conf/config.py')
app.config['CWD'] = os.path.dirname(__file__)

handler = FileHandler(app.config['LOG_FILE'])
handler.setFormatter(Formatter(app.config['LOG_FORMAT']))
app.logger.addHandler(handler)
app.logger.setLevel(app.config['LOG_LEVEL'])

import weixin
from weixin import MessageReceived, RepliedMessage, OrderMessage
weixin.logger = app.logger
weixin.ssl_cert_file = app.config['WEIXIN_SSL_CERT_FILE']
weixin.ssl_key_file = app.config['WEIXIN_SSL_KEY_FILE']

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with connect_db() as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read().decode('utf-8'))
        db.commit()

def print_req(req, printer):
    printer(req.method)
    printer(req.url)
    printer(req.headers)
    printer(req.environ)
    printer(req.form)
    printer(req.data)

def ret_msg(ret, msg = ''):
    return json.dumps({ 'ret': ret, 'msg': msg })

def randstr():
    return uuid.uuid4().hex

def _timestamp_str():
    now = datetime.now()
    return now.strftime('%Y%m%d%H%M%S%f')[0:-3]

def _build_mch_billno():
    return app.config['MCH_ID'] + _timestamp_str()

# http_msg: request or response
def get_json_object(http_msg):
    return json.loads(http_msg.data.decode('utf-8'))

def weixin_oauth2_url():
    return weixin.oauth2_url(app.config['RESTFUL_ROOT'] + '/auth/redirect')

SUCCESS = 'SUCCESS'
FAIL = 'FAIL'

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

@app.route('/callback')
def auth():
    return request.args.get('echostr')


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
    openid = session.get('openid')
    if openid is None:
        access_token = weixin.get_web_auth_access_token(request.args.get('code'))
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

def _build_order(openid, money, remote_addr):
    order = OrderMessage()
    order.appid = app.config['APP_ID']
    order.nonce_str = randstr()
    order.mch_id = app.config['MCH_ID']
    order.body = 'game-tax'
    order.out_trade_no = _timestamp_str()
    order.total_fee = money
    order.spbill_create_ip = remote_addr
    order.notify_url = app.config['RESTFUL_ROOT'] + '/pay/notify'
    order.trade_type = 'JSAPI'
    order.openid = openid
    order.sign()
    return order

def _decide_repack_money(openid):
    return 100

def _send_redpack(openid, user_pay_id):
    money = _decide_repack_money(openid)
    redpack = weixin.RedPack()
    redpack.nonce_str = randstr()
    redpack.mch_billno = _build_mch_billno()
    redpack.mch_id = app.config['MCH_ID']
    redpack.wxappid = app.config['APP_ID']
    redpack.send_name = app.config['MCH_NAME']
    redpack.re_openid = openid
    redpack.total_amount = money
    redpack.total_num = 1
    redpack.wishing = app.config['REDPACK_WISHING']
    redpack.client_ip = app.config['LOCAL_IP']
    redpack.act_name = app.config['REDPACK_ACTIVE_NAME']
    redpack.remark = app.config['REDPACK_REMARK']
    redpack.sign()
    # FIXME: 若在发出红包之后，向微信确认之前出现异常，微信会重复发送此事件，导致重复给用户发红包
    result = weixin.send_redpack(redpack)
    result = MessageReceived(result)

    sys_pay = dict(openid=openid, money=money, billno=redpack.mch_billno, user_pay_id, state='SENDED')
    service.save_sys_pay(sys_pay)

    # todo: 给用户发红包失败后应有应对措施
    if result.return_code == FAIL:
        app.logger.error('communication error while send redpack to user: %s, billno: %s, reason: %s',
                           openid, redpack.mch_billno, result.return_msg)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = result.return_msg
        service.save_sys_pay(sys_pay)
        return

    if result.result_code == FAIL:
        app.logger.error('send redpack to user: %s failed, billno: %s, reason: %s-%s',
                           openid, redpack.mch_billno, result.err_code, result.err_code_des)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = '{}-{}'.format(result.err_code, result.err_code_des)
        service.save_sys_pay(sys_pay)
        return

    app.logger.info('send redpack to user: %s success, billno: %s', openid, redpack.mch_billno)
    sys_pay['state'] = SUCCESS
    sys_pay['wx_billno'] = result.send_listid
    service.save_sys_pay(sys_pay)
    
# DOC: https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_7
@app.route('/pay/notify', methods=['POST'])
def process_pay_result():
    reply = RepliedMessage()
    reply.return_code = 'SUCCESS'
    reply.return_msg = 'OK'
    result = MessageReceived(request.data)

    if result.return_code == FAIL:
        app.logger.warning('communication error while pay notify, reason: %s', result.return_msg)
        return reply.xml()

    openid = result.openid
    trade_no = result.out_trade_no
    pay = service.find_user_pay(trade_no)
    if pay is None:
        app.logger.error('get a pay notify but not has recorded, openid: %s, trade no: %s', openid, trade_no)
        return reply.xml()
    
    if result.result_code == FAIL:
        app.logger.waring('user pay failed, openid: %s, trade no: %s, reason: %s', openid, trade_no, result.err_code_des)
        pay['state'] = FAIL
        pay['error_msg'] = result.err_code_des
        service.update_user_pay(pay)
        return reply.xml()
        
    # user pay success
    app.logger.info('user pay success, openid: %s, trade no: %s', openid, trade_no)
    pay['state'] = SUCCESS
    service.update_user_pay(pay)

    # send redpack to user
    _send_redpack(openid, pay['id'])
    return reply.xml()

@app.route('/pay', methods=['POST'])
def receive_tax():
    openid = session.get('openid')
    if openid is None:
        return redirect(weixin_oauth2_url())

    remote_addr = request.environ['REMOTE_ADDR']
    if not request.data:
        app.logger.warning("get a empty pay request from user: %s, ip: %s", openid, remote_addr)
        return ret_msg(FAIL, 'money amount is required')

    data = get_json_object(request)
    if 'money' not in data or type(data['money']) is not int or data['money'] <= 0:
        app.logger.warning("get a illegal pay request from user: %s, ip: %s", openid, remote_addr)
        return ret_msg(FAIL, 'money content error')

    order = _build_order(openid, data['money'], remote_addr)
    result = weixin.make_order(order)
    pay_info = dict(
        openid=openid,
        money=data['money'],
        trade_no=order.out_trade_no,
        ip=remote_addr,
        )

    if result.return_code == 'FAIL':
        app.logger.warning('communication error while make order, reason: %s', result.return_msg)
        pay_info['state'] = 'FAIL'
        pay_info['error_msg'] = result.return_msg
        service.save_user_pay(pay_info)
        return ret_msg(FAIL, result.return_msg)

    if result.result_code == 'FAIL':
        app.logger.warning('make order to weixin failed, reason: %d:%s', result.err_code, result.err_code_des)
        pay_info['state'] = 'FAIL'
        pay_info['error_msg'] = result.err_code_des
        service.save_user_pay(pay_info)
        return ret_msg(FAIL, "{}:{}".format(result.err_code, result.err_code_des))

    # save to db
    app.logger.info('user: %s make order success, wait to pay, trade_no: %s', openid, order.out_trade_no)
    pay_info['state'] = 'PREPAY'
    pay_info['prepay_id'] = result.prepay_id
    service.save_user_pay(pay_info)

    # get sign
    pay_sign = weixin.get_pay_sign(result.prepay_id)
    pay_sign['ret'] = SUCCESS
    pay_sign['msg'] = 'ok'
    return json.dumps(pay_sign)

# just for test
@app.route('/test/<func>', methods=['POST'])
def test(func):
    if not app.config['TESTING']:
        abort(403)

    if func == 'login':
        session['openid'] = request.args['openid']
        return 'ok'

    if func == 'logout':
        del session['openid']
    return 'ok'
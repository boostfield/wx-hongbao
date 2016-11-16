from __future__ import print_function
import os
import json
import strategy
import pymysql
from service import Service
from datetime import datetime
from logging import Formatter, FileHandler
from common import randstr, now_sec, json_dumps
from flask import Flask, request, redirect, session, g, abort

app = Flask(__name__, static_url_path='')
app.config.from_pyfile('conf/config.py')
app.config['CWD'] = os.path.dirname(os.path.abspath(__file__))
app.config['STATIC_HOME'] = app.config['CWD'] + '/static'
app.config['QRCODE_HOME'] = app.config['STATIC_HOME'] + '/qrcode'

handler = FileHandler(app.config['CWD'] + '/' + app.config['LOG_FILE'])
handler.setFormatter(Formatter(app.config['LOG_FORMAT']))
app.logger.addHandler(handler)
app.logger.setLevel(app.config['LOG_LEVEL'])
strategy.logger = app.logger

import weixin
from weixin import Message
weixin.logger = app.logger
weixin.ssl_cert_file = app.config['WEIXIN_SSL_CERT_FILE']
weixin.ssl_key_file = app.config['WEIXIN_SSL_KEY_FILE']
weixin.APP_ID = app.config['APP_ID']
weixin.APP_SECRET = app.config['APP_SECRET']
weixin.API_KEY = app.config['API_KEY']

SUCCESS = 'SUCCESS'
FAIL = 'FAIL'

def connect_db():
    return pymysql.connect(app.config['DB_HOST'], app.config['DB_USER'], app.config['DB_PASS'], app.config['DB_SCHEMA'],
                           use_unicode=True, charset='utf8')

def init_db():
    with connect_db() as db:
        with app.open_resource('schema.mysql.sql') as f:
            db.execute(f.read().decode('utf-8'))

def shared_money(money):
    return int(money * app.config['AGENT_SHARE_PERCENT'])

def create_menu():
    menu = {
        'button': [{
            'type': 'view',
            'name': '开始游戏',
            'url': app.config['AUTH2_SHORT_URL']
        }]}
    rsp = weixin.create_menu(menu)
    app.logger.info('create menu return: %s', rsp['errmsg'])

def print_req(req, printer):
    printer(req.method)
    printer(req.url)
    printer(req.headers)
    printer(req.environ)
    printer(req.form)
    printer(req.data)

def ret_msg(ret, msg = ''):
    return json_dumps({ 'ret': ret, 'msg': msg })

def _timestamp_str():
    now = datetime.now()
    return now.strftime('%Y%m%d%H%M%S%f')[0:-3]

def build_mch_billno():
    return app.config['MCH_ID'] + _timestamp_str()

# http_msg: request or response
def get_json_object(http_msg):
    return json.loads(http_msg.data.decode('utf-8'))

def weixin_oauth2_url():
    return weixin.oauth2_url(app.config['RESTFUL_ROOT'] + '/auth/redirect')

def _get_agent(eventkey):
    content = eventkey[len('qrscene_'):]
    return int(content)

def _handle_subscribe(service, msg):
    user = service.find_user(msg.FromUserName)
    if 'EventKey' in msg:
        agent = _get_agent(msg.EventKey)
        # 分销关注
        if user is None:
            app.logger.info('user: %s subscribe app follow by agent: %d', msg.FromUserName, agent)
            service.create_user(msg.FromUserName, agent)
            service.save_event(msg.FromUserName, 'follow', agent)
        else:
            app.logger.info('user: %s subscribe app follow by agent: %d, but has registered', msg.FromUserName, agent)
            service.save_event(msg.FromUserName, 'refollow', agent)
    else:
        # 主动关注
        if user is None:
            app.logger.info('new user: %s subscribe app, register', msg.FromUserName)
            service.create_user(msg.FromUserName)
        else:
            app.logger.info('user: %s subscribe app', msg.FromUserName)
        service.save_event(msg.FromUserName, 'subscribe')

    session['openid'] = msg.FromUserName
    return SUCCESS
            
def _handle_unsubscribe(service, msg):
    app.logger.info('user %s unsubscribe app', msg.FromUserName)
    service.save_event(msg.FromUserName, msg.Event)
    return SUCCESS

def _handle_scan(service, msg):
    agent = int(msg.EventKey)
    app.logger.info('user %s scan qrcode own by user: %d', msg.FromUserName)
    service.save_event(msg.FromUserName, msg.Event, agent)
    return SUCCESS
    
def _build_order(openid, money, remote_addr):
    order = Message()
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

def _send_redpack(service, openid, user_pay_id, money):
    money = strategy.get_strategy().pay(openid, money)
    redpack = Message()
    redpack.nonce_str = randstr()
    redpack.mch_billno = build_mch_billno()
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

    sys_pay = dict(openid=openid, money=money, billno=redpack.mch_billno,
                   user_pay_id=user_pay_id, state='SENDED', type='RETURN')
    service.save_sys_pay(sys_pay)

    # todo: 给用户发红包失败后应有应对措施
    if result.return_code == FAIL:
        app.logger.error('communication error while send redpack to user: %s, billno: %s, reason: %s',
                           openid, redpack.mch_billno, result.return_msg)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = result.return_msg
        service.update_sys_pay(sys_pay)
        return

    if result.result_code == FAIL:
        app.logger.error('send redpack to user: %s failed, billno: %s, reason: %s-%s',
                           openid, redpack.mch_billno, result.err_code, result.err_code_des)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = '{}-{}'.format(result.err_code, result.err_code_des)
        service.update_sys_pay(sys_pay)
        return

    app.logger.info('send redpack to user: %s success, billno: %s', openid, redpack.mch_billno)
    
    sys_pay['state'] = SUCCESS
    sys_pay['wx_billno'] = result.send_listid
    service.update_sys_pay(sys_pay)
    
@app.before_request
def before_request():
    g.db = connect_db()
    g.service = Service(g.db)

@app.after_request
def after_request(response):
    g.db.close()
    return response

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/debug', methods=['POST'])
def wx_debug_helper():
    print_req(request, app.logger.info)
    return 'ok'

@app.route('/api/callback')
def auth():
    return request.args.get('echostr')

@app.route('/api/callback', methods=['POST'])
def callback():
    msg = Message(request.data)
    if msg.MsgType == 'event':
        if msg.Event == 'subscribe':
            return _handle_subscribe(g.service, msg)
        if msg.Event == 'unsubscribe':
            return _handle_unsubscribe(g.service, msg)
        if msg.Event == 'SCAN':
            return _handle_scan(g.service, msg)
        
    reply_msg = Message()

    reply_msg.ToUserName = msg.FromUserName
    reply_msg.FromUserName = msg.ToUserName
    reply_msg.CreateTime = now_sec()
    reply_msg.MsgType = 'image'
    reply_msg.Content = app.config['AUTH2_SHORT_URL']

    return reply_msg.xml()

@app.route('/api/share/qrcode')
def get_user_share_qrcode():
    openid = session.get('openid')
    if not openid:
        return redirect(weixin_oauth2_url())

    user = g.service.find_user(openid)
    rsp = dict(ret=SUCCESS, msg='ok')
    if not user['share_qrcode']:
        qr_file = randstr()
        ticket = weixin.get_unlimit_qrcode_ticket(user['id'])
        if weixin.dump_qrcode(ticket, app.config['QRCODE_HOME'] + '/' + qr_file):
            user['share_qrcode'] = qr_file
            g.service.update_user(user)
        else:
            rsp = dict(ret=FAIL, msg='download qrcode failed')
            return json_dumps(rsp)
            
    rsp['qrcode'] = user['share_qrcode']
    app.logger.debug("user: %s, get qrcode return: %s", openid, rsp)
    return json_dumps(rsp)

# 用户在网页端授权后回调至此位置
@app.route('/api/auth/redirect')
def auth_redirect():
    openid = session.get('openid')
    if openid is None:
        access_token = weixin.get_web_auth_access_token(request.args.get('code'))
        if 'errcode' in access_token:
            app.logger.warn("get weixin auth access token failed: %d:%s", access_token['errcode'], access_token['errmsg'])
            return redirect(weixin_oauth2_url())
        openid = access_token['openid']

    # 记录用户登录信息
    user = g.service.find_user(openid)
    if user is None:
        g.service.create_user(openid)
        app.logger.info('register a new user, openid: %s', openid)
    g.service.record_login(openid)
    app.logger.info('user: %s logined', openid)

    session['openid'] = openid
    return redirect(app.config['WEB_ROOT'] + '/index.html')

@app.route('/api/jsapi/sign')
def get_jsapi_sign():
    url = request.args.get('url')   # 当前需要执行jsapi的url
    if url is None:
        return 'fuck you'

    return json_dumps(weixin.get_jsapi_sign(url))

# DOC: https://pay.weixin.qq.com/wiki/doc/api/jsapi.php?chapter=9_7
@app.route('/api/pay/notify', methods=['POST'])
def process_pay_result():
    reply = Message()
    reply.return_code = SUCCESS
    reply.return_msg = 'OK'
    result = Message(request.data)

    if result.return_code == FAIL:
        app.logger.warning('communication error while pay notify, reason: %s', result.return_msg)
        return reply.xml()

    if not result.check_sign():
        app.logger.warning('check weixin pay notify sign failed, openid: %s, from ip: %s', result.openid, request.environ['REMOTE_ADDR'])
        reply.return_code = FAIL
        rsply.return_msg = 'check sign failed'
        return reply.xml()
    
    openid = result.openid
    trade_no = result.out_trade_no
    pay = g.service.find_user_pay(trade_no)
    if pay is None:
        app.logger.error('get a pay notify but not has recorded, openid: %s, trade no: %s', openid, trade_no)
        return reply.xml()
    
    if result.result_code == FAIL:
        app.logger.waring('user pay failed, openid: %s, trade no: %s, reason: %s', openid, trade_no, result.err_code_des)
        pay['state'] = FAIL
        pay['error_msg'] = result.err_code_des
        g.service.update_user_pay(pay)
        return reply.xml()
        
    # user pay success
    app.logger.info('user pay success, openid: %s, trade no: %s', openid, trade_no)
    pay['state'] = SUCCESS
    g.service.update_user_pay(pay)

    # send redpack to user
    _send_redpack(g.service, openid, pay['id'], pay['money'])
    return reply.xml()

@app.route('/api/pay', methods=['POST'])
def receive_tax():
    openid = session.get('openid')
    if openid is None:
        return redirect(weixin_oauth2_url())

    remote_addr = request.environ['REMOTE_ADDR']
    if not request.data:
        app.logger.warning("get a empty pay request from user: %s, ip: %s", openid, remote_addr)
        return ret_msg(FAIL, 'money amount is required')

    data = get_json_object(request)
    if 'money' not in data or type(data['money']) is not int or data['money'] not in app.config['AVAILABLE_PAY_MONEY']:
        app.logger.warning("get a illegal pay request from user: %s, ip: %s, illegal money: %s", openid, remote_addr, str(data.get('money')))
        return ret_msg(FAIL, 'money content error')

    order = _build_order(openid, data['money'], remote_addr)
    result = weixin.make_order(order)
    pay_info = dict(openid=openid, money=data['money'], trade_no=order.out_trade_no, ip=remote_addr,)

    if result.return_code == FAIL:
        app.logger.warning('communication error while make order, reason: %s', result.return_msg)
        pay_info['state'] = FAIL
        pay_info['error_msg'] = result.return_msg
        g.service.save_user_pay(pay_info)
        return ret_msg(FAIL, result.return_msg)

    if result.result_code == FAIL:
        app.logger.warning('make order to weixin failed, reason: %d:%s', result.err_code, result.err_code_des)
        pay_info['state'] = FAIL
        pay_info['error_msg'] = result.err_code_des
        g.service.save_user_pay(pay_info)
        return ret_msg(FAIL, "{}:{}".format(result.err_code, result.err_code_des))

    # save to db
    app.logger.info('user: %s make order success, wait to pay, trade_no: %s', openid, order.out_trade_no)
    pay_info['state'] = 'PREPAY'
    pay_info['prepay_id'] = result.prepay_id
    g.service.save_user_pay(pay_info)

    # get sign
    pay_sign = weixin.get_pay_sign(result.prepay_id)
    pay_sign['ret'] = SUCCESS
    pay_sign['msg'] = 'ok'
    return json_dumps(pay_sign)

@app.route('/api/income/last')
def get_user_last_income():
    openid = session.get('openid')
    if openid is None:
        return redirect(weixin_oauth2_url())

    rsp = g.service.find_user_last_income(openid)
    rsp = rsp or (None, None)
    ret = dict(ret=SUCCESS, msg='ok', money=rsp[0], time=rsp[1])
    if rsp[0] is None:
        ret['msg'] = 'not found' 
        
    return json_dumps(ret)


@app.route('/api/agent/account')
def get_user_account_detail_as_agent():
    openid = session.get('openid')
    if openid is None:
        return redirect(weixin_oauth2_url())
    # todo: 检查参数中是否仅包含数字

    page = int(request.args.get('page', 0))
    pagesize = int(request.args.get('pagesize', 50))
    _offset = page * pagesize
    
    total_bill_num = g.service.find_agent_bill_num(openid)
    shared_bill_num = g.service.find_agent_shared_bill_num(openid)
    bills = g.service.find_agent_bill(openid, _offset, pagesize)

    total_income = 0
    shared_income = 0
    ret_bills = []
    for b in bills:
        income = shared_money(b['money'])
        total_income += income
        shared_income += b['shared_money'] or 0
        ret_bills.append(dict(income=income, time=b['timestamp'], shared=(b['shared_money'] is not None), share_time=b['shared_timestamp']))

    ret = dict(ret=SUCCESS, msg='ok', total_bill_num=total_bill_num, shared_bill_num=shared_bill_num,
               page=page, pagesize=pagesize, total_income=total_income, shared_income=shared_income,
               follower_num=g.service.find_follower_num(openid), bills=ret_bills)
    return json_dumps(ret)
    
# just for test
@app.route('/api/test/<func>', methods=['POST'])
def test(func):
    if not app.config['TESTING']:
        abort(403)

    if func == 'login':
        session['openid'] = request.args['openid']
        return 'ok'

    if func == 'logout':
        del session['openid']

    if func == 'session':
        return json_dumps(dict(session))
    return 'ok'

if __name__ == '__main__':
    debug = app.config['TESTING']
    app.run('0.0.0.0', port=80, threaded=True, debug=debug)

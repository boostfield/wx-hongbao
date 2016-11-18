#! /usr/bin/env python3

import os
import sys
cdir = os.path.dirname(os.path.abspath(__file__))
homedir = os.path.join(cdir, '..')
sys.path.append(homedir)
import main
from main import app
from service import Service
import weixin
from weixin import Message
from itertools import groupby

SUCCESS = 'SUCCESS'
FAIL = 'FAIL'
service = None

def _init_redpack():
    red = Message()
    red.nonce_str = main.randstr()
    red.mch_billno = main.build_mch_billno()
    red.mch_id = app.config['MCH_ID']
    red.wxappid = app.config['APP_ID']
    red.send_name = app.config['MCH_NAME']
    red.total_num = 1
    red.wishing = '会员返利'
    red.client_ip = app.config['LOCAL_IP']
    red.act_name = app.config['REDPACK_ACTIVE_NAME']
    red.remark = app.config['REDPACK_REMARK']
    return red

def _share(agent_openid, fee, user_pay_id):
    redpack = _init_redpack()
    redpack.total_amount = fee
    redpack.re_openid = agent_openid
    redpack.sign()

    result = weixin.send_redpack(redpack)

    sys_pay = dict(openid=agent_openid, money=fee, billno=redpack.mch_billno, state='SENDED', type='SHARE')
    service.save_sys_pay(sys_pay)
    sys_pay = service.find_sys_pay(sys_pay['billno'])

    if result.return_code == FAIL:
        app.logger.error('communication error while send redpack to user: %s, billno: %s, reason: %s',
                           agent_openid, redpack.mch_billno, result.return_msg)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = result.return_msg
        service.update_sys_pay(sys_pay)
        return sys_pay

    if result.result_code == FAIL:
        app.logger.error('send redpack to user: %s failed, billno: %s, reason: %s-%s',
                           agent_openid, redpack.mch_billno, result.err_code, result.err_code_des)
        sys_pay['state'] = FAIL
        sys_pay['error_msg'] = '{}-{}'.format(result.err_code, result.err_code_des)
        service.update_sys_pay(sys_pay)
        return sys_pay

    app.logger.info('send redpack to user: %s success, billno: %s', openid, redpack.mch_billno)

    sys_pay['state'] = SUCCESS
    sys_pay['wx_billno'] = result.send_listid
    service.update_sys_pay(sys_pay)
    return sys_pay

def save_shares(profits, sys_pay_id):
    for p in profits:
        service.save_share(p['user_pay_id'], sys_pay_id, main.shared_money(p['money']))
        
# 处理一个 agent 的分红
def settlement(agent, profits):
    fee = 0
    total = 0
    profits_in_one_share = []
    for p in profits:
        share = main.shared_money(p['money'])
        if fee + share > app.config['REDPACK_MAX']:
            sys_pay = _share(p['agent_openid'], fee, p['user_pay_id'])
            if sys_pay['state'] == SUCCESS:
                save_shares(profits_in_one_share, sys_pay['id'])
                total += fee
            profits_in_one_share = []
            fee = 0
        fee += share
        profits_in_one_share.append(p)

    if fee > app.config['REDPACK_MIN']:
        sys_pay = _share(p['agent_openid'], fee, p['user_pay_id'])
        if sys_pay['state'] == SUCCESS:
            save_shares(profits_in_one_share, sys_pay['id'])
            total += fee
    app.logger.info('share %d points to user: %d', total, agent)
        

if __name__ == '__main__':
    app.logger.info('share profilt run')

    service = Service(main.connect_db())
    weixin.ssl_cert_file = './apiclient_cert.pem'
    weixin.ssl_key_file = './apiclient_key.pem'
    profit = service.find_unshared_profit()

    for k, g in groupby(profit, lambda x: x['agent']):
        settlement(k, g)

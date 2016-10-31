# -*- encoding: utf-8 -*-

import xml.etree.ElementTree as ET
import urllib
import json
import uuid
import hashlib
import time

#APP_ID = 'wxf7b5161f46d0b191'
#APP_SECRET = 'b73f9b5da3cc4f7b0e09eb3d148c0447'
APP_ID = 'wx9fb7ef78c47f8ef2'
APP_SECRET = '4c7b0db408b0c1b4242337ade30120f1'
API_KEY = 'get_from_pay.weixin.qq.com'
WX_URL_GET_ACCESS_TOKEN = 'https://api.weixin.qq.com/cgi-bin/token'
WX_URL_CREATE_MENU = 'https://api.weixin.qq.com/cgi-bin/menu/create'
WX_URL_OAUTH2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
WX_URL_WEB_AUTH_ACCESS_TOKEN = 'https://api.weixin.qq.com/sns/oauth2/access_token'
WX_URL_MAKE_ORDER = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
WX_URL_GET_JSAPI_TICKET = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket' #?access_token=ACCESS_TOKEN&type=jsapi

_access_token = {
        'token': None,
        'timestamp': 0
        }

_jsapi_ticket = {
        'ticket': None,
        'timestamp': 0
        }

def query_str(kw):
    querys = ["{}={}".format(key, kw[key]) for key in kw]
    return '&'.join(querys)

def _http_req(url, args={}, data=None):
    query = query_str(args)
    if query:
        url += '?' + query

    rsp = urllib.urlopen(url, data)
    return rsp.read().decode('utf-8')

def http_get(url, **kws):
    return _http_req(url, kws)

def http_post(url, data, **kws):
    return _http_req(url, kws, data)

def now():
    return int(time.time()) 

def randstr():
    return uuid.uuid4().hex

def sha1_sign(s):
    sha1 = hashlib.sha1()
    sha1.update(s)
    return sha1.hexdigest()

def _build_jsapi_sign(ticket, noncestr, timestamp, url):
    string = 'jsapi_ticket={}&noncestr={}&timestamp={}&url={}'.format(ticket, noncestr, timestamp, url)
    return sha1_sign(string)


def get_access_token():
    if _access_token['token'] is None or _access_token['timestamp'] + 7000 <= now():
        _access_token['token'] = json.loads(http_get(WX_URL_GET_ACCESS_TOKEN, grant_type='client_credential', appid=APP_ID, secret=APP_SECRET))['access_token']
        _access_token['timestamp'] = now()
    return _access_token['token']

def get_web_auth_access_token(code):
    return json.loads(http_get(WX_URL_WEB_AUTH_ACCESS_TOKEN, appid=APP_ID, secret=APP_SECRET, code=code, grant_type='authorization_code'))

def get_jsapi_sign(url):
    if _jsapi_ticket['ticket'] is None or _jsapi_ticket['timestamp'] + 7000 <= now():
        access_token = get_access_token()
        _jsapi_ticket['ticket'] = json.loads(http_get(WX_URL_GET_JSAPI_TICKET, access_token=access_token, type='jsapi'))['ticket']
        _jsapi_ticket['timestamp'] = now()

    noncestr = randstr()
    timestamp = now()
    sign = _build_jsapi_sign(_jsapi_ticket['ticket'], noncestr, timestamp, url)
    return {
            'noncestr': noncestr,
            'sign': sign,
            'timestamp': timestamp,
            'appid': APP_ID
            }

def oauth2_url(redirect_uri):
    params = (
            ('appid', APP_ID),
            ('redirect_uri', redirect_uri),
            ('response_type', 'code'),
            ('scope', 'snsapi_base'),
            ('state', 'STATE')
            )
    return '{}?{}#wechat_redirect'.format(WX_URL_OAUTH2, urllib.urlencode(params))

def make_order(order):
    return http_post(WX_URL_MAKE_ORDER, order.xml())

def create_menu():
    access_token = get_access_token()

class MessageReceived(object):
    def __init__(self, xml):
        self._xml = xml
        self._root = ET.fromstring(xml)
    
    def __getattr__(self, key, type=None):
        ele = self._root.find(key)
        if ele is not None:
            return ele.text

class MessageReplied(object):
    def xml(self):
        root = ET.Element('xml')
        for k, v in self.__dict__.iteritems():
            e = ET.SubElement(root, k)
            e.text = str(v)
            
        return ET.tostring(root)

    def __getattr__(self, key, type=None):
        return self.__dict__.get(key)
    
    def __setattr__(self, key, value):
        self.__dict__[key] = value

class OrderMessage(object):
    def __init__(self):
        self.appid = APP_ID 
        self.nonce_str = randstr()

    def xml(self):
        if self.sign is None:
            self.sign = self._build_sign()

        root = ET.Element('xml')
        for k, v in self.__dict__.iteritems():
            e = ET.SubElement(root, k)
            e.text = str(v)
            
        return ET.tostring(root, encoding='UTF-8')

    def _build_sign(self):
        argstr = self._arg_string()
        argstr += '&key=' + API_KEY
        md5 = hashlib.md5()
        md5.update(argstr)
        md5str = md5.hexdigest()
        return md5str.upper()

    # 拼接所有参数以生成签名
    def _arg_string(self):
        keys = self.__dict__.keys()
        keys.sort()
        return '&'.join(['{}={}'.format(k, self.__dict__[k]) for k in keys])
        
    def __getattr__(self, key, type=None):
        return self.__dict__.get(key)

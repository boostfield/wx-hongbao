import xml.etree.ElementTree as ET
import urllib.request
import json
import uuid
import hashlib
import time
import ssl

# == 由外部赋值 ==
logger = None       
ssl_cert_file = None
ssl_key_file = None
APP_ID = 'wx9fb7ef78c47f8ef2'
APP_SECRET = '4c7b0db408b0c1b4242337ade30120f1'
API_KEY = 'ac3d073861ac4035b2187549a3d4fd61'
# ================

WX_URL_GET_ACCESS_TOKEN = 'https://api.weixin.qq.com/cgi-bin/token'
WX_URL_CREATE_MENU = 'https://api.weixin.qq.com/cgi-bin/menu/create'
WX_URL_OAUTH2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
WX_URL_WEB_AUTH_ACCESS_TOKEN = 'https://api.weixin.qq.com/sns/oauth2/access_token'
WX_URL_MAKE_ORDER = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
WX_URL_SEND_REDPACK = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack'
WX_URL_GET_JSAPI_TICKET = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket' #?access_token=ACCESS_TOKEN&type=jsapi
_access_token = {
        'token': None,
        'timestamp': 0
        }

_jsapi_ticket = {
        'ticket': None,
        'timestamp': 0
        }

def _query_str(kw):
    querys = ["{}={}".format(key, kw[key]) for key in kw]
    return '&'.join(querys)

def _http_req(url, args={}, data=None):
    query = _query_str(args)
    if query:
        url += '?' + query

    rsp = urllib.request.urlopen(url, data)
    return rsp.read().decode('utf-8')

def http_get(url, **kws):
    return _http_req(url, kws)

def http_post(url, data, **kws):
    return _http_req(url, kws, data)

def ssl_http_post(url, data):
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.load_cert_chain(ssl_cert_file, ssl_key_file)
    rsp = urllib.request.urlopen(url, data, context=context)
    return rsp.read().decode('utf-8')

def now():
    return int(time.time()) 

def randstr():
    return uuid.uuid4().hex

def _sha1_sign(s):
    sha1 = hashlib.sha1()
    sha1.update(s.encode('utf-8'))
    return sha1.hexdigest()

def _md5_sign(s):
    md5 = hashlib.md5()
    md5.update(s.encode('utf-8'))
    return md5.hexdigest()

def _build_jsapi_sign(ticket, noncestr, timestamp, url):
    string = 'jsapi_ticket={}&noncestr={}&timestamp={}&url={}'.format(ticket, noncestr, timestamp, url)
    return _sha1_sign(string)


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

def get_pay_sign(prepay_id):
    sign_items = {
            'nonceStr': randstr(),
            'timeStamp': str(now()),
            'package': 'prepay_id=' + prepay_id,
            'signType': 'MD5',
            'appId': APP_ID
            }
    sign_items['paySign'] = _pay_sign(sign_items)
    return sign_items

def oauth2_url(redirect_uri):
    params = (
            ('appid', APP_ID),
            ('redirect_uri', redirect_uri),
            ('response_type', 'code'),
            ('scope', 'snsapi_base'),
            ('state', 'STATE')
            )
    return '{}?{}#wechat_redirect'.format(WX_URL_OAUTH2, urllib.parse.urlencode(params))

def make_order(order):
    result = http_post(WX_URL_MAKE_ORDER, order.xml())
    return MessageReceived(result)

def create_menu():
    access_token = get_access_token()

def send_redpack(redpack):
    result = ssl_http_post(WX_URL_SEND_REDPACK, redpack.xml())
    return result

def _pay_sign(kvs):
    keys = list(kvs.keys())
    keys.sort()
    signstr = '&'.join([u'{}={}'.format(k, kvs[k]) for k in keys])    # 拼接所有参数以生成签名
    signstr += '&key=' + API_KEY
    
    return _md5_sign(signstr).upper()
    

class MessageReceived(object):
    def __init__(self, xml):
        self._xml = xml
        self._root = ET.fromstring(xml)
    
    def __getattr__(self, key, type=None):
        ele = self._root.find(key)
        if ele is not None:
            return ele.text

    def xml(self):
        return self._xml

class RepliedMessage(object):
    def xml(self):
        root = ET.Element('xml')
        for k, v in self.__dict__.items():
            e = ET.SubElement(root, k)
            e.text = str(v)
            
        return ET.tostring(root, encoding='UTF-8')

    def __getattr__(self, key, type=None):
        return self.__dict__.get(key)


class Signer(object):
    def sign(self):
        self.sign = self.signstr()

    def signstr(self, kvs = None):
        kvs = kvs or self.__dict__
        keys = list(kvs.keys())
        keys.sort()
        _signstr = '&'.join([u'{}={}'.format(k, kvs[k]) for k in keys])    # 拼接所有参数以生成签名
        _signstr += '&key=' + API_KEY
        
        return self._md5_sign(_signstr).upper()

    def _md5_sign(self, s):
        md5 = hashlib.md5()
        md5.update(s.encode('utf-8'))
        return md5.hexdigest()

class RedPack(RepliedMessage, Signer):
    pass

class OrderMessage(RepliedMessage, Signer):
    pass

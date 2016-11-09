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
APP_ID = None
APP_SECRET = None
API_KEY = None
# ================

WX_URL_GET_ACCESS_TOKEN = 'https://api.weixin.qq.com/cgi-bin/token'
WX_URL_CREATE_MENU = 'https://api.weixin.qq.com/cgi-bin/menu/create'
WX_URL_OAUTH2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
WX_URL_WEB_AUTH_ACCESS_TOKEN = 'https://api.weixin.qq.com/sns/oauth2/access_token'
WX_URL_MAKE_ORDER = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
WX_URL_SEND_REDPACK = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack'
WX_URL_GET_JSAPI_TICKET = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket' #?access_token=ACCESS_TOKEN&type=jsapi
WX_URL_GET_QRCODE = 'https://api.weixin.qq.com/cgi-bin/qrcode/create'
WX_URL_SHORTURL = 'https://api.weixin.qq.com/cgi-bin/shorturl'

_access_token = {
        'token': None,
        'timestamp': 0
        }

_jsapi_ticket = {
        'ticket': None,
        'timestamp': 0
        }

def now():
    return int(time.time()) 

def randstr():
    return uuid.uuid4().hex

class Message:
    def _inflate(self, xml):
        root = ET.fromstring(xml)
        for item in root:
            self.__dict__[item.tag] = item.text
        
    def __init__(self, xml=None):
        if xml:
            self._inflate(xml)

    def __iter__(self):
        return iter(self.__dict__)

    def sign(self):
        self.sign = Signer.signstr(self.__dict__)

    def xml(self):
        root = ET.Element('xml')
        for k, v in self.__dict__.items():
            e = ET.SubElement(root, k)
            e.text = str(v)
            
        return ET.tostring(root, encoding='UTF-8')

class Signer:
    @classmethod
    def signstr(cls, kvs):
        keys = list(kvs.keys())
        keys.sort()
        _signstr = '&'.join([u'{}={}'.format(k, kvs[k]) for k in keys])    # 拼接所有参数以生成签名
        _signstr += '&key=' + API_KEY
        
        return cls.md5_sign(_signstr).upper()

    @classmethod
    def md5_sign(cls, s):
        md5 = hashlib.md5()
        md5.update(s.encode('utf-8'))
        return md5.hexdigest()

    @staticmethod
    def sha1_sign(s):
        sha1 = hashlib.sha1()
        sha1.update(s.encode('utf-8'))
        return sha1.hexdigest()

class HTTP:
    @classmethod
    def get(cls, url, **kws):
        return cls._req(url, kws)

    @classmethod
    def _query_str(cls, kw):
        querys = ["{}={}".format(key, kw[key]) for key in kw]
        return '&'.join(querys)

    @classmethod
    def _req(cls, url, args={}, data=None):
        query = cls._query_str(args)
        if query:
            url += '?' + query

        rsp = urllib.request.urlopen(url, data)
        return rsp.read().decode('utf-8')

    @classmethod
    def post(cls, url, data, **kws):
        if type(data) is str:
            data = data.encode('utf-8')
        return cls._req(url, kws, data)

    @classmethod
    def ssl_post(cls, url, data):
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.load_cert_chain(ssl_cert_file, ssl_key_file)
        rsp = urllib.request.urlopen(url, data, context=context)
        return rsp.read().decode('utf-8')

def _build_jsapi_sign(ticket, noncestr, timestamp, url):
    string = 'jsapi_ticket={}&noncestr={}&timestamp={}&url={}'.format(ticket, noncestr, timestamp, url)
    return Signer.sha1_sign(string)

def get_access_token():
    if _access_token['token'] is None or _access_token['timestamp'] + 7000 <= now():
        _access_token['token'] = json.loads(HTTP.get(WX_URL_GET_ACCESS_TOKEN, grant_type='client_credential', appid=APP_ID, secret=APP_SECRET))['access_token']
        _access_token['timestamp'] = now()
    return _access_token['token']

def get_web_auth_access_token(code):
    return json.loads(HTTP.get(WX_URL_WEB_AUTH_ACCESS_TOKEN, appid=APP_ID, secret=APP_SECRET, code=code, grant_type='authorization_code'))

def get_jsapi_sign(url):
    if _jsapi_ticket['ticket'] is None or _jsapi_ticket['timestamp'] + 7000 <= now():
        access_token = get_access_token()
        _jsapi_ticket['ticket'] = json.loads(HTTP.get(WX_URL_GET_JSAPI_TICKET, access_token=access_token, type='jsapi'))['ticket']
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
    sign_items['paySign'] = Signer.signstr(sign_items)
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
    result = HTTP.post(WX_URL_MAKE_ORDER, order.xml())
    return Message(result)

def create_menu(menu):
    logger.info(json.dumps(menu))
    rsp = HTTP.post(WX_URL_CREATE_MENU, json.dumps(menu, ensure_ascii=False), access_token=get_access_token())
    
    return json.loads(rsp)

def send_redpack(redpack):
    result = HTTP.ssl_post(WX_URL_SEND_REDPACK, redpack.xml())
    return result

def get_unlimit_qrcode_ticket(arg):
    args = {
        'action_name': 'QR_LIMIT_SCENE',
        'action_info': {
            'scene': {
                'scene_id': arg
                }
            }
        }
    logger.debug(args)
    rsp = HTTP.post(WX_URL_GET_QRCODE, json.dumps(args), access_token=get_access_token())
    logger.debug('get a unlimit qrcode, arg: %s, ret: %s', arg, rsp)
    rsp = json.loads(rsp)
    return rsp['ticket']

def url_to_short(url):
    data = dict(action='long2short', long_url=url)
    rsp = HTTP.post(WX_URL_SHORTURL, json.dumps(data), access_token=get_access_token())
    return json.loads(rsp)

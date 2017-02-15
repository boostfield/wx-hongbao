import json
import hashlib
import urllib
import socket
import struct
import base64
from httplib import HTTP
from common import now_sec, randstr
from Crypto.Cipher import AES
import xml.etree.ElementTree as ET

# == 由外部赋值 ==
logger = None       
ssl_cert_file = None
ssl_key_file = None
APP_ID = None
APP_SECRET = None
API_KEY = None
ENCODING_AES_KEY = None
TOKEN = None
# ================

WX_URL_GET_ACCESS_TOKEN = 'https://api.weixin.qq.com/cgi-bin/token'
WX_URL_CREATE_MENU = 'https://api.weixin.qq.com/cgi-bin/menu/create'
WX_URL_OAUTH2 = 'https://open.weixin.qq.com/connect/oauth2/authorize'
WX_URL_WEB_AUTH_ACCESS_TOKEN = 'https://api.weixin.qq.com/sns/oauth2/access_token'
WX_URL_MAKE_ORDER = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
WX_URL_SEND_REDPACK = 'https://api.mch.weixin.qq.com/mmpaymkttransfers/sendredpack'
WX_URL_GET_JSAPI_TICKET = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket'
WX_URL_CREATE_QRCODE = 'https://api.weixin.qq.com/cgi-bin/qrcode/create'
WX_URL_SHORTURL = 'https://api.weixin.qq.com/cgi-bin/shorturl'
WX_URL_GET_QRCODE = 'https://mp.weixin.qq.com/cgi-bin/showqrcode'

_access_token = {
        'token': None,
        'timestamp': 0
        }

_jsapi_ticket = {
        'ticket': None,
        'timestamp': 0
        }

class PKCS7Encoder():
    """提供基于PKCS7算法的加解密接口"""
    block_size = 32
    def encode(self, text):
        """ 对需要加密的明文进行填充补位
        @param text: 需要进行填充补位操作的明文
        @return: 补齐明文字符串
        """
        text_length = len(text)
        # 计算需要填充的位数
        amount_to_pad = self.block_size - (text_length % self.block_size)
        if amount_to_pad == 0:
            amount_to_pad = self.block_size
        # 获得补位所用的字符
        pad = bytes(chr(amount_to_pad), 'utf-8')
        return text + pad * amount_to_pad

    def decode(self, decrypted):
        """删除解密后明文的补位字符
        @param decrypted: 解密后的明文
        @return: 删除补位字符后的明文
        """
        pad = ord(decrypted[-1])
        if pad<1 or pad >32:
            pad = 0
        return decrypted[:-pad]

class Message:
    def _inflate(self, xml):
        root = ET.fromstring(xml)
        for item in root:
            self.__dict__[item.tag] = item.text
        
    def __init__(self, arg=None):
        if arg:
            if isinstance(arg, dict):
                self.__dict__ = arg.copy()
            else:
                self._inflate(arg)

    def __iter__(self):
        return iter(self.__dict__)

    def sign(self):
        self.sign = Signer.signstr(self.__dict__)

    def check_sign(self):
        if 'sign' not in self or not self.sign:
            return False
        
        _dict = self.__dict__.copy()
        del _dict['sign']
        return self.sign == Signer.signstr(_dict)
            

    def xml(self):
        root = ET.Element('xml')
        for k, v in self.__dict__.items():
            e = ET.SubElement(root, k)
            if isinstance(v, str):
                e.text = v
            elif isinstance(v, bytes):
                e.text = v.decode('utf-8')
            else:
                e.text = str(v)
            
        return ET.tostring(root, encoding='UTF-8')

    def _encrypt(self):
        text = self.xml()
        text = bytes(randstr(16), 'utf-8') + struct.pack("I", socket.htonl(len(text))) + text + bytes(APP_ID, 'utf-8')
        text = PKCS7Encoder().encode(text)

        key = base64.b64decode(ENCODING_AES_KEY)
        cryptor = AES.new(key, AES.MODE_CBC, key[:16])
        cipher = cryptor.encrypt(text)
        return base64.b64encode(cipher)

    def _decrypt(self, text):
        key = base64.b64decode(ENCODING_AES_KEY)
        cryptor = AES.new(key, AES.MODE_CBC, key[:16])
        plain_text = cryptor.decrypt(base64.b64decode(text))
        
        pad = plain_text[-1]
        content = plain_text[16:-pad]
        xml_len = socket.ntohl(struct.unpack("I", content[:4])[0])
        xml_content = content[4:xml_len+4]
        from_appid = content[xml_len+4:]
        return xml_content

    def _sign_msg(self, timestamp, nonce, encrypt):
        items = [bytes(TOKEN, 'utf-8'), bytes(timestamp, 'utf-8'), bytes(nonce, 'utf-8'), encrypt]
        items.sort()
        return Signer.sha1_sign(b''.join(items))
    
    def encrypt(self):
        msg = Message()
        msg.TimeStamp = str(now_sec())
        msg.Nonce = randstr()
        msg.Encrypt = self._encrypt()
        msg.MsgSignature = self._sign_msg(msg.TimeStamp, msg.Nonce, msg.Encrypt)
        return msg

    def decrypt(self):
        if 'Encrypt' not in self.__dict__:
            return Message(self.__dict__)
        else:
            plain_text = self._decrypt(self.Encrypt)
            return Message(plain_text)
        

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
        if isinstance(s, bytes):
            sha1.update(s)
        else:
            sha1.update(s.encode('utf-8'))
        return sha1.hexdigest()

def _build_jsapi_sign(ticket, noncestr, timestamp, url):
    string = 'jsapi_ticket={}&noncestr={}&timestamp={}&url={}'.format(ticket, noncestr, timestamp, url)
    return Signer.sha1_sign(string)

def get_access_token():
    if _access_token['token'] is None or _access_token['timestamp'] + 7000 <= now_sec():
        _access_token['token'] = json.loads(HTTP.get(WX_URL_GET_ACCESS_TOKEN, grant_type='client_credential', appid=APP_ID, secret=APP_SECRET))['access_token']
        _access_token['timestamp'] = now_sec()
        logger.info('access_token is: %s', _access_token['token'])
    return _access_token['token']

def get_web_auth_access_token(code):
    return json.loads(HTTP.get(WX_URL_WEB_AUTH_ACCESS_TOKEN, appid=APP_ID, secret=APP_SECRET, code=code, grant_type='authorization_code'))

def get_jsapi_sign(url):
    if _jsapi_ticket['ticket'] is None or _jsapi_ticket['timestamp'] + 7000 <= now_sec():
        access_token = get_access_token()
        _jsapi_ticket['ticket'] = json.loads(HTTP.get(WX_URL_GET_JSAPI_TICKET, access_token=access_token, type='jsapi'))['ticket']
        _jsapi_ticket['timestamp'] = now_sec()

    noncestr = randstr()
    timestamp = now_sec()
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
            'timeStamp': str(now_sec()),
            'package': 'prepay_id=' + prepay_id,
            'signType': 'MD5',
            'appId': APP_ID
            }
    sign_items['paySign'] = Signer.signstr(sign_items)
    return sign_items

def oauth2_url(redirect_uri, state=0):
    params = (
            ('appid', APP_ID),
            ('redirect_uri', redirect_uri),
            ('response_type', 'code'),
            ('scope', 'snsapi_base'),
            ('state', state)
            )
    return '{}?{}#wechat_redirect'.format(WX_URL_OAUTH2, HTTP.urlencode(params))

def make_order(order):
    result = HTTP.post(WX_URL_MAKE_ORDER, order.xml())
    return Message(result)

def create_menu(menu):
    logger.info(json.dumps(menu))
    rsp = HTTP.post(WX_URL_CREATE_MENU, json.dumps(menu, ensure_ascii=False), access_token=get_access_token())
    
    return json.loads(rsp)

def send_redpack(redpack):
    result = HTTP.ssl_post(ssl_cert_file, ssl_key_file, WX_URL_SEND_REDPACK, redpack.xml())
    return Message(result)

def get_unlimit_qrcode_ticket(arg):
    args = {
        'action_name': 'QR_LIMIT_SCENE',
        'action_info': {
            'scene': {
                'scene_id': arg
                }
            }
        }
    rsp = HTTP.post(WX_URL_CREATE_QRCODE, json.dumps(args), access_token=get_access_token())
    logger.info('get a unlimit qrcode, arg: %s, ret: %s', arg, rsp)
    rsp = json.loads(rsp)
    return rsp['ticket']

def url_to_short(url):
    data = dict(action='long2short', long_url=url)
    rsp = HTTP.post(WX_URL_SHORTURL, json.dumps(data), access_token=get_access_token())
    return json.loads(rsp)

def dump_qrcode(ticket, path):
    try:
        file, rsp = HTTP.download(HTTP.joinurl(WX_URL_GET_QRCODE, ticket=ticket), path)
    except urllib.error.HTTPError as err:
        logger.warning('get qrcode: %s from weixin failed: %s', ticket, err)
        return None
    else:
        return file

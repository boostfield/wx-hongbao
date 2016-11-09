WEB_ROOT = 'http://test.boostfield.com'
RESTFUL_ROOT = 'http://test.boostfield.com/api'
APP_ID = 'wx9fb7ef78c47f8ef2'
APP_SECRET = '4c7b0db408b0c1b4242337ade30120f1'
API_KEY = 'ac3d073861ac4035b2187549a3d4fd61'
MCH_ID = '1405637602'
MCH_NAME = 'redpack-game'
LOCAL_IP = '120.25.204.174'
REDPACK_ACTIVE_NAME = '抢红包'
REDPACK_REMARK = '抢到就是赚到'
REDPACK_WISHING = '手气不错'
LOG_FILE = 'log/redpack-game.log'
DATABASE = 'redpack-game.db'
LOG_LEVEL = 'INFO'
AGENT_SHARE_PERCENT = 0.05      # 代理提成点数
REDPACK_MAX = 20000             # 红包最大金额
LOG_FORMAT = '[%(levelname)s] %(asctime)s [%(funcName)s@%(pathname)s:%(lineno)s]- %(message)s'
SECRET_KEY = '4c7b0db408b0c1b4242337ade30120f1'
WEIXIN_SSL_CERT_FILE = '/var/www/wx-test/apiclient_cert.pem'
WEIXIN_SSL_KEY_FILE = '/var/www/wx-test/apiclient_key.pem'
RESTITUTION_STRATEGY = {
    'strategy': (
        (1, 100, 110),
        (2, 4, 50, 140),
        (0, 55, 130)
    ),
    'correction': (3, 2)
}
AUTH2_SHORT_URL = 'http://w.url.cn/s/AJdObO7'

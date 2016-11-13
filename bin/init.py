#! /usr/bin/env python3

import os
import sys
import urllib

os.system('mkdir -p ../log')
cdir = os.path.dirname(os.path.abspath(__file__))
homedir = os.path.join(cdir, '..')
sys.path.append(homedir)
import main
import weixin

main.init_db()
main.create_menu()
os.system('lessc {}/static/style.less > {}/static/style.css'.format(homedir, homedir))

# 获取主页短链接
url = weixin.url_to_short(main.weixin_oauth2_url())
print('get short url return: ' + url['errmsg'])
if url['errcode'] != 0:
    exit(1)
os.system("sed -i '/AUTH2_SHORT_URL/c\AUTH2_SHORT_URL = \"{}\"\' {}/{}".format(url['short_url'], homedir, '/conf/config.py'))

# 获取主页二维码
qrcode_url = 'http://qr.topscan.com/api.php?' + urllib.parse.urlencode({'text': url['short_url']})
if os.system("wget '{}' -O qrcode.png".format(qrcode_url)) != 0:
    print('get qrcode failed')
    exit(1)

# 生成分享二维码
from PIL import Image
qr = Image.open('qrcode.png')
bg = Image.open('../static/images/img_share.png')
bg.paste(qr, (225, 360, 525, 660))
bg.save('../static/images/entry_qrcode.png')
os.system('rm qrcode.png')
print('get app entry qrcode from: http://test.boostfield.com/images/entry_qrcode.png')
        
# 定时为代理分红
cmd = "echo '0 10 * * * {}/share_profit.py' | crontab -".format(homedir)
print('install crontab task to system:')
print(cmd)
os.system(cmd)

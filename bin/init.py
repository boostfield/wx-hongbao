#! /usr/bin/env python3

import os
import sys
import urllib

cdir = os.path.dirname(os.path.abspath(__file__))
homedir = os.path.join(cdir, '..')
sys.path.append(homedir)
import main
import weixin

main.init_db()
main.create_menu()
url = weixin.url_to_short(main.weixin_oauth2_url())
print('get short url return: ' + url['errmsg'])
if url['errcode'] != 0:
    exit(1)

print('download qrcode from: ' + 'http://qr.topscan.com/api.php?' + urllib.parse.urlencode({'text': url['short_url']}))
        
os.system("sed -i '/AUTH2_SHORT_URL/c\AUTH2_SHORT_URL = \"{}\"\' {}/{}".format(url['short_url'], homedir, '/conf/config.py'))

# 定时为代理分红
cmd = "echo '0 10 * * * {}/share_profit.py' | crontab -".format(homedir)
print('install crontab task to system:')
print(cmd)
os.system(cmd)

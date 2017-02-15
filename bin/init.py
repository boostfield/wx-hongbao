#! /usr/bin/env python3

import os
import sys
import urllib

os.system('mkdir -p ../log')
os.system('rm ../log/*')
os.system('mkdir -p ../static/qrcode')
cdir = os.path.dirname(os.path.abspath(__file__))
homedir = os.path.join(cdir, '..')
sys.path.append(homedir)
import main
import weixin
from common import save_file, make_qrcode

# 初始化数据库
script_file = 'script.sql'
script = "\
create database if not exists {0};\
create user '{1}'@'{2}' identified by '{3}';\
grant all on {0}.* to '{1}'@'{2}';".format(
    main.app.config['DB_SCHEMA'], main.app.config['DB_USER'], main.app.config['DB_HOST'], main.app.config['DB_PASS'])
save_file(script_file, script)
print("entry mysql root user password:")
os.system('mysql -u root -f -p < %s' % script_file)
main.init_db()

os.system('lessc {}/static/style.less > {}/static/style.css'.format(homedir, homedir))

# 获取主页短链接
url = weixin.url_to_short(main.weixin_oauth2_url())
print('get short url return: ' + url['errmsg'])
if url['errcode'] != 0:
    exit(1)
os.system("sed -i '/AUTH2_SHORT_URL/c\AUTH2_SHORT_URL = \"{}\"\' {}/{}".format(url['short_url'], homedir, '/conf/config.py'))

main.create_menu()

# 生成分享二维码
make_qrcode(url['short_url'], 'qrcode.png')
from PIL import Image
qr = Image.open('qrcode.png')
bg = Image.open('../static/images/img_share_picture.png')
qr = qr.convert('RGB')
bg = bg.convert('RGB')
qr_w, qr_h = qr.size
bg_w, bg_h = bg.size
qr_x = (bg_w - qr_w) // 2
qr_y = bg_h // 3
bg.paste(qr, (qr_x, qr_y, qr_x + qr_w, qr_y + qr_h))
bg = bg.convert('P')
bg.save('../static/images/entry_qrcode.png')
os.system('rm qrcode.png')
print('get app entry qrcode from: http://test.boostfield.com/images/entry_qrcode.png')

# 定时为代理分红
cmd = "echo '0 10 * * * {}/share_profit.py' | crontab -".format(homedir)
print('install crontab task to system:')
print(cmd)
os.system(cmd)

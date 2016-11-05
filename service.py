__TABLE_COLUMNS = {
    'user': ('id', 'openid', 'register_time'),
    'login': ('id', 'openid', 'timestamp'),
    'user_pay': ('id', 'openid', 'money', 'trade_no', 'ip', 'state', 'prepay_id', 'error_msg', 'timestamp')
    }

def find_user(openid):
    args = (openid,)
    c = db.execute('SELECT * FROM user WHERE openid=?', args)
    row = c.fetchone()
    if row is None:
        return None
    return dict(zip(__TABLE_COLUMNS['user'], row))

def create_user(user):
    args = (user['openid'], )
    db.execute('INSERT INTO user(openid) VALUES(?)', args)
    db.commit()

def record_login(openid):
    args = (openid, )
    db.execute('INSERT INTO login(openid) VALUES(?)', args)
    db.commit()

def save_user_pay(pay):
    args = (pay['openid'], pay['money'], pay['trade_no'], pay['ip'], pay['state'],
            pay.get('prepay_id'), pay.get('error_msg'))
    db.execute('INSERT INTO user_pay(openid, money, trade_no, ip, state, prepay_id, error_msg) VALUES(?, ?, ?, ?, ?, ?, ?)', args)
    db.commit()

def find_user_pays(openid, state=None):
    c = None
    if state is None:
        args = (openid, )
        c = db.execute('SELECT * FROM user_pay WHERE openid=? ORDER BY timestamp DESC', args)
    else:
        args = (openid, state)
        c = db.execute("SELECT * FROM user_pay WHERE openid=? AND state='?' ORDER BY timestamp DESC", args)

    pays = c.fetchall()
    return list(map(lambda pay: dict(zip((__TABLE_COLUMNS['user_pay']), pay)), pays))

def find_user_pay(trade_no):
    args = (trade_no, )
    c = db.execute('SELECT * FROM user_pay WHERE trade_no=?', args)
    row = c.fetchone()
    if row:
        row = dict(zip(__TABLE_COLUMNS['user_pay'], row))
    return row

def update_user_pay(pay):
    args = (pay['openid'], pay['money'], pay['trade_no'], pay['ip'], pay['state'], pay.get('prepay_id'),
            pay.get('error_msg'), pay['id'])
    db.execute('UPDATE user_pay SET openid=?, money=?, trade_no=?, ip=?, state=?, prepay_id=?, error_msg=? WHERE id=?', args)
    db.commit()

def update_sys_pay(pay):
    args = (pay['openid'], pay['money'], pay['user_pay_id'], pay['state'], pay.get('wx_billno'),
            pay.get('error_msg'), pay['billno'])
    db.execute('UPDATE sys_pay SET openid=?, money=?, user_pay_id=?, state=?, wx_billno=?, error_msg=? WHERE billno=?', args)

def save_sys_pay(pay):
    args = (pay['openid'], pay['money'], pay['billno'], pay['user_pay_id'],
            pay['state'], pay.get('wx_billno'), pay.get('error_msg'))
    db.execute('INSERT INTO sys_pay(openid, money, billno, user_pay_id, state, wx_billno, error_msg) VALUES(?, ?, ?, ?, ?, ?, ?)', args)
    db.commit()

# 查找用户历史收入与支出
def find_user_bill(openid):
    args = (openid, )
    c = db.execute('SELECT up.money, sp.money FROM user_pay AS up LEFT JOIN sys_pay AS sp ON up.id=sp.user_pay_id WHERE up.openid=?', args)
    return c.fetchall()

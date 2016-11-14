__TABLE_COLUMNS = {
    'user': ('id', 'openid', 'agent', 'share_qrcode', 'register_time'),
    'login': ('id', 'openid', 'timestamp'),
    'user_pay': ('id', 'openid', 'money', 'trade_no', 'ip', 'state', 'prepay_id', 'error_msg', 'timestamp'),
    'sys_pay': ('id', 'openid', 'money', 'billno', 'user_pay_id', 'state', 'type', 'wx_billno', 'error_msg', 'timestamp'),
    'event': ('id', 'openid', 'type', 'info', 'timestamp'),
    }

# row to dict
def _inflate(tablename, row):
    return dict(zip(__TABLE_COLUMNS[tablename], row))

def find_user(openid):
    args = (openid,)
    c = db.execute('SELECT * FROM user WHERE openid=?', args)
    row = c.fetchone()
    if row is None:
        return None
    return _inflate('user', row)

def update_user(user):
    args = (user['openid'], user['agent'], user['share_qrcode'], user['id'])
    db.execute('UPDATE user SET openid=?, agent=?, share_qrcode=? WHERE id=?', args)
    db.commit()

def create_user(openid, agent=None):
    args = (openid, agent)
    db.execute('INSERT INTO user(openid, agent) VALUES(?, ?)', args)
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
    return list(map(lambda pay: _inflate('user_pay', pay), pays))

def find_user_pay(trade_no):
    args = (trade_no, )
    c = db.execute('SELECT * FROM user_pay WHERE trade_no=?', args)
    row = c.fetchone()
    if row:
        row = _inflate('user_pay', row)
    return row

def update_user_pay(pay):
    args = (pay['openid'], pay['money'], pay['trade_no'], pay['ip'], pay['state'], pay.get('prepay_id'),
            pay.get('error_msg'), pay['id'])
    db.execute('UPDATE user_pay SET openid=?, money=?, trade_no=?, ip=?, state=?, prepay_id=?, error_msg=? WHERE id=?', args)
    db.commit()

def update_sys_pay(pay):
    args = (pay['openid'], pay['money'], pay.get('user_pay_id'), pay['state'], pay['type'], pay.get('wx_billno'),
            pay.get('error_msg'), pay['billno'])
    db.execute('UPDATE sys_pay SET openid=?, money=?, user_pay_id=?, state=?, type=?, wx_billno=?, error_msg=? WHERE billno=?', args)

def save_sys_pay(pay):
    args = (pay['openid'], pay['money'], pay['billno'], pay.get('user_pay_id'),
            pay['state'], pay['type'], pay.get('wx_billno'), pay.get('error_msg'))
    db.execute('INSERT INTO sys_pay(openid, money, billno, user_pay_id, state, type, wx_billno, error_msg) VALUES(?, ?, ?, ?, ?, ?, ?, ?)', args)
    db.commit()

def find_sys_pay(billno):
    args = (billno, )
    c = db.execute('SELECT * FROM sys_pay WHERE billno=?', args)
    row = c.fetchone()
    if row:
        row = _inflate('sys_pay', row)
    return row
    
# 查找用户历史收入与支出
def find_user_bill(openid):
    args = (openid, )
    c = db.execute('SELECT up.money, sp.money FROM user_pay AS up LEFT JOIN sys_pay AS sp ON up.id=sp.user_pay_id WHERE up.openid=?', args)
    return c.fetchall()

def save_event(openid, event, info=None):
    args = (openid, event, info)
    db.execute('INSERT INTO event(openid, type, info) VALUES(?, ?, ?)', args)
    db.commit()

def find_events(openid, event):
    args = (openid, event)
    c = db.execute('SELECT * FROM event WHERE openid=? AND type=? ORDER BY timestamp DESC', args)
    return list(map(lambda event: _inflate('event', event), c.fetchall()))

def find_unshared_profit():
    c = db.execute("SELECT u.openid, u.agent, a.openid, p.money, p.id FROM user AS u JOIN user_pay AS p ON u.openid=p.openid JOIN user AS a ON u.agent=a.id WHERE p.state='SUCCESS' AND NOT EXISTS (SELECT * FROM share WHERE user_pay_id=p.id)")
    keys = ('openid', 'agent', 'agent_openid', 'money', 'user_pay_id')
    return list(map(lambda row: dict(zip(keys, row)), c.fetchall()))
    
def save_share(uid, sid, money):
    args = (uid, sid, money)
    db.execute('insert into share(user_pay_id, sys_pay_id, money) values(?, ?, ?)', args)
    db.commit()

def find_agent_bill(openid, offset=0, limit=50):
    args = (openid, limit, offset)
    c = db.execute(
        "SELECT u.openid, up.id, up.money, up.timestamp, s.money, s.timestamp, s.sys_pay_id \
        FROM user AS agent \
        JOIN user AS u \
        ON u.agent=agent.id \
        JOIN user_pay AS up \
        ON up.openid=u.openid \
        LEFT JOIN share AS s \
        ON up.id=s.user_pay_id \
        WHERE agent.openid=? \
        AND up.state='SUCCESS' \
        ORDER BY up.id DESC \
        LIMIT ? \
        OFFSET ?", args)
    keys = ('openid', 'user_pay_id', 'money', 'timestamp', 'shared_money', 'shared_timestamp', 'sys_pay_id')
    return list(map(lambda row: dict(zip(keys, row)), c.fetchall()))

def find_follower_num(openid):
    args = (openid, )
    c = db.execute('SELECT count(*) FROM user AS a JOIN user AS f ON f.agent=a.id WHERE a.openid=?', args)
    return c.fetchone()[0]

def find_agent_bill_num(openid):
    args = (openid, )
    c = db.execute(
        "SELECT count(*) \
        FROM user AS agent \
        JOIN user AS u \
        ON u.agent=agent.id \
        JOIN user_pay AS up \
        ON up.openid=u.openid \
        LEFT JOIN share AS s \
        ON up.id=s.user_pay_id \
        WHERE agent.openid=? \
        AND up.state='SUCCESS'", args)
    return c.fetchone()[0]

def find_agent_shared_bill_num(openid):
    args = (openid, )
    c = db.execute(
        "SELECT count(*) \
        FROM user AS agent \
        JOIN user AS u \
        ON u.agent=agent.id \
        JOIN user_pay AS up \
        ON up.openid=u.openid \
        JOIN share AS s \
        ON up.id=s.user_pay_id \
        WHERE agent.openid=? \
        AND up.state='SUCCESS'", args)
    return c.fetchone()[0]

def find_user_last_income(openid):
    args = (openid, )
    c = db.execute("SELECT money, timestamp FROM sys_pay WHERE openid=? AND state='SUCCESS' AND type='RETURN' ORDER BY timestamp DESC LIMIT 1", args)
    return c.fetchone()

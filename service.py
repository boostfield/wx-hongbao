# -*- encoding: utf-8 -*-

def find_user(openid):
    args = (openid,)
    c = db.execute('SELECT * FROM user WHERE openid=?', args)
    row = c.fetchone()
    if row is None:
        return None
    return dict(zip(
        ('id', 'openid', 'register_time'), row
        ))

def create_user(user):
    args = (user['openid'], )
    db.execute('INSERT INTO user(openid) VALUES(?)', args)
    db.commit()

def record_login(openid):
    args = (openid, )
    db.execute('INSERT INTO login(openid) VALUES(?)', args)
    db.commit()

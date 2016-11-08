DROP TABLE IF EXISTS user;
CREATE TABLE user(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
	agent INTEGER NULL,
    register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY(agent) REFERENCES user(id)
);

DROP TABLE IF EXISTS login;
CREATE TABLE login(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

DROP TABLE IF EXISTS user_pay;
CREATE TABLE user_pay(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
    money INT NOT NULL,
    trade_no TEXT NOT NULL,
    ip TEXT NOT NULL,
    state TEXT NOT NULL,
	prepay_id TEXT,
    error_msg TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);


DROP TABLE IF EXISTS sys_pay;
CREATE TABLE sys_pay(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
	money INT NOT NULL,
	billno TEXT NOT NULL,
	user_pay_id INTEGER NOT NULL,
	state TEXT NOT NULL,
	wx_billno TEXT,
	error_msg TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
	FOREIGN KEY(user_pay_id) REFERENCES user_pay(id)
);

DROP TABLE IF EXISTS event;
CREATE TABLE EVENT(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
	type TEXT NOT NULL,
	info TEXT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

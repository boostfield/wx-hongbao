DROP TABLE IF EXISTS user;
CREATE TABLE user(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
    register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

DROP TABLE IF EXISTS login;
CREATE TABLE login(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL,
    register_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);


DROP TABLE IF EXISTS user_pay;
CREATE TABLE user_pay(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL
);


DROP TABLE IF EXISTS sys_pay;
CREATE TABLE sys_pay(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    openid TEXT NOT NULL
);

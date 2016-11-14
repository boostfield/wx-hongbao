import json
import logging
from logging import StreamHandler, Formatter
from random import choice, randint
from itertools import groupby
from datetime import datetime
from pathlib import Path
from common import now, now_sec

def _default_logger():
    logger = logging.Logger(__name__)
    handler = StreamHandler()
    handler.setFormatter(Formatter('[%(levelname)s] %(asctime)s [%(process)d:%(thread)d] [%(funcName)s@%(pathname)s:%(lineno)s]- %(message)s'))
    logger.addHandler(handler)
    return logger

logger = _default_logger()

STRATEGY_FILES_HOME = './strategies'
STRATEGY_FILES_SUFFIX = '.json'
STRATEGY_REFREASH_INTERVAL = 120 # 重新加载策略的间隔时间（分钟）
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'

CONFIG_DEFAULT_VALUE = {
    "enable": True,
    "priority": 2,
    "goal": "gain",
    "gain_rate": 5,
    "loss_limit": 3000,
    "min_redpack": 100,
    "max_redpack": 20000,
    "miss_limit": 5,
    "win_limit": 2,
    "custom": {
        "detail":[],
        "default": []
    }
}

def get_strategy():
    return StrategyManager.get_strategy()

class StrategyManager:
    strategy_manager = None
    
    @classmethod
    def get_manager(cls):
        if not cls.strategy_manager:
            cls.strategy_manager = StrategyManager()
        return cls.strategy_manager

    def __init__(self):
        self._load_strategies()
        self._current_strategy = None
        
    def get_strategy(self):
        stg = self._current_strategy
        if stg is None:
            self._current_strategy = self._find_strategy()
            self._current_strategy.start()
            logger.info("new strategy: %s started", self._current_strategy.name)
        elif not stg.is_available():
            stg.stop()
            logger.info("current strategy: %s is no more available, it will be replaced", stg.name)
            logger.info("strategy %s summary: start at: %s, stop at: %s, duration: %d minutes, serve %d users, total income: %d￥, total pay: %d￥, profit: %d￥",
                        stg.name, stg.start_at(), stg.stop_at(), stg.duration(), stg.user_num, stg.total_income, stg.total_pay, stg.net_profit())
            self._current_strategy = self._find_strategy()
            self._current_strategy.start()
            logger.info("new strategy: %s started", self._current_strategy.name)
        return self._current_strategy            

    def add(self, stg):
        self.strategies.append(stg)

    def _load_strategies(self):
        logger.info('load strategies')
        self.strategy_files = self._find_strategy_files()
        self.strategies = [Strategy(file) for file in self.strategy_files]
        self._load_strategies_time = now_sec()
            
    def _find_strategy_files(self):
        path = Path(STRATEGY_FILES_HOME)
        return [str(p) for p in path.iterdir() if p.is_file() and p.suffix == STRATEGY_FILES_SUFFIX]
            
    def _strategies_old(self):
        return self._load_strategies_time + STRATEGY_REFREASH_INTERVAL * 60 <= now_sec()
    
    def _find_strategy(self):
        if self._strategies_old():
            self._load_strategies()
            
        available_strategies = [s for s in self.strategies if s.is_available()]

        available_strategies.sort(key=lambda s: s.config['priority'], reverse=True)
        for k, g, in groupby(available_strategies, lambda x: x.config['priority']):
            same_prioriby_strategies = list(g)
            if len(same_prioriby_strategies) > 0:
                return choice(same_prioriby_strategies)

        return Strategy.default()


class Strategy:
    @classmethod
    def default(cls):
        return Strategy(CONFIG_DEFAULT_VALUE)
    
    def __init__(self, cfg):
        if isinstance(cfg, dict):
            self.config = cfg
            self.name = None
        elif isinstance(cfg, str):
            with open(cfg) as f:
                self.config = json.loads(f.read())
            self.name = self._get_filename(cfg)

        self._fill_config_default()
        self._check_config()

        self.name = self.config.get('name') or self.name
        self.start_time = None
        self.stop_time = None
        self.started = False
        self.total_income = 0
        self.total_pay = 0
        self.user_num = 0
        self._users_history = {}

    def start_at(self):
        if not self.start_time:
            return None
        
        return self._fmt_timestamp(self.start_time)

    def stop_at(self):
        if not self.stop_time:
            return None
        
        return self._fmt_timestamp(self.stop_time)

    def duration(self):
        if not self.start_time:
            return 0

        if not self.stop_time:
            return (now_sec() - self.start_time) // 60
        
        return (self.stop_time - self.start_time) // 60
    
    def is_available(self):
        _now = now_sec()
        if _now >= self._disable_time():
            return False

        if self.started:
            if 'duration' in self.config:
                return self.start_time + self.config['duration'] * 60 > _now
        
        if self.config['enable'] and _now > self._available_time():
            return True
        return False
    
    def start(self):
        self.start_time = now_sec()
        self.stop_time = None
        self.total_income = 0
        self.total_pay = 0
        self.user_num = 0
        self.started = True
        self._users_history = {}

    def stop(self):
        self.stop_time = now_sec()
        self.started = False

    def pay(self, openid, income):
        """ 根据收入决定中奖金额 """
        history = self._find_history(openid)
        history.play_times += 1
        self.total_income += income
        
        _range = self._find_pay_range(history.index, history.play_times)
        pay = self._rand_pay(income, _range) if _range else self._global_pay(openid, income)
        self.total_pay += pay
        history.append(income, pay)

        return pay

    def net_profit(self):
        return self.total_income - self.total_pay

    ###################
    # private methods #
    ###################
    def _fmt_timestamp(self, time):
        return datetime.fromtimestamp(time).strftime(TIMESTAMP_FMT)
    
    def _check_config(self):
        # todo
        pass

    def _available_time(self):
        if 'available_time' not in self.config:
            return int(datetime.min.timestamp())
        return int(datetime.strptime(self.config['available_time'], TIMESTAMP_FMT).timestamp())
    
    def _disable_time(self):
        if 'disable_time' not in self.config:
            return int(datetime.max.timestamp())
        return int(datetime.strptime(self.config['disable_time'], TIMESTAMP_FMT).timestamp())

    def _fill_config_default(self):
        for k, v in CONFIG_DEFAULT_VALUE.items():
            self.config.setdefault(k, v)
        self.config['custom'].setdefault('default', CONFIG_DEFAULT_VALUE['custom']['default'])
        self.config['custom'].setdefault('detail', CONFIG_DEFAULT_VALUE['custom']['detail'])
    
    def _find_history(self, openid):
        history = self._users_history.get(openid)
        if not history:
            history = UserHistory(openid)
            history.index = self.user_num
            self.user_num += 1
            self._users_history[openid] = history
        return history
        
    def _find_pay_range(self, index, times):
        """ 查找中奖区间 """
        range_table = self.config['custom']['detail']
        range_list = range_table[index] if index < len(range_table) else self.config['custom']['default']
        return None if times > len(range_list) else range_list[times - 1]
            
    def _rand_pay(self, income, _range):
        """ 在区间中随机选取中间金额 """
        pay = randint(_range[0], _range[1]) * income // 100
        pay = max(self.config['min_redpack'], pay)
        pay = min(pay, self.config['max_redpack'])
        return pay

    def _rand_money(self, income, low, high=None):
        """ 在 low-high 直间随机生成一个返现金额，low/high 表示倍率，若不指定high则取红包上限 """
        _low = max(min(int(income * low), self.config['max_redpack']), self.config['min_redpack'])
        if high is None: _high = self.config['max_redpack']
        else: _high = max(min(int(income * high), self.config['max_redpack']), self.config['min_redpack'])
        return randint(_low, _high)
            
    def _get_filename(self, path):
        p = Path(path)
        return p.name[:-len(p.suffix)]

    def _global_pay(self, openid, income):
        """ 统筹全局决定返现金额 """
        history = self._find_history(openid)
        must_win = history.continue_miss_times() >= self.config['miss_limit']
        must_miss = history.continue_win_times() >= self.config['win_limit']
        
        if self.config['goal'] == 'gain':
            expect_profit = self.total_pay * (100 + self.config['gain_rate']) // 100
            exceed_profit = self.net_profit() - expect_profit
            if exceed_profit >= 0: # 已超出盈利目标, 尽最大可能让利
                return self._rand_money(income, 5)
            else:
                if must_win:    # 未达盈利目标但用户连输，仍返利
                    return self._rand_money(income, 1.5, 4)
                elif must_miss: # 
                    return self._rand_money(income, 0.5, 0.8)
                else:
                    return self._rand_money(income, 0.5, 1.2)
        else:                   # 目标是让利
            total_loss = -self.net_profit()
            may_loss = self.config['loss_limit'] - total_loss
            if may_loss > 0:    # 有利可让
                return min(may_loss, self._rand_money(income, 5))
            else:
                if must_win:    # 已无利可让但用户连输，仍返利
                    return self._rand_money(income, 1.5, 4)
                elif must_miss:
                    return self._rand_money(income, 0.5, 0.8)
                else:
                    return self._rand_money(income, 0.5, 0.8)
        
class UserHistory:
    def __init__(self, openid):
        self.openid = openid
        self.index = 0          # 在所有用户中加入游戏的次序
        self.play_times = 0     # 抽奖次数
        self.history = []

    def append(self, income, pay):
        self.history.append((income, pay, now_sec()))

    def continue_win_times(self):
        result = 0
        for (income, pay, time) in self.history[-1::-1]:
            if pay >= income:
                result += 1
            else:
                break;
        return result

    def continue_miss_times(self):
        result = 0
        for (income, pay, time) in self.history[-1::-1]:
            if pay < income:
                result += 1
            else:
                break;
        return result

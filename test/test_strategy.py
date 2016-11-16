#! /usr/bin/env python3

import base
import unittest
import json
import main
import time
import strategy
from strategy import Strategy
from pathlib import Path
from base import anything
from common import now_sec, fmt_timestamp

FAIL = 'FAIL'
SUCCESS = 'SUCCESS'
OPENID = 'oenW2wz47W1RisML5QijHzwRz34M'
TIMESTAMP_FMT = '%Y-%m-%d %H:%M:%S'

class TC(unittest.TestCase):

    def setUp(self):
        Path(strategy.STRATEGY_FILES_HOME).mkdir()
        
    def tearDown(self):
        strategy.StrategyManager.get_manager().clean()
        Path(strategy.STRATEGY_FILES_HOME).rmdir()
        
    def test_strategy_enable(self):
        config = dict(enable=False)
        stg = strategy.Strategy(config)
        self.assertFalse(stg.is_available())

        config['enable'] = True
        stg = strategy.Strategy(config)
        self.assertTrue(stg.is_available())

        config['available_time'] = fmt_timestamp(now_sec() + 2, TIMESTAMP_FMT)
        config['disable_time'] = fmt_timestamp(now_sec() + 4, TIMESTAMP_FMT)
        stg = strategy.Strategy(config)
        self.assertFalse(stg.is_available())

        time.sleep(3)
        self.assertTrue(stg.is_available())
        time.sleep(2)
        self.assertFalse(stg.is_available())

    def test_min_max_redpack(self):
        config = { 'custom': { 'detail': [[
            [300, 400], [0, 1], [90, 110]
        ]]}}
        stg = strategy.Strategy(config)
        pay = stg.pay('user0', 10000)
        self.assertEqual(20000, pay)

        pay = stg.pay('user0', 100)
        self.assertEqual(100, pay)

        pay = stg.pay('user0', 1000)
        self.assertIn(pay, range(900, 1101))
        
    def test_priority(self):
        manager = strategy.StrategyManager.get_manager()
        config = dict(priority=3, name='stg0')
        stg0 = Strategy(config)
        manager.add(stg0)

        config = dict(priority=3, name='stg1')
        stg1 = Strategy(config)
        manager.add(stg1)

        config = dict(name='stg2')
        stg2 = Strategy(config)
        manager.add(stg2)

        config = dict(priority=1, name='stg3')
        stg3 = Strategy(config)
        manager.add(stg3)

        stg = manager.get_strategy()
        self.assertIn(stg.name, ['stg0', 'stg1'])

        stg0.config['enable'] = False
        stg = manager.get_strategy()
        self.assertEqual('stg1', stg.name)

        stg1.config['enable'] = False
        stg = manager.get_strategy()
        self.assertEqual('stg2', stg.name)
        
        stg2.config['enable'] = False
        stg = manager.get_strategy()
        self.assertEqual('stg3', stg.name)
        
    def test_use_default(self):
        config = { 
            'min_redpack': 10,
            'custom': {
                'detail': [
                    [[50, 120]],
                    [[50, 120]],
                ],
                'default': [[90, 92], [100, 103]],
            }}

        stg = strategy.Strategy(config)
        stg.pay('usera', 10000)
        stg.pay('userb', 10000)
        for i in range(100):
            user = "user{}".format(i)
            self.assertIn(stg.pay(user, 100), range(90, 93)) 
            self.assertIn(stg.pay(user, 100), range(100, 104)) 

    def test_all_strategy_disabled(self):
        """ 使用默认策略 """
        config = {
            "name": 'strategy1',
            "disable_time": fmt_timestamp(now_sec() + 3, TIMESTAMP_FMT)
            }
        
        stg = Strategy(config)
        strategy.StrategyManager.get_manager().add(stg)
        self.assertEqual('strategy1', strategy.get_strategy().name)
        time.sleep(4)
        self.assertEqual('default', strategy.get_strategy().name)
        
    def test_reload_strategy(self):

        pass
    
    def test_summary(self):
        stg = strategy.Strategy({
            'goal': 'loss',
            'loss_limit': 3000
        })

        total = 0
        times = 10000
        for i in range(times):
            pay0 = stg.pay('user0', 1000)
            pay1 = stg.pay('user1', 1000)
            pay2 = stg.pay('user2', 1000)

            print(pay0, pay1, pay2)
            total += (pay0 + pay1 + pay2)

        # self.assertEqual(times * 3 * 1000, stg.total_income)
        # self.assertEqual(total, stg.total_pay)
        # self.assertEqual(3, stg.user_num)
        self.assertEqual(3 * times, stg.pay_num)
        # self.assertEqual(stg.total_income - total, stg.net_profit())
        # print("net profit: %d" % stg.net_profit())
        print("profit rate: %f" % stg.profit_rate())
        print(strategy.count)
    
if __name__ == '__main__':
    unittest.main()

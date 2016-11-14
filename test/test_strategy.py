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
        self.assertIn(900, 1100)
        
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

    def test_summary(self):
        stg = strategy.Strategy({})

        print(stg.pay('user', 10000))
        print(stg.pay('user', 10000))
        print(stg.pay('user', 10000))
        print(stg.pay('user', 10000))
        print(stg.pay('user', 10000))
        print(stg.pay('user', 10000))
        
if __name__ == '__main__':
    unittest.main()

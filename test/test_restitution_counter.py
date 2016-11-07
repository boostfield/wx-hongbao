#! /usr/bin/env python3

import base
import unittest
import restitution_counter as rc

class TestCase(unittest.TestCase):
    def setUp(self):
        pass

    def test_no_data(self):
        history = []
        with self.assertRaises(ValueError):
            rc.count(None, history)

    def test_no_history(self):
        strategy = {
            'strategy': (
                (1, 95, 105),
            )
        }
        history = [(100, None)]
        pay = rc.count(strategy, history)
        self.assertIn(pay, range(90, 111))

    def test_func(self):
        strategy = {
            'strategy': (
                (1, 95, 105),
                (2, 80, 110),
                (3, 5, 80, 110),
                (6, 10, 20, 30)
            )
        }
        history = [(100, 100), (100, 100), (100, 100), (100, 100), (100, 100), (100, None)]
        pay = rc.count(strategy, history)
        self.assertIn(pay, range(20, 31))

    def test_strategy_not_found(self):
        strategy = {
            'strategy': (
                (1, 95, 105),
                (2, 80, 110),
                (3, 5, 80, 110)
            )
        }
        history = [(100, 100), (100, 100), (100, 100), (100, 100), (100, 100), (100, None)]
        pay = rc.count(strategy, history)
        self.assertIn(pay, range(70, 121))

    def test_correction(self):
        strategy = {
            'strategy': (
                (1, 95, 105),
                (2, 80, 110),
                (3, 5, 80, 95),
                (6, 10, 110, 140)
            ),
            'correction': (3, 2)
        }
        history = [(100, 100), (100, 100), (100, 110), (100, 110), (100, 110), (100, None)]
        pay = rc.count(strategy, history)
        self.assertIn(pay, range(50, 101))

        history = [(100, 100), (100, 100), (100, 90), (100, 90), (100, None)]
        pay = rc.count(strategy, history)
        self.assertIn(pay, range(100, 151))
        
if __name__ == '__main__':
    unittest.main()

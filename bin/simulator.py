#! /usr/bin/env python3

import os
import sys
cdir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(cdir, '..'))
from main import app
import restitution_counter as rc

strategy = app.config['RESTITUTION_STRATEGY']
history = []

def simulate_user(times):
    total = 0
    for i in range(0, times):
        history.append([1000, None])
        income = rc.count(strategy, history)
        history[-1][1] = income
        total += income

    return (1000 * times) - total

def simulate(user_num, times):
    total = 0
    for i in range(0, user_num):
        total += simulate_user(times)
    return total

if len(sys.argv) >= 3:
    user_num = int(sys.argv[1])
    times = int(sys.argv[2])
    print(simulate(user_num, times))
else:
    print('用户数量\t交易次数\t预期收益')
    scenes = (
        (1, 1),
        (1, 5),
        (1, 10),
        (1, 20),
        (100, 1),
        (100, 5),
        (100, 10),
        (100, 20),
        (500, 1),
        (500, 2),
        (500, 5),
        (1000, 1),
        (1000, 2),
        (1000, 4),
        )
    for s in scenes:
        income = simulate(s[0], s[1]) / 100
        print('{}\t\t{}\t\t{}'.format(s[0], s[1], income))

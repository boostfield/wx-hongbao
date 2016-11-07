import random

def _count_net_income(history):
    return [income - expend if income else -expend for expend, income in history]
    
def _find_restitution_range(strategy, trade_time):
    for s in strategy:
        if len(s) < 3:
            raise 'strategy error: %s'.format(s)
        if s[0] == 0:
            return s[1:3]
        if len(s) == 3:
            if s[0] == trade_time:
                return s[1:3]
            continue
        if trade_time >= s[0] and trade_time <= s[1]:
            return s[2:4]

    # return default range
    return (70, 120)

def _continue_lose_num(net_income):
    result = 0
    for i in net_income[-2::-1]:
        if i < 0:
            result += 1
        else:
            break
            
    return result

def _continue_win_num(net_income):
    result = 0
    for i in net_income[-2::-1]:
        if i >= 0:
            result += 1
        else:
            break
        
    return result

def count(strategy, history):
    net_income = _count_net_income(history)
    trade_time = len(history)
    if trade_time == 0:
        raise ValueError('no pay, no gain')

    low, high = _find_restitution_range(strategy['strategy'], trade_time)
    last_expend = history[-1][0]

    # 连续盈利或亏损时人为干预随机结果
    if 'correction' in strategy:
        continue_win = _continue_win_num(net_income)
        continue_lose = _continue_lose_num(net_income)
        if continue_win >= strategy['correction'][0]: # 连续盈利次数超过阈值
            high = min(high, 100)
            if low >= high:
                low = high // 2

        if continue_lose >= strategy['correction'][1]:
            low = max(low, 100)
            if low >= high:
                high = low + low // 2

    return random.randint(low, high) * last_expend // 100
    

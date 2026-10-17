"""一进二打板回测（同花顺日 K，不复权）。
买入：首板次日以涨停价买入（摸板即成交，含炸板；剔除一字板）。
卖出规则：A 次日开盘卖；B 次日收盘卖；C 次日 -4% 止损（开盘已低于则按开盘），否则收盘卖；
          D 同 C，但次日收盘涨停则持有到第三天开盘卖。
用法：python3 stock-research/backtest_yijiner.py"""
import json, os, re, time, math
import fetch_hotspots as fh
from entry_stats import days, LU, OP, height, hm, MAIN
from pool_cache import R

KDIR = R + '/kline'
os.makedirs(KDIR, exist_ok=True)


def kline(code):
    f = f'{KDIR}/{code}.json'
    if os.path.exists(f):
        return json.load(open(f))
    txt = fh.http_get(f'https://d.10jqka.com.cn/v6/line/hs_{code}/00/last.js',
                      {'Referer': 'https://stockpage.10jqka.com.cn/'})
    data = json.loads(txt[txt.index('(') + 1: txt.rindex(')')])['data']
    k = {}
    for row in data.split(';'):
        p = row.split(',')
        k[f'{p[0][:4]}-{p[0][4:6]}-{p[0][6:]}'] = [float(x) for x in p[1:5]]  # open high low close
    json.dump(k, open(f, 'w'))
    time.sleep(0.2)
    return k


def lim(prev):
    return math.floor(prev * 1.1 * 100 + 0.5) / 100


def pnl(buy, sell):
    sh = int(5000 / buy / 100) * 100 or 100
    a, b = buy * sh, sell * sh
    fee = max(5, a * 0.00025) + max(5, b * 0.00025) + b * 0.0005 + (a + b) * 0.00001
    return (b - a - fee) / a


trades = []
for i in range(1, len(days) - 2):
    p, d = days[i - 1], days[i]
    d1, d2 = days[i + 1], days[i + 2]
    for c, r in LU[p].items():
        if c[:3] not in MAIN: continue
        h, cons = height(r['high_days'])
        if h != 1 or not cons: continue
        x = LU[d].get(c) or OP[d].get(c)
        if not x or (c in LU[d] and x['limit_up_type'] == '一字板'): continue
        try:
            k = kline(c)
        except Exception as e:
            print('skip', c, e); continue
        if not all(t in k for t in (p, d, d1)): continue
        B = lim(k[p][3])
        o1, h1, l1, c1 = k[d1]
        stop = B * 0.96
        sc = o1 if o1 <= stop else (stop if l1 <= stop else c1)
        sd = sc
        if sc == c1 and c1 >= lim(k[d][3]) - 0.001 and d2 in k:
            sd = k[d2][0]
        trades.append(dict(code=c, name=r['name'], day=d, t=hm(x['first_limit_up_time']), sealed=c in LU[d],
                           A=pnl(B, o1), B=pnl(B, c1), C=pnl(B, sc), D=pnl(B, sd)))

json.dump(trades, open(R + '/backtest_trades.json', 'w'), ensure_ascii=False, indent=0)


def report(rows, title):
    print(f'\n### {title}（{len(rows)} 笔）\n| 卖出规则 | 胜率 | 平均盈利 | 平均亏损 | 盈亏比 | 单笔期望 | 最大单笔亏损 |\n|---|---|---|---|---|---|---|')
    for key, nm in (('A', '次日开盘卖'), ('B', '次日收盘卖'), ('C', '次日-4%止损/否则收盘'), ('D', 'C+次日涨停拿到第三天开盘')):
        v = [t[key] for t in rows]
        if not v: continue
        w = [x for x in v if x > 0]; l = [x for x in v if x <= 0]
        aw = sum(w) / len(w) if w else 0; al = sum(l) / len(l) if l else 0
        print(f'| {nm} | {len(w)/len(v):.0%} | {aw:+.2%} | {al:+.2%} | {abs(aw/al) if al else 0:.2f} | {sum(v)/len(v):+.2%} | {min(v):+.1%} |')


report(trades, '全部摸板（剔除一字）')
report([t for t in trades if t['t'] and '09:35' <= t['t'] < '10:30'], '9:35–10:30 首次触板')
report([t for t in trades if t['t'] and t['t'] < '09:35'], '9:35 之前首次触板')
report([t for t in trades if t['t'] and t['t'] >= '10:30'], '10:30 之后首次触板')


# ---- 叠加选股规则（首板当日）：终封 ≤10:30、流通 ≥30亿、换手 ≤25%、真首板（前 20 个交易日无涨停）
def rule_ok(t):
    i = days.index(t['day']); p = days[i - 1]
    r = LU[p][t['code']]
    if not r['last_limit_up_time'] or hm(r['last_limit_up_time']) > '10:30': return False
    if (r['currency_value'] or 0) < 30e8 or (r['turnover_rate'] or 0) > 25: return False
    prior = days[max(0, i - 21): i - 1]
    if i - 21 < 0: return False  # 历史不足 20 天不判
    return not any(t['code'] in LU[q] for q in prior)


ok = [t for t in trades if rule_ok(t)]
report(ok, '规则过滤后·全部触板时间')
report([t for t in ok if t['t'] and '09:35' <= t['t'] < '10:30'], '规则过滤后·9:35–10:30 首次触板')
report([t for t in ok if t['t'] and t['t'] < '09:35'], '规则过滤后·9:35 前首次触板')

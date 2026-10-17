"""一进二/二进三条件统计：
1) 最高板断板当天 vs 非断板日；2) 前一日连板亏钱效应后 vs 非亏钱日；3) 按首次触板时间分桶。
用法：python3 stock-research/entry_stats.py"""
import datetime as dt, os, re
from pool_cache import full_pool, R

CST = dt.timezone(dt.timedelta(hours=8))
MAIN = ('600', '601', '603', '605', '000', '001', '002', '003')


def height(h):
    if not h: return 0, False
    if h == '首板': return 1, True
    m = re.match(r'(\d+)天(\d+)板', h)
    return (int(m.group(2)), m.group(1) == m.group(2)) if m else (0, False)


def hm(ts):
    return dt.datetime.fromtimestamp(int(ts), CST).strftime('%H:%M') if ts else None


days = [d for d in sorted(os.listdir(R)) if re.match(r'\d{4}-\d\d-\d\d$', d) and full_pool('limit_up_pool', d)]
LU = {d: {r['code']: r for r in full_pool('limit_up_pool', d) if 'ST' not in (r['name'] or '')} for d in days}
OP = {d: {r['code']: r for r in full_pool('open_limit_pool', d)} for d in days}
LD = {d: {r['code'] for r in full_pool('lower_limit_pool', d)} for d in days}

# 最高板断板：前一日最高板（全市场）当天没有封住
brk, loss, jinji = {}, {}, {}
for i in range(1, len(days)):
    p, d = days[i - 1], days[i]
    top = max(height(r['high_days'])[0] for r in LU[p].values())
    leaders = [c for c, r in LU[p].items() if height(r['high_days'])[0] == top]
    brk[d] = not any(c in LU[d] for c in leaders)
    # 当日连板亏钱效应：前一日 ≥2 连板股今天的表现
    lb = [c for c, r in LU[p].items() if height(r['high_days'])[0] >= 2 and height(r['high_days'])[1]]
    up = sum(c in LU[d] for c in lb); dn = sum(c in LD[d] for c in lb)
    zr = [OP[d][c]['change_rate'] for c in lb if c in OP[d] and OP[d][c]['change_rate'] is not None]
    jinji[d] = up / len(lb) if lb else 0
    loss[d] = dn >= 1 or (lb and up / len(lb) < 0.3)


def samples(stage):
    """返回每个样本：(买入日 D, 结果, 首次触板时间, 炸板亏损, 次日再板, 连续两板, 是否一次封死)"""
    out = []
    for i in range(1, len(days)):
        p, d = days[i - 1], days[i]
        d1 = days[i + 1] if i + 1 < len(days) else None
        d2 = days[i + 2] if i + 2 < len(days) else None
        for c, r in LU[p].items():
            if c[:3] not in MAIN: continue
            h, cons = height(r['high_days'])
            if h != stage or not cons: continue
            if c in LU[d]:
                x = LU[d][c]
                if x['limit_up_type'] == '一字板':
                    out.append((d, 'yizi', None, None, None, None, None)); continue
                n1 = (c in LU[d1]) if d1 else None
                n2 = (n1 and c in LU[d2]) if d2 else None
                out.append((d, 'seal', hm(x['first_limit_up_time']), None, n1, n2, not x['open_num']))
            elif c in OP[d]:
                x = OP[d][c]; cr = x['change_rate']
                out.append((d, 'zha', hm(x['first_limit_up_time']), (1 + cr / 100) / 1.1 - 1 if cr is not None else None, None, None, None))
    return out


def summarize(rows):
    s = [r for r in rows if r[1] == 'seal']; z = [r for r in rows if r[1] == 'zha']
    t = len(s) + len(z)
    if not t: return '| 0 | - | - | - | - |'
    zl = [r[3] for r in z if r[3] is not None]
    n1 = [r[4] for r in s if r[4] is not None]; n2 = [r[5] for r in s if r[5] is not None]
    f = lambda a: f"{sum(a)/len(a):.0%} ({sum(a)}/{len(a)})" if a else '-'
    return (f"| {t} | {len(s)/t:.1%} | {sum(zl)/len(zl)*100:.1f}% | {f(n1)} | {f(n2)} |" if zl else
            f"| {t} | {len(s)/t:.1%} | - | {f(n1)} | {f(n2)} |")


H = '| 条件 | 可买摸板数 | 打板成功率 | 炸板平均亏损 | 成功后次日再板 | 成功后再连两板 |\n|---|---|---|---|---|---|'
print(f'交易日 {len(days)}：{days[0]} → {days[-1]}；最高板断板日 {sum(brk.values())} 天；前一日亏钱效应日 {sum(loss.values())} 天\n')
for stage, nm in ((1, '一进二'), (2, '二进三')):
    rows = samples(stage)
    print(f'## {nm}（已剔除一字板，一字板 {sum(r[1]=="yizi" for r in rows)} 个）\n' + H)
    print('| 全部 ' + summarize(rows))
    print('| 最高板断板当天 ' + summarize([r for r in rows if brk.get(r[0])]))
    print('| 最高板未断板 ' + summarize([r for r in rows if not brk.get(r[0])]))
    prev = {days[i]: loss.get(days[i - 1]) for i in range(1, len(days))}
    print('| 前一日连板亏钱效应 ' + summarize([r for r in rows if prev.get(r[0])]))
    print('| 前一日无亏钱效应 ' + summarize([r for r in rows if prev.get(r[0]) is False]))
    print('| 断板当天且前一日亏钱 ' + summarize([r for r in rows if brk.get(r[0]) and prev.get(r[0])]))
    print('\n按首次触板时间：\n' + H)
    for lo, hi, lab in (('09:25', '09:35', '9:25-9:35'), ('09:35', '10:00', '9:35-10:00'), ('10:00', '10:30', '10:00-10:30'),
                        ('10:30', '13:00', '10:30-13:00'), ('13:00', '15:01', '13:00 以后')):
        print(f'| {lab} ' + summarize([r for r in rows if r[2] and lo <= r[2] < hi]))
    s = [r for r in rows if r[1] == 'seal']
    for lab, flt in (('一次封死', lambda r: r[6]), ('开板后回封', lambda r: r[6] is False)):
        a = [r[4] for r in s if flt(r) and r[4] is not None]
        print(f'封住的票中「{lab}」：{len(a)} 个，次日再板 {sum(a)/max(len(a),1):.0%}')
    print()

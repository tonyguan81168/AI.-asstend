"""连板晋级统计：首板→2板、2板→3板…的晋级率、打板成功率、炸板亏损。
用法：python3 stock-research/ladder_stats.py（数据来自 reports/<日期>/ 下缓存的同花顺涨停/炸板/跌停池）"""
import json, glob, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_hotspots as fh
R = os.path.dirname(os.path.abspath(__file__)) + '/reports'


def main_board(c): return c[:3] in ('600','601','603','605','000','001','002','003')

def lu(day):
    f = f'{R}/{day}/limit_up_pool.json'
    if os.path.exists(f): return json.load(open(f))
    f = f'{R}/{day}/raw.json'
    if os.path.exists(f):
        d = json.load(open(f)).get('ths_limit_up')
        d = d['data'] if isinstance(d, dict) else d
        return d or []
    return []

def pool(kind, day):
    f = f'{R}/{day}/{kind}.json'
    if os.path.exists(f): return json.load(open(f))
    out = []
    for page in range(1, 6):
        p = {'page': page, 'limit': 200, 'field': '199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004',
             'filter': 'HS,GEM2STAR', 'order_field': '330324', 'order_type': '0', 'date': day.replace('-', '')}
        url = f'https://data.10jqka.com.cn/dataapi/limit_up/{kind}?' + urllib.parse.urlencode(p)
        d = json.loads(fh.http_get(url, {'Referer': 'https://data.10jqka.com.cn/'}))
        info = (d.get('data') or {}).get('info') or []
        out += [{'code': r['code'], 'name': r['name'], 'cr': r.get('change_rate')} for r in info]
        if len(info) < 200: break
        time.sleep(0.3)
    json.dump(out, open(f, 'w'), ensure_ascii=False)
    time.sleep(0.3)
    return out

def boards(h):
    if not h: return 0
    if h == '首板': return 1
    m = re.match(r'(\d+)天(\d+)板', h)
    if m and m.group(1) == m.group(2): return int(m.group(1))
    m = re.match(r'(\d+)连板', h)
    return int(m.group(1)) if m else 0

days = sorted(d for d in os.listdir(R) if re.match(r'\d{4}-\d\d-\d\d$', d) and lu(d))
print('交易日', len(days), days[0], '→', days[-1])
LU = {d: {s['code']: s for s in lu(d)} for d in days}
OP = {d: {s['code']: s for s in pool('open_limit_pool', d)} for d in days}
LD = {d: {s['code'] for s in pool('lower_limit_pool', d)} for d in days}

stats = {}
for i in range(len(days) - 1):
    d, d1 = days[i], days[i + 1]
    d2 = days[i + 2] if i + 2 < len(days) else None
    for c, s in LU[d].items():
        if not main_board(c) or 'ST' in (s.get('name') or ''): continue
        n = boards(s.get('high_days'))
        if not n: continue
        k = min(n, 5)
        st = stats.setdefault(k, dict(N=0, seal=0, zha=0, zha_ret=[], down=0, d2_lu=0, d2_zha=0, d2_down=0, d2_n=0))
        st['N'] += 1
        if c in LU[d1]:
            st['seal'] += 1
            if d2:
                st['d2_n'] += 1
                if c in LU[d2]: st['d2_lu'] += 1
                elif c in OP[d2]: st['d2_zha'] += 1
                elif c in LD[d2]: st['d2_down'] += 1
        elif c in OP[d1]:
            st['zha'] += 1
            cr = OP[d1][c]['cr']
            if cr is not None: st['zha_ret'].append((1 + cr / 100) / 1.1 - 1)
        elif c in LD[d1]:
            st['down'] += 1

name = {1: '首板→2板(一进二)', 2: '2板→3板(二进三)', 3: '3板→4板(三进四)', 4: '4板→5板(四进五)', 5: '5板+→再进一板'}
print('| 阶段 | 样本 | 晋级率 | 打板成功率(封住/摸板) | 炸板占比 | 炸板当日平均亏损 | 次日跌停 | 晋级后再涨停率 |')
for k in sorted(stats):
    s = stats[k]; t = s['seal'] + s['zha']
    zr = sum(s['zha_ret']) / len(s['zha_ret']) * 100 if s['zha_ret'] else 0
    print(f"| {name[k]} | {s['N']} | {s['seal']/s['N']:.1%} | {s['seal']/t:.1%} ({s['seal']}/{t}) | {s['zha']/s['N']:.1%} | {zr:.1f}% | {s['down']/s['N']:.1%} | {s['d2_lu']/max(s['d2_n'],1):.1%} ({s['d2_lu']}/{s['d2_n']}) |")

"""盈亏比改进测试：卖出规则对比、入场条件分组、组合与前后半年样本外检验。
用法：python3 stock-research/improve_stats.py（依赖 backtest_yijiner 的缓存）"""
import contextlib, io, statistics as st, sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    import backtest_yijiner as b
from entry_stats import days, LU, OP, LD, hm
K = b.kline
base = [t for t in b.trades if b.rule_ok(t) and t['t'] and '09:35' <= t['t'] < '10:30']

def stat(v, name):
    if not v: return
    w=[x for x in v if x>0]; l=[x for x in v if x<=0]
    aw=st.mean(w) if w else 0; al=st.mean(l) if l else 0
    print(f"| {name} | {len(v)} | {len(w)/len(v):.0%} | {aw:+.2%} | {al:+.2%} | {abs(aw/al) if al else 0:.2f} | {st.mean(v):+.2%} |")

H="| 方案 | 笔数 | 胜率 | 平均盈利 | 平均亏损 | 盈亏比 | 单笔期望 |\n|---|---|---|---|---|---|---|"
# ---- 卖出规则
print("## 卖出规则（规则过滤 + 9:35–10:30）\n"+H)
rows={k:[] for k in 'A E F G H'.split()}
for t in base:
    i=days.index(t['day']); p,d,d1=days[i-1],t['day'],days[i+1]
    k=K(t['code']); B=b.lim(k[p][3]); o,h,l,c=k[d1]; lim1=b.lim(k[d][3])
    sealed = t['code'] in LU[d]
    rows['A'].append(b.pnl(B,o))
    # E: 低开(开盘<买价)开盘卖；高开则持有，跌回买价保本卖，否则收盘卖
    rows['E'].append(b.pnl(B,o) if o<B else b.pnl(B, B if l<=B else c))
    # F: 当天炸板 → 次日开盘卖；当天封住 → 规则E
    rows['F'].append(b.pnl(B,o) if (not sealed or o<B) else b.pnl(B, B if l<=B else c))
    # G: 高开≥3%持有到收盘，否则开盘卖
    rows['G'].append(b.pnl(B,c) if o>=B*1.03 else b.pnl(B,o))
    # H: 开盘卖一半 + 收盘卖一半
    rows['H'].append((b.pnl(B,o)+b.pnl(B,c))/2)
for k,n in (('A','次日开盘全卖（基准）'),('E','低开开盘卖；高开持有，跌回成本保本卖，否则收盘卖'),('F','当日炸板→次日开盘卖；当日封住→同上'),('G','高开≥3%拿到收盘，否则开盘卖'),('H','开盘卖一半+收盘卖一半')): stat(rows[k],n)

# ---- 入场过滤（基准卖法 A）
print("\n## 入场条件（卖法：次日开盘卖）\n"+H)
def feat(t):
    i=days.index(t['day']); p=days[i-1]; q=days[i-2]; r=LU[p][t['code']]
    nlu=len(LU[p]); zr=len(OP[p])/max(len(OP[p])+len(LU[p]),1)
    return dict(open0=not r['open_num'], fd=(r['order_amount'] or 0)/(r['currency_value'] or 1),
                cap=(r['currency_value'] or 0)/1e8, to=r['turnover_rate'] or 0, nlu=nlu, zr=zr,
                seal=hm(r['last_limit_up_time']), sealed=t['code'] in LU[t['day']], ld=len(LD[p]))
F=[(t,feat(t)) for t in base]
stat([t['A'] for t,f in F],'基准')
for name,fn in [('首板一次封死(未开板)',lambda f:f['open0']),('首板开过板',lambda f:not f['open0']),
                ('首板终封≤9:45',lambda f:f['seal']<='09:45'),('首板终封9:45–10:30',lambda f:f['seal']>'09:45'),
                ('封单/流通≥1%',lambda f:f['fd']>=0.01),('封单/流通<1%',lambda f:f['fd']<0.01),
                ('流通30–60亿',lambda f:f['cap']<60),('流通≥60亿',lambda f:f['cap']>=60),
                ('换手≤8%',lambda f:f['to']<=8),('换手>8%',lambda f:f['to']>8),
                ('前日涨停≥60家',lambda f:f['nlu']>=60),('前日涨停<60家',lambda f:f['nlu']<60),
                ('前日炸板率<25%',lambda f:f['zr']<0.25),('前日炸板率≥25%',lambda f:f['zr']>=0.25),
                ('前日跌停<10家',lambda f:f['ld']<10),('前日跌停≥10家',lambda f:f['ld']>=10),
                ('当日封住(未炸)',lambda f:f['sealed']),('当日炸板',lambda f:not f['sealed'])]:
    stat([t['A'] for t,f in F if fn(f)],name)
print("\n## 组合\n"+H)
for name,fn in [('终封≤9:45 + 一次封死',lambda f:f['seal']<='09:45' and f['open0']),
                ('终封≤9:45 + 前日炸板率<25%',lambda f:f['seal']<='09:45' and f['zr']<0.25),
                ('流通≥60亿 + 前日炸板率<25%',lambda f:f['cap']>=60 and f['zr']<0.25),
                ('终封≤9:45 + 流通≥60亿',lambda f:f['seal']<='09:45' and f['cap']>=60)]:
    stat([t['A'] for t,f in F if fn(f)],name)
# 样本外检验：1-6月 vs 7-10月
for name,fn in [('终封≤9:45',lambda f:f['seal']<='09:45'),('前日炸板率<25%',lambda f:f['zr']<0.25),('流通≥60亿',lambda f:f['cap']>=60),('一次封死',lambda f:f['open0'])]:
    for half,hf in (('1–6月',lambda t:t['day']<'2026-07'),('7–10月',lambda t:t['day']>='2026-07')):
        stat([t['A'] for t,f in F if fn(f) and hf(t)],f'{name}·{half}')
        stat([t['A'] for t,f in F if not fn(f) and hf(t)],f'  反面·{half}')

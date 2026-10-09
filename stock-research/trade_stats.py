#!/usr/bin/env python3
"""交易记录统计：胜率、平均盈亏、盈亏比、扣费后期望、最大回撤，并给出是否可以放大仓位的判断。

用法：
    python3 stock-research/trade_stats.py                 # 统计全部
    python3 stock-research/trade_stats.py --mode-only     # 只统计模式内交易
    python3 stock-research/trade_stats.py add 2026-10-12 600478 科力远 1000 9.85 Y 一进二 "回封打板"
    python3 stock-research/trade_stats.py close 3 2026-10-13 10.40 ["备注"]

记录在 stock-research/trades.csv；sell_price 为空表示仍持有。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

CSV = Path(__file__).with_name("trades.csv")
FIELDS = ["id", "buy_date", "code", "name", "shares", "buy_price", "sell_date", "sell_price", "in_mode", "setup", "note"]

# 费用（按普通券商估算，可按自己的佣金修改）
COMMISSION = 0.00025  # 佣金，买卖双向
MIN_COMMISSION = 5.0  # 单笔最低佣金（元）
STAMP_TAX = 0.0005  # 印花税，仅卖出
TRANSFER = 0.00001  # 过户费，双向

# 放大仓位的门槛
MIN_SAMPLES = 30
MIN_EXPECTANCY = 0.005  # 扣费后每笔平均收益 ≥ 0.5%
MAX_AVG_LOSS = 0.03  # 平均亏损 ≤ 3%


def load() -> list[dict]:
    if not CSV.exists():
        return []
    with CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(rows: list[dict]) -> None:
    with CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def fees(amount: float, sell: bool) -> float:
    f = max(amount * COMMISSION, MIN_COMMISSION) + amount * TRANSFER
    return f + (amount * STAMP_TAX if sell else 0)


def pnl(r: dict) -> tuple[float, float]:
    """返回（扣费后盈亏金额, 扣费后收益率）。"""
    n, b, s = int(r["shares"]), float(r["buy_price"]), float(r["sell_price"])
    cost = n * b
    net = n * s - cost - fees(cost, False) - fees(n * s, True)
    return net, net / cost


def stats(rows: list[dict], mode_only: bool) -> None:
    closed = [r for r in rows if r["sell_price"] and (not mode_only or r["in_mode"].upper() == "Y")]
    opened = [r for r in rows if not r["sell_price"]]
    title = "模式内交易" if mode_only else "全部交易"
    print(f"== {title}：已平仓 {len(closed)} 笔，持仓中 {len(opened)} 笔 ==")
    if opened:
        for r in opened:
            print(f"  持仓 #{r['id']} {r['name']} {r['shares']} 股 @ {r['buy_price']}（{'模式内' if r['in_mode'].upper()=='Y' else '模式外'}）")
    if not closed:
        print("  暂无已平仓记录")
        return

    results = [(r, *pnl(r)) for r in closed]
    wins = [x for x in results if x[1] > 0]
    losses = [x for x in results if x[1] <= 0]
    win_rate = len(wins) / len(results)
    avg_win = sum(x[2] for x in wins) / len(wins) if wins else 0.0
    avg_loss = -sum(x[2] for x in losses) / len(losses) if losses else 0.0
    payoff = avg_win / avg_loss if avg_loss else float("inf")
    expectancy = sum(x[2] for x in results) / len(results)
    total = sum(x[1] for x in results)

    # 资金曲线（按平仓顺序累计金额）、最大回撤、最长连亏
    equity = peak = max_dd = 0.0
    streak = max_streak = 0
    for _, amt, _ in sorted(results, key=lambda x: (x[0]["sell_date"], int(x[0]["id"]))):
        equity += amt
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        streak = streak + 1 if amt <= 0 else 0
        max_streak = max(max_streak, streak)

    print(f"  胜率          {win_rate:6.1%}（{len(wins)} 胜 / {len(losses)} 负）")
    print(f"  平均盈利      {avg_win:+6.2%}")
    print(f"  平均亏损      {-avg_loss:+6.2%}")
    print(f"  盈亏比        {payoff:6.2f}")
    print(f"  每笔期望      {expectancy:+6.2%}（已扣佣金、印花税、过户费）")
    print(f"  累计盈亏      {total:+,.0f} 元")
    print(f"  最大回撤      {max_dd:,.0f} 元   最长连亏 {max_streak} 笔")
    print("  明细：")
    for r, amt, pct in results:
        tag = "模式内" if r["in_mode"].upper() == "Y" else "模式外"
        print(f"    #{r['id']} {r['buy_date']} {r['name']} {r['setup']} [{tag}] {pct:+.2%} {amt:+,.0f} 元")

    if mode_only:
        print("\n== 能否放大仓位 ==")
        checks = [
            (len(closed) >= MIN_SAMPLES, f"样本 ≥ {MIN_SAMPLES} 笔（当前 {len(closed)}）"),
            (expectancy >= MIN_EXPECTANCY, f"每笔期望 ≥ {MIN_EXPECTANCY:.1%}（当前 {expectancy:+.2%}）"),
            (avg_loss <= MAX_AVG_LOSS, f"平均亏损 ≤ {MAX_AVG_LOSS:.0%}（当前 {avg_loss:.2%}）"),
            (streak < 3, f"当前未处于连亏 3 笔（当前连亏 {streak}）"),
        ]
        for ok, text in checks:
            print(f"  {'✅' if ok else '❌'} {text}")
        print("  结论：" + ("可以按“盈利满 10% 加 20% 额度”的规则放大" if all(c[0] for c in checks) else "暂不放大，继续用当前仓位积累样本"))


def add(args: list[str]) -> None:
    if len(args) < 7:
        sys.exit("用法：add 买入日期 代码 名称 股数 买入价 Y/N 模式 [备注]")
    rows = load()
    new_id = max((int(r["id"]) for r in rows), default=0) + 1
    rows.append(dict(zip(FIELDS, [str(new_id), *args[:5], "", "", args[5].upper(), args[6], args[7] if len(args) > 7 else ""])))
    save(rows)
    print(f"已记录 #{new_id}")


def close(args: list[str]) -> None:
    if len(args) < 3:
        sys.exit("用法：close 编号 卖出日期 卖出价 [备注]")
    rows = load()
    for r in rows:
        if r["id"] == args[0]:
            r["sell_date"], r["sell_price"] = args[1], args[2]
            if len(args) > 3:
                r["note"] = (r["note"] + "；" if r["note"] else "") + args[3]
            save(rows)
            amt, pct = pnl(r)
            print(f"#{r['id']} {r['name']} 平仓：{pct:+.2%}，{amt:+,.0f} 元")
            return
    sys.exit(f"找不到编号 {args[0]}")


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "add":
        add(argv[1:])
    elif argv and argv[0] == "close":
        close(argv[1:])
    else:
        rows = load()
        stats(rows, mode_only=False)
        print()
        stats(rows, mode_only=True)

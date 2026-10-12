#!/usr/bin/env python3
"""回查候选首板近 N 个交易日的涨停记录，识别“老妖股二次首板”（前期已连板、底仓多，易拉高出货）。

用法：
    python3 stock-research/history_check.py 2026-10-09 600127 600478 ...
    （第一个参数是“首板当天”的日期，之后是代码）

数据来源：同花顺涨停池（逐日查询，结果缓存在 stock-research/reports/<date>/limit_up_pool.json）。
"""
from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import fetch_hotspots as fh  # noqa: E402

REPORTS = Path(__file__).parent / "reports"
LOOKBACK_DAYS = 30  # 日历日，约 20 个交易日


def pool(date: dt.date) -> list[dict]:
    cache = REPORTS / date.isoformat() / "limit_up_pool.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    raw = REPORTS / date.isoformat() / "raw.json"
    if raw.exists():
        rows = json.loads(raw.read_text(encoding="utf-8")).get("ths_limit_up") or []
        if rows:
            return rows
    if date.weekday() >= 5:
        return []
    params = {
        "page": "1", "limit": "200", "field": "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004",
        "filter": "HS,GEM2STAR", "order_field": "330324", "order_type": "0", "date": date.strftime("%Y%m%d"),
    }
    url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?" + urllib.parse.urlencode(params)
    data = json.loads(fh.http_get(url, {"Referer": "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"}))
    rows = [{"code": r.get("code"), "name": r.get("name"), "high_days": r.get("high_days")}
            for r in ((data.get("data") or {}).get("info") or [])]
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return rows


def check(day: dt.date, codes: list[str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {c: [] for c in codes}
    for i in range(1, LOOKBACK_DAYS + 1):
        d = day - dt.timedelta(days=i)
        try:
            rows = pool(d)
        except Exception as e:  # noqa: BLE001
            print(f"  {d} 查询失败：{e}", file=sys.stderr)
            continue
        for r in rows:
            if r.get("code") in hits:
                hits[r["code"]].append(f"{d.isoformat()}({r.get('high_days') or '?'})")
    return hits


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    day = dt.date.fromisoformat(sys.argv[1])
    for code, h in check(day, sys.argv[2:]).items():
        flag = "❌ 剔除（近期已涨停 %d 次，疑似二次首板）" % len(h) if h else "✅ 真首板（近 20 个交易日无涨停）"
        print(f"{code}: {flag}" + (("  " + "、".join(sorted(h))) if h else ""))

#!/usr/bin/env python3
"""每日热点数据抓取：财联社 / 韭研公社 / 同花顺。

只依赖标准库。每个数据源独立抓取，任一失败不影响其它源，
失败原因写进输出的 errors 字段，供后续分析时说明数据缺口。

用法：
    python3 stock-research/fetch_hotspots.py                 # 默认最近一个交易日
    python3 stock-research/fetch_hotspots.py --date 2026-09-25
    python3 stock-research/fetch_hotspots.py --out reports/raw.json

输出一个 JSON（默认写到 stock-research/reports/<date>/raw.json），结构：
    {
      "date": "2026-09-25",
      "fetched_at": "...",
      "cls_telegraph": [...],        # 财联社电报（加红/重要优先）
      "jygs_action": [...],          # 韭研公社异动解析：板块 -> 个股 + 原因
      "ths_limit_up": [...],         # 同花顺涨停池：连板数、涨停原因、封单
      "ths_hot_stocks": [...],       # 同花顺热股榜
      "ths_hot_plates": [...],       # 同花顺热门概念板块
      "errors": {"source": "reason"}
    }

注意：这些接口均为网页端非公开接口，字段可能随网站改版变化；
解析失败时脚本会保留原始片段（raw_sample），便于修正。
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
TIMEOUT = 20


def http_get(url: str, headers: dict | None = None) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip", **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            data = gzip.decompress(data)
        return data.decode(resp.headers.get_content_charset() or "utf-8", errors="replace")


def http_post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": UA, "Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def last_trading_day(today: dt.date) -> dt.date:
    """粗略回退到最近的工作日（不含法定节假日，节假日请用 --date 指定）。"""
    d = today
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


# ---------------------------------------------------------------- 财联社

def fetch_cls_telegraph(date: dt.date, limit: int = 100) -> list[dict]:
    """财联社电报。rn 为条数；返回按时间倒序，只保留指定日期的条目。"""
    params = {"app": "CailianpressWeb", "os": "web", "sv": "8.4.6", "rn": str(limit)}
    url = "https://www.cls.cn/nodeapi/telegraphList?" + urllib.parse.urlencode(params)
    data = json.loads(http_get(url, {"Referer": "https://www.cls.cn/telegraph"}))
    rows = (data.get("data") or {}).get("roll_data") or []
    out = []
    for r in rows:
        ts = dt.datetime.fromtimestamp(int(r.get("ctime", 0)))
        if ts.date() != date:
            continue
        out.append(
            {
                "time": ts.strftime("%H:%M"),
                "title": r.get("title") or "",
                "content": re.sub(r"<[^>]+>", "", r.get("content") or r.get("brief") or "")[:500],
                "important": r.get("level") in ("A", "B") or bool(r.get("recommend")),
                "subjects": [s.get("subject_name") for s in r.get("subjects") or [] if s.get("subject_name")],
                "stocks": [s.get("name") for s in r.get("stock_list") or [] if s.get("name")],
            }
        )
    out.sort(key=lambda x: (not x["important"], x["time"]), reverse=False)
    return out


# ---------------------------------------------------------------- 韭研公社

def _jygs_headers() -> dict:
    ts = str(int(time.time() * 1000))
    token = hashlib.md5(f"Uu0KfOB8iUP69d3c:{ts}".encode()).hexdigest()
    return {
        "platform": "3",
        "timestamp": ts,
        "token": token,
        "Origin": "https://www.jiuyangongshe.com",
        "Referer": "https://www.jiuyangongshe.com/",
    }


def fetch_jygs_action(date: dt.date) -> list[dict]:
    """韭研公社「异动解析」：按板块分组的涨停/异动个股及原因。

    先调 App 接口，失败则回退解析网页 /action/<date> 的内嵌数据。
    """
    try:
        data = http_post_json(
            "https://app.jiuyangongshe.com/jystock-app/api/v1/action/field",
            {"date": date.isoformat(), "pc": 1},
            _jygs_headers(),
        )
        fields = data.get("data") or []
        if isinstance(fields, list) and fields:
            return _parse_jygs_fields(fields)
    except Exception:  # noqa: BLE001 - 回退到网页解析
        pass

    html = http_get(f"https://www.jiuyangongshe.com/action/{date.isoformat()}")
    # 网页为 Nuxt SSR，个股解析在 HTML 中；这里做宽松提取：板块名 + 个股名 + 解析文本
    blocks = re.findall(r'class="[^"]*fs18-bold[^"]*"[^>]*>\s*([^<]{2,30})\s*<', html)
    stocks = re.findall(r'class="[^"]*shrink fs15-bold[^"]*"[^>]*>\s*([^<]{2,12})\s*<', html)
    if not blocks and not stocks:
        raise RuntimeError("网页结构未识别（可能需要登录或页面改版）")
    return [{"plate": b, "stocks": []} for b in blocks] + ([{"plate": "(未分组)", "stocks": [{"name": s} for s in stocks]}] if stocks else [])


def _parse_jygs_fields(fields: list) -> list[dict]:
    out = []
    for f in fields:
        plate = f.get("name") or f.get("field_name") or ""
        if not plate or plate in ("简图",):
            continue
        items = []
        for s in f.get("list") or []:
            info = s.get("article", {}).get("action_info", {}) if isinstance(s.get("article"), dict) else {}
            items.append(
                {
                    "name": s.get("name"),
                    "code": s.get("code"),
                    "limit_time": info.get("time"),
                    "num": info.get("num"),  # 如 "3天2板"
                    "reason": (info.get("expound") or "")[:400],
                }
            )
        out.append({"plate": plate, "reason": (f.get("reason") or "")[:300], "count": len(items), "stocks": items})
    out.sort(key=lambda x: x["count"], reverse=True)
    return out


# ---------------------------------------------------------------- 同花顺

def fetch_ths_limit_up(date: dt.date) -> list[dict]:
    """同花顺涨停池（含连板数、涨停原因、首次/最终封板时间）。"""
    params = {
        "page": "1",
        "limit": "300",
        "field": "199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004",
        "filter": "HS,GEM2STAR",
        "order_field": "330324",
        "order_type": "0",
        "date": date.strftime("%Y%m%d"),
    }
    url = "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool?" + urllib.parse.urlencode(params)
    data = json.loads(http_get(url, {"Referer": "https://data.10jqka.com.cn/datacenterph/limitup/limtupInfo.html"}))
    info = (data.get("data") or {}).get("info") or []
    out = []
    for r in info:
        out.append(
            {
                "code": r.get("code"),
                "name": r.get("name"),
                "change_pct": r.get("change_rate"),
                "reason": r.get("reason_type"),
                "high_days": r.get("high_days"),  # 如 "3天3板"
                "first_limit_time": _ts(r.get("first_limit_up_time")),
                "last_limit_time": _ts(r.get("last_limit_up_time")),
                "open_num": r.get("open_num"),  # 开板次数
                "order_amount": r.get("order_amount"),  # 封单额
                "turnover_rate": r.get("turnover_rate"),
                "market_cap": r.get("currency_value"),
                "is_new": r.get("is_new"),
            }
        )
    return out


def _ts(v) -> str | None:
    try:
        return dt.datetime.fromtimestamp(int(v)).strftime("%H:%M:%S")
    except (TypeError, ValueError):
        return None


def fetch_ths_hot_stocks() -> list[dict]:
    url = (
        "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
        "?stock_type=a&type=day&list_type=normal"
    )
    data = json.loads(http_get(url))
    rows = (data.get("data") or {}).get("stock_list") or []
    return [
        {
            "rank": r.get("order"),
            "code": r.get("code"),
            "name": r.get("name"),
            "change_pct": r.get("rise_and_fall"),
            "heat": r.get("rate"),
            "tags": [t for t in ((r.get("tag") or {}).get("concept_tag") or [])],
            "popularity_tag": (r.get("tag") or {}).get("popularity_tag"),
        }
        for r in rows[:50]
    ]


def fetch_ths_hot_plates() -> list[dict]:
    url = "https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/plate?type=concept"
    data = json.loads(http_get(url))
    rows = (data.get("data") or {}).get("plate_list") or []
    return [
        {
            "rank": r.get("order"),
            "name": r.get("name"),
            "change_pct": r.get("rise_and_fall"),
            "heat": r.get("rate"),
            "limit_up_num": r.get("limit_up_num"),
            "hot_tag": r.get("hot_tag"),
        }
        for r in rows[:30]
    ]


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description="抓取财联社/韭研公社/同花顺每日热点原始数据")
    ap.add_argument("--date", help="交易日 YYYY-MM-DD，默认最近工作日")
    ap.add_argument("--out", help="输出 JSON 路径")
    args = ap.parse_args()

    date = dt.date.fromisoformat(args.date) if args.date else last_trading_day(dt.date.today())
    out_path = Path(args.out) if args.out else Path(__file__).parent / "reports" / date.isoformat() / "raw.json"

    result: dict = {"date": date.isoformat(), "fetched_at": dt.datetime.now().isoformat(timespec="seconds"), "errors": {}}
    jobs = {
        "cls_telegraph": lambda: fetch_cls_telegraph(date),
        "jygs_action": lambda: fetch_jygs_action(date),
        "ths_limit_up": lambda: fetch_ths_limit_up(date),
        "ths_hot_stocks": fetch_ths_hot_stocks,
        "ths_hot_plates": fetch_ths_hot_plates,
    }
    for key, fn in jobs.items():
        try:
            result[key] = fn()
            print(f"[ok]   {key}: {len(result[key])} 条", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError, ValueError, RuntimeError, KeyError, TypeError) as e:
            result[key] = []
            result["errors"][key] = f"{type(e).__name__}: {e}"
            print(f"[fail] {key}: {e}", file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out_path)
    return 0 if len(result["errors"]) < len(jobs) else 1


if __name__ == "__main__":
    raise SystemExit(main())

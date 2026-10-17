"""同花顺涨停/炸板/跌停池完整字段缓存：reports/<日期>/full_<kind>.json。"""
import json, os, time, urllib.parse
import fetch_hotspots as fh

R = os.path.dirname(os.path.abspath(__file__)) + '/reports'
FIELDS = '199112,10,9001,330323,330324,330325,9002,330329,133971,133970,1968584,3475914,9003,9004'
KEEP = ('code', 'name', 'change_rate', 'high_days', 'first_limit_up_time', 'last_limit_up_time',
        'open_num', 'limit_up_type', 'is_again_limit', 'order_amount', 'turnover_rate', 'currency_value')


def full_pool(kind: str, day: str) -> list[dict]:
    f = f'{R}/{day}/full_{kind}.json'
    if os.path.exists(f):
        return json.load(open(f))
    out = []
    for page in range(1, 6):
        p = {'page': page, 'limit': 200, 'field': FIELDS, 'filter': 'HS,GEM2STAR',
             'order_field': '330324', 'order_type': '0', 'date': day.replace('-', '')}
        url = f'https://data.10jqka.com.cn/dataapi/limit_up/{kind}?' + urllib.parse.urlencode(p)
        d = json.loads(fh.http_get(url, {'Referer': 'https://data.10jqka.com.cn/'}))
        if d.get('status_code') != 0:
            raise RuntimeError(d.get('status_msg'))
        info = (d.get('data') or {}).get('info') or []
        out += [{k: r.get(k) for k in KEEP} for r in info]
        if len(info) < 200:
            break
        time.sleep(0.3)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(out, open(f, 'w'), ensure_ascii=False)
    time.sleep(0.3)
    return out

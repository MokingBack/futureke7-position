#!/usr/bin/env python3
"""批量拉东方期货持仓数据"""
import requests, json, time, os, sys
from pathlib import Path

RAW_DIR = Path('/home/user/Doubao/chats/38441425997216770/trade-blueprint-data/raw')
RAW_DIR.mkdir(parents=True, exist_ok=True)

# 从蓝图标注里取交易日
bp = json.load(open('/home/user/Doubao/chats/38441425997216770/trade-blueprint-data/blueprint_raw_2026.json'))
DATES = [d['date'] for d in bp['days']]
print(f"共 {len(DATES)} 个交易日要拉")

URL = 'https://datacenter-web.eastmoney.com/api/data/v1/get'
HEADERS = {'Referer': 'https://data.eastmoney.com/'}

def fetch_day(date):
    fp = RAW_DIR / f'{date}.json'
    if fp.exists():
        print(f"  {date} 已存在,跳过")
        return
    all_rows = []
    page = 1
    while True:
        params = {
            'sortColumns': 'TRADE_CODE,SECURITY_CODE,LPRANK',
            'sortTypes': '1,1,1',
            'pageSize': '500',
            'pageNumber': str(page),
            'reportName': 'RPT_FUTU_DAILYPOSITION',
            'columns': 'ALL',
            'source': 'WEB',
            'client': 'WEB',
            'filter': f"(TRADE_DATE='{date}')(TYPE=\"0\")"
        }
        try:
            r = requests.get(URL, params=params, headers=HEADERS, timeout=30)
            d = r.json()
        except Exception as e:
            print(f"  {date} 第{page}页异常: {e}, 3秒后重试")
            time.sleep(3)
            continue
        if not d.get('result'):
            print(f"  {date} ERR: {d.get('message')}")
            return
        rows = d['result']['data']
        all_rows.extend(rows)
        total = d['result']['pages']
        if page >= total:
            break
        page += 1
        time.sleep(0.15)
    with open(fp, 'w') as f:
        json.dump(all_rows, f, ensure_ascii=False)
    print(f"  {date}: {len(all_rows)} rows, saved")

for i, date in enumerate(DATES, 1):
    print(f"[{i}/{len(DATES)}] {date}")
    fetch_day(date)

print("全部完成")

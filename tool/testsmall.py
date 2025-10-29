#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试获取单只基金历史涨跌
"""

import requests
import json
from datetime import date, timedelta
import re

HEADERS = {"User-Agent": "python-requests/2.x (+https://github.com/)"}

def fetch_history_nav(code: str, days: int = 5):
    """抓取基金最近 days 个交易日的净值涨跌"""
    end = date.today()
    start = end - timedelta(days=days*2)  # 多取几天保证获取到交易日
    url = (
        f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}"
        f"&pageIndex=1&pageSize={days}&startDate={start}&endDate={end}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        r.raise_for_status()
        data = r.json()
        rows = data.get("Data", {}).get("LSJZList", [])
        pct = []
        for row in rows:
            val = row.get("JZZZL", "")
            if val and re.match(r"[\-\+]?\d+(\.\d+)?", val):
                pct.append(float(val))
        return list(reversed(pct))  # 从旧到新
    except Exception as e:
        print("异常:", e)
        return []

if __name__ == "__main__":
    fund_code = "019020"
    history = fetch_history_nav(fund_code, days=5)
    print(f"基金 {fund_code} 最近 {len(history)} 个交易日涨跌：", history)

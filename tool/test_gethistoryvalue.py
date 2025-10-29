#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试抓取单只基金历史净值（涨跌百分比）脚本
"""

import requests
import json
import re
from datetime import datetime, timedelta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.0.0 Safari/537.36",
}

def fetch_history_nav(code: str, days: int = 5):
    end = datetime.today()
    start = end - timedelta(days=days*3)
    url = "https://api.fund.eastmoney.com/f10/lsjz"
    params = {
        "fundCode": code,
        "pageIndex": 1,
        "pageSize": days * 2,
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "_": int(end.timestamp() * 1000)
    }
    headers = HEADERS.copy()
    headers["Referer"] = f"https://fundf10.eastmoney.com/jjjz_{code}.html"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=8)
        print("Raw response for code", code, ":", r.text[:500])
        # 提取回调函数包裹的 JSON
        m = re.search(r"\((\{.*\})\)", r.text)
        if m:
            data = json.loads(m.group(1))
        else:
            data = r.json()
        if "Data" not in data or "LSJZList" not in data["Data"]:
            print("Unexpected data structure:", data)
            return []
        rows = data["Data"]["LSJZList"]
        pct = []
        for row in rows:
            val = row.get("JZZZL", "")
            if val and re.match(r"[\-\+]?\d+(\.\d+)?", str(val)):
                pct.append(float(val))
        return list(reversed(pct))[:days]
    except Exception as e:
        print("异常:", e)
        return []

if __name__ == "__main__":
    fund_code = "019020"
    history = fetch_history_nav(fund_code, days=5)
    print(f"基金 {fund_code} 最近 {len(history)} 个交易日涨跌：", history)

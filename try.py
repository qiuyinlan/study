#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund_signals_final_all.py
- 自动抓取当日基金涨跌（fundgz / eastmoney）
- 获取历史净值并计算连续同向涨跌段（从最近一天开始，按多数方向判定）
- 自动计算信号强度
- 输出 CSV: outputs/signals_YYYYMMDD.csv
- 可选 --date 参数指定分析日期
"""

import os
import csv
import json
import re
import requests
import argparse
from datetime import date, timedelta
from typing import List, Optional

# ========== 配置 ==========
FUNDS = [
    {"name": "易方达医疗保健行业混合C", "code": "019020"},
    {"name": "易方达港股通优质增长混合C", "code": "017974"},
    {"name": "易方达机器人ETF联接C", "code": "020973"},
    {"name": "易方达标普信息科技指数(QDII-LOF)C", "code": "012868"},
    {"name": "易方达人工智能ETF联接C", "code": "023565"},
    {"name": "易方达全球成长精选混合(QDII)C", "code": "012922"},
    {"name": "华夏恒生科技ETF联接(QDII)C", "code": "513180"},
    {"name": "华夏食品饮料ETF联接C", "code": "013126"},
    {"name": "华安标普全球石油指数(QDII-LOF)C", "code": "014982"},
    {"name": "华安中证云计算与大数据主题指数C", "code": "019990"},
    {"name": "前海开源中证军工指数A", "code": "000596"},
    {"name": "永赢低碳环保智选混合C", "code": "016387"},
    {"name": "永赢半导体产业智选混合C", "code": "015968"},
    {"name": "永赢医药创新智选混合C", "code": "015916"},
    {"name": "永赢中证沪深港黄金产业股票ETF联接C", "code": "517520"},
    {"name": "永赢数字经济智选混合C", "code": "018123"},
    {"name": "华泰柏瑞中证红利低波动ETF联接C", "code": "007467"},
    {"name": "天弘中证细分化工产业主题指数C", "code": "015897"},
    {"name": "天弘纳斯达克100指数(QDII)C", "code": "018044"},
    {"name": "招商沪深300地产等权重C", "code": "013273"},
    {"name": "招商中证白酒指数C", "code": "012414"},
    {"name": "招商中证TMT50ETF联接C", "code": "004409"},
    {"name": "安信医药健康主题股票C", "code": "010710"},
    {"name": "广发中证环保产业ETF联接C", "code": "002984"},
    {"name": "广发港股通互联网指数C", "code": "021093"},
    {"name": "广发纳斯达克100ETF联接QDII/C", "code": "006479"},
    {"name": "华宝中证医疗ETF联接C", "code": "512170"},
    {"name": "华宝中证稀有金属主题指数增强C", "code": "013943"},
    {"name": "大成标普500等权重指数(QDII)A", "code": "013404"},
    {"name": "大成标普500等权重指数(QDII)C", "code": "008401"},
    {"name": "大成纳斯达克100ETF联接QDII/C", "code": "008971"},
    {"name": "中欧医疗健康混合C", "code": "003096"},
    {"name": "东方阿尔法优选混合C", "code": "007519"},
    {"name": "富国全球消费精选混合(QDII)C", "code": "012062"},
    {"name": "长城新兴产业灵活配置混合C", "code": "019412"},
    {"name": "中信建投低碳成长混合C", "code": "013852"},
    {"name": "中航机遇领航混合C", "code": "018957"},
    {"name": "鹏华碳中和主题混合C", "code": "016531"},
    {"name": "银华中证光伏产业ETF联接C", "code": "516880"},
    {"name": "国联安中证半导体ETF联接C", "code": "007301"},
    {"name": "德邦鑫星价值灵活配置混合C", "code": "002112"},
    {"name": "嘉实上证科创板芯片ETF联接C", "code": "588200"},
]

OUTPUT_DIR = "outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

THRESHOLDS = {
    "daily_move_threshold": 1.5,      # 单日涨跌阈值
    "signal_strength_cutoff": 0.4
}

HEADERS = {"User-Agent": "python-requests/2.x (+https://github.com/)"}

# ========== 数据抓取 ==========

def fetch_fundgz(code: str) -> Optional[dict]:
    url = f"http://fundgz.1234567.com.cn/js/{code}.js"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return None
        m = re.search(r"(\{.*\})", r.text)
        if not m:
            return None
        return json.loads(m.group(1))
    except Exception:
        return None

def fetch_eastmoney(code: str) -> Optional[dict]:
    url = f"https://fund.eastmoney.com/{code}.html"
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return None
        txt = r.text
        m = re.search(r"单位净值.*?(\d+\.\d+).*?\(([\+\-]\d+\.\d+)%\)", txt)
        if m:
            return {"name": "", "gszzl": m.group(2)}
        return None
    except Exception:
        return None

def fetch_history_nav(code: str, days: int = 5) -> List[float]:
    """从天天基金抓取最近 N 日涨跌"""
    from datetime import datetime, timedelta
    end = datetime.today()
    start = end - timedelta(days=days*3)
    url = "https://api.fund.eastmoney.com/f10/lsjz"
    params = {
        "fundCode": code,
        "pageIndex": 1,
        "pageSize": days*2,
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "_": int(end.timestamp()*1000)
    }
    headers = HEADERS.copy()
    headers["Referer"] = f"https://fundf10.eastmoney.com/jjjz_{code}.html"
    try:
        r = requests.get(url, headers=headers, params=params, timeout=8)
        r.raise_for_status()
        data = r.json()
        lsjz = data.get("Data", {}).get("LSJZList", [])
        pct = []
        for row in reversed(lsjz):  # 从旧到新
            val = row.get("JZZZL")
            if val:
                pct.append(float(val))
        return pct[:days]
    except Exception as e:
        print("异常:", e)
        return []

# ========== 连续计算（按多数方向判定） ==========

def compute_recent_consecutive(history: List[float]) -> (int, int, float):
    """
    从最近一天开始，统计同向连续天数（多数方向判定，零天不算）
    返回：
        consecutive_days, consecutive_direction (1=涨,-1=跌), consecutive_change_pct
    """
    if not history:
        return 0, 0, 0.0
    # 判定多数方向
    non_zero = [x for x in history if x != 0]
    if not non_zero:
        return 0, 0, 0.0
    pos = sum(1 for x in non_zero if x > 0)
    neg = sum(1 for x in non_zero if x < 0)
    direction = 1 if pos >= neg else -1
    # 统计连续天数
    count, change_sum = 0, 0.0
    for delta in reversed(history):
        if delta == 0:
            continue
        cur_dir = 1 if delta > 0 else -1
        if cur_dir == direction:
            count += 1
            change_sum += delta
        else:
            break
    return count, direction, change_sum

# ========== 信号生成 ==========

def generate_signal(daily_change_pct, consecutive_days, consecutive_change_pct):
    sig, reasons, risk = "无操作", "", ""
    if abs(daily_change_pct) >= THRESHOLDS["daily_move_threshold"]:
        sig = "买入" if daily_change_pct > 0 else "减持"
        reasons = f"单日涨跌 {daily_change_pct:.2f}% 超阈值"
        risk = "关注波动性"
    elif consecutive_days >= 2:
        sig = "趋势提醒"
        reasons = f"连续 {consecutive_days} 天同向涨跌 {consecutive_change_pct:.2f}%"
        risk = "趋势持续可能有机会或风险"
    return sig, reasons, risk

# ========== 主流程 ==========

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, default=date.today().isoformat(), help="指定日期，格式 YYYY-MM-DD")
    args = parser.parse_args()
    today = args.date
    results = []

    for f in FUNDS:
        code, name = f["code"], f["name"]

        data = fetch_fundgz(code) or fetch_eastmoney(code)
        daily_change_pct = float(data.get("gszzl", 0.0)) if data else 0.0

        history = fetch_history_nav(code, days=5) + [daily_change_pct]
        consecutive_days, consecutive_direction, consecutive_change_pct = compute_recent_consecutive(history)

        strength = min(1, abs(consecutive_change_pct)/10)  # 可按规则调整

        sig, reasons, risk = generate_signal(daily_change_pct, consecutive_days, consecutive_change_pct)

        results.append({
            "date": today,
            "name": name,
            "daily_change_pct": daily_change_pct,
            "consecutive_days": consecutive_days,
            "consecutive_direction": consecutive_direction,
            "consecutive_change_pct": round(consecutive_change_pct,2),
            "strength": round(strength,2),
            "reasons": reasons,
            "risk_warning": risk
        })

    out_file = os.path.join(OUTPUT_DIR, f"signals_{today.replace('-','')}.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ 已生成 {out_file}")

if __name__ == "__main__":
    main()

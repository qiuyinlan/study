#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund_signals_final_all.py
- 自动抓取当日基金涨跌（fundgz / eastmoney）
- 获取历史净值并计算概率连续同向涨跌段
- 自动计算信号强度
- 输出 CSV: outputs/signals_YYYYMMDD.csv
"""

import os
import csv
import json
import re
import requests
import argparse
from datetime import date, datetime, timedelta
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
    "window_days": 5,                  # 概率连续窗口天数
    "prob_threshold": 0.6,             # 同向涨跌占比阈值
    "signal_strength_cutoff": 0.4
}

HEADERS = {"User-Agent": "python-requests/2.x (+https://github.com/)"}

# ========== 数据抓取部分 ==========

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

def fetch_history(code: str, days: int = 20) -> List[float]:
    """从天天基金抓取近 N 日涨跌幅"""
    end = date.today()
    start = end - timedelta(days=days * 2)
    url = (
        f"https://api.fund.eastmoney.com/f10/lsjz?fundCode={code}"
        f"&pageIndex=1&pageSize={days}&startDate={start}&endDate={end}"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return []
        data = json.loads(r.text)
        rows = data.get("Data", {}).get("LSJZList", [])
        pct = []
        for row in rows:
            val = row.get("JZZZL", "")
            if val and re.match(r"[\-\+]?\d+(\.\d+)?", val):
                pct.append(float(val))
        return list(reversed(pct))
    except Exception:
        return []

# ========== 概率连续计算 ==========

def compute_probabilistic_consecutive(history: List[float], window: int = 5) -> (int, int, float):
    """
    计算最近 window 天中同向涨跌占比
    返回：
        window: 天数
        count: 同向涨跌天数
        ratio: 占比 (0~1)
    """
    if not history:
        return 0, 0, 0.0
    recent = history[-window:]
    ups = sum(1 for x in recent if x > 0)
    downs = sum(1 for x in recent if x < 0)
    if ups >= downs:
        return window, ups, ups/window
    else:
        return window, downs, downs/window

# ========== 信号生成 ==========

def generate_signal(daily_change_pct, window, count, ratio):
    sig, action, reasons, risk = "无操作", "", "", ""
    if abs(daily_change_pct) >= THRESHOLDS["daily_move_threshold"]:
        sig = "买入" if daily_change_pct > 0 else "减持"
        action = "增配" if daily_change_pct > 0 else "减仓"
        reasons = f"单日涨跌 {daily_change_pct:.2f}% 超阈值"
        risk = "关注波动性"
    elif ratio >= THRESHOLDS["prob_threshold"]:
        sig = "趋势提醒"
        action = "观察"
        reasons = f"最近 {window} 天同向涨跌 {count} 天，占比 {ratio:.2f}"
        risk = "趋势持续可能有机会或风险"
    return sig, action, reasons, risk

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

        history = fetch_history(code, days=20)
        window, count, ratio = compute_probabilistic_consecutive(history + [daily_change_pct], window=THRESHOLDS["window_days"])

        strength = min(1, ratio)  # 用占比作为信号强度

        sig, action, reasons, risk = generate_signal(daily_change_pct, window, count, ratio)

        results.append({
            "date": today,
            "name": name,
            "daily_change_pct": daily_change_pct,
            "window_days": window,
            "consecutive_count": count,
            "consecutive_ratio": round(ratio, 2),
            "signal_type": sig,
            "strength": round(strength, 2),
            "reasons": reasons,
            "action_suggestion": action,
            "data_points_snapshot": f"{history + [daily_change_pct]}",
            "risk_warning": risk
        })

    out_file = os.path.join(OUTPUT_DIR, f"signals_{today.replace('-', '')}.csv")
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    print(f"✅ 已生成 {out_file}")


if __name__ == "__main__":
    main()

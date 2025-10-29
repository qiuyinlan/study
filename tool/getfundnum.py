#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fund_code_fuzzy_match.py

用途：
- 从天天基金的 fundcode_search.js 下载基金名单（稳定）
- 对给定的基金名称列表做多步匹配（exact, substring, fuzzy）
- 输出 Excel，包含匹配代码、匹配名称、相似度分数、匹配方法，便于人工复核
"""

import requests
import json
import re
import pandas as pd
from difflib import SequenceMatcher
from typing import List, Tuple

# ========== 配置 ==========
FUND_NAMES = [
    "易方达医疗保健行业混合C",
    "易方达港股通优质增长混合C",
    "易方达机器人ETF联接C（易方达国证机器人产业ETF联接发起式C）",
    "易方达标普信息科技指数(QDII-LOF)C",
    "易方达人工智能ETF联接C",
    "易方达全球成长精选混合(QDII)C",
    "华夏恒生科技ETF联接(QDII)C",
    "华夏食品饮料ETF联接C",
    "华安标普全球石油指数(QDII-LOF)C",
    "华安中证云计算与大数据主题指数C",
    "前海开源中证军工指数A",
    "永赢低碳环保智选混合C",
    "永赢半导体产业智选混合C",
    "永赢医药创新智选混合C",
    "永赢中证沪深港黄金产业股票ETF联接C",
    "永赢数字经济智选混合C",
    "华泰柏瑞中证红利低波动ETF联接C",
    "天弘中证细分化工产业主题指数C",
    "天弘纳斯达克100指数(QDII)C",
    "招商沪深300地产等权重C",
    "招商中证白酒指数C",
    "招商中证TMT50ETF联接C",
    "安信医药健康主题股票C",
    "广发中证环保产业ETF联接C",
    "广发港股通互联网指数C",
    "广发纳斯达克100ETF联接QDII/C",
    "华宝中证医疗ETF联接C",
    "华宝中证稀有金属主题指数增强C",
    "大成标普500等权重指数(QDII)A",
    "大成标普500等权重指数(QDII)C",
    "大成纳斯达克100ETF联接QDII/C",
    "中欧医疗健康混合C",
    "东方阿尔法优选混合C",
    "富国全球消费精选混合(QDII)C",
    "长城新兴产业灵活配置混合C",
    "中信建投低碳成长混合C",
    "中航机遇领航混合C",
    "鹏华碳中和主题混合C",
    "银华中证光伏产业ETF联接C",
    "国联安中证半导体ETF联接C",
    "德邦鑫星价值灵活配置混合C",
    "嘉实上证科创板芯片ETF联接C"
]

FUND_JS_URL = "http://fund.eastmoney.com/js/fundcode_search.js"
OUT_XLSX = "基金代码匹配结果_含相似度.xlsx"
FUZZY_THRESHOLD = 0.70  # 相似度阈值（0-1），低于此认为较不确定

# ========== 工具函数 ==========
def download_fund_list(url: str):
    print("下载基金代码库...")
    r = requests.get(url, timeout=15)
    r.encoding = r.apparent_encoding
    js_text = r.text
    # 提取中间的 JSON 数组部分
    start = js_text.find("[[")
    end = js_text.rfind("]]")
    if start < 0 or end < 0:
        raise RuntimeError("无法解析 fundcode_search.js 格式")
    json_text = js_text[start:end+2]
    data = json.loads(json_text)
    # data 格式：[ [code, abbrev, fullname, type, pinyin], ... ]
    return data

def normalize(s: str) -> str:
    """标准化名称用于匹配：去括号、去空格、去类后缀、统一大小写"""
    if s is None:
        return ""
    s2 = re.sub(r"（.*?）|\(.*?\)", "", s)  # 去掉括号内容
    s2 = s2.replace(" ", "").replace("　", "")
    s2 = s2.replace("A类", "").replace("B类", "").replace("C类", "").replace("/C", "").replace("/A", "")
    s2 = s2.strip().lower()
    return s2

def seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# ========== 主匹配逻辑 ==========
def match_funds(fund_names: List[str], fund_data: List[List[str]]):
    # 先把官方名字做索引
    index = []
    for item in fund_data:
        code = item[0]
        fullname = item[2]
        t = item[3] if len(item) > 3 else ""
        index.append({"code": code, "name": fullname, "type": t, "norm": normalize(fullname)})
    results = []
    names_norm_map = {name: normalize(name) for name in fund_names}

    for orig_name in fund_names:
        norm = names_norm_map[orig_name]
        matched = None
        method = ""
        score = 0.0
        candidate_name = ""
        candidate_code = ""

        # 1) 精确（规范化后完全相等）
        for it in index:
            if norm == it["norm"]:
                matched = it
                method = "exact"
                score = 1.0
                break

        # 2) 子串匹配：规范名互为子串
        if not matched:
            for it in index:
                if norm in it["norm"] or it["norm"] in norm:
                    matched = it
                    method = "substring"
                    score = seq_ratio(norm, it["norm"])
                    break

        # 3) fuzzy（取 top1 相似度）
        if not matched:
            best = None
            best_score = 0.0
            for it in index:
                r = seq_ratio(norm, it["norm"])
                if r > best_score:
                    best_score = r
                    best = it
            if best and best_score >= FUZZY_THRESHOLD:
                matched = best
                method = "fuzzy"
                score = best_score

        if matched:
            candidate_code = matched["code"]
            candidate_name = matched["name"]
        else:
            candidate_code = "未找到"
            candidate_name = ""

        results.append({
            "原始名称": orig_name,
            "规范化名称": norm,
            "匹配代码": candidate_code,
            "匹配名称(官方)": candidate_name,
            "匹配方式": method if method else "未匹配",
            "相似度_score": round(score, 4)
        })

    return results

# ========== 执行 ==========
def main():
    fund_data = download_fund_list(FUND_JS_URL)
    results = match_funds(FUND_NAMES, fund_data)
    df = pd.DataFrame(results)
    # 给低置信度行标注提醒，方便人工核对
    df["需人工复核"] = df["相似度_score"].apply(lambda x: "是" if x < 0.85 or x == 0.0 else "否")
    df.to_excel(OUT_XLSX, index=False)
    print(f"完成：已将匹配结果保存到 {OUT_XLSX}")
    print("建议：打开 Excel，优先检查“需人工复核=是”的行并确认代码是否正确。")

if __name__ == "__main__":
    main()

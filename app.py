from flask import Flask, jsonify, render_template
import success  # 复用 success.py 中的核心逻辑
from datetime import date
import os

# 初始化 Flask 应用
app = Flask(__name__)

# 确保输出目录存在（复用 success.py 的配置）
os.makedirs(success.OUTPUT_DIR, exist_ok=True)

# ========== 路由定义 ==========

@app.route("/")
def index():
    """首页：展示所有基金信号的简单页面"""
    return render_template("index.html")

@app.route("/api/funds")
def get_all_funds():
    """API：获取所有基金的基本信息（名称、代码）"""
    return jsonify(success.FUNDS)

@app.route("/api/fund/<code>")
def get_fund_detail(code):
    """API：获取单只基金的实时数据和信号分析"""
    # 1. 抓取实时数据
    data = success.fetch_fundgz(code) or success.fetch_eastmoney(code)
    if not data:
        return jsonify({"error": "基金代码不存在或数据获取失败"}), 404
    
    daily_change_pct = float(data.get("gszzl", 0.0))
    
    # 2. 抓取历史数据并计算连续趋势
    history = success.fetch_history_nav(code, days=5) + [daily_change_pct]
    consecutive_days, consecutive_dir, consecutive_pct = success.compute_recent_consecutive(history)
    
    # 3. 生成信号
    sig, reasons, risk = success.generate_signal(daily_change_pct, consecutive_days, consecutive_pct)
    
    # 4. 查找基金名称
    fund_name = next((f["name"] for f in success.FUNDS if f["code"] == code), "未知名称")
    
    return jsonify({
        "code": code,
        "name": fund_name,
        "daily_change_pct": daily_change_pct,
        "consecutive_days": consecutive_days,
        "consecutive_direction": "上涨" if consecutive_dir == 1 else "下跌" if consecutive_dir == -1 else "持平",
        "consecutive_change_pct": round(consecutive_pct, 2),
        "signal": sig,
        "reasons": reasons,
        "risk_warning": risk
    })

@app.route("/api/funds/signals")
def get_all_signals():
    """API：获取所有基金的信号分析（类似 success.py 的 main 函数逻辑）"""
    today = date.today().isoformat()
    results = []
    for fund in success.FUNDS:
        code, name = fund["code"], fund["name"]
        
        # 复用 success.py 的数据抓取和计算流程
        data = success.fetch_fundgz(code) or success.fetch_eastmoney(code)
        daily_change_pct = float(data.get("gszzl", 0.0)) if data else 0.0
        
        history = success.fetch_history_nav(code, days=5) + [daily_change_pct]
        consecutive_days, consecutive_dir, consecutive_pct = success.compute_recent_consecutive(history)
        
        sig, reasons, risk = success.generate_signal(daily_change_pct, consecutive_days, consecutive_pct)
        
        strength = min(1, abs(consecutive_pct)/10)  # 信号强度（复用 success.py 逻辑）
        
        results.append({
            "date": today,
            "code": code,
            "name": name,
            "daily_change_pct": daily_change_pct,
            "consecutive_days": consecutive_days,
            "signal": sig,
            "strength": round(strength, 2),
            "reasons": reasons
        })
    return jsonify(results)

# ========== 运行应用 ==========
if __name__ == "__main__":
    # 开发环境：开启 debug 模式，允许外部访问
    app.run(host="0.0.0.0", port=5000, debug=True)
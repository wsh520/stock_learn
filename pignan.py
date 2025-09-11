import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
from datetime import timedelta


def analyze_stock_profit(symbol: str, buy_date_str: str, buy_qty: int):
    """
    分析指定股票在近一年内的买入收益，并绘制收益率曲线

    参数:
        symbol: 股票代码（如 "sh601318"）
        buy_date_str: 买入日期（格式 "YYYY-MM-DD"，必须是交易日）
        buy_qty: 买入数量（股）
    """
    print(f"正在获取 {symbol} 近一年的历史股价数据...")

    # --- 1. 获取数据 ---
    stock_data = ak.stock_zh_a_daily(symbol=symbol).reset_index()
    # 日期字段兼容不同版本
    if "date" in stock_data.columns:
        stock_data.rename(columns={"date": "trade_date"}, inplace=True)
    elif "index" in stock_data.columns:
        stock_data.rename(columns={"index": "trade_date"}, inplace=True)
    stock_data["trade_date"] = pd.to_datetime(stock_data["trade_date"])

    # 近一年数据
    end_date = stock_data["trade_date"].max()
    start_date = end_date - timedelta(days=365)
    stock_data = stock_data[(stock_data["trade_date"] >= start_date) & (stock_data["trade_date"] <= end_date)]
    stock_data = stock_data.sort_values("trade_date").reset_index(drop=True)

    print(
        f"成功获取 {len(stock_data)} 条记录，时间范围：{stock_data['trade_date'].min().date()} ~ {stock_data['trade_date'].max().date()}")

    # --- 2. 买入逻辑 ---
    buy_date = pd.to_datetime(buy_date_str)
    if buy_date not in stock_data["trade_date"].values:
        raise ValueError(f"买入日期 {buy_date_str} 不是交易日，请选择有效交易日")

    buy_price = stock_data.loc[stock_data["trade_date"] == buy_date, "close"].values[0]
    print(f"\n买入日期: {buy_date.date()}，买入价格: {buy_price:.2f} 元，买入数量: {buy_qty} 股")

    # --- 3. 计算收益 ---
    future_data = stock_data[stock_data["trade_date"] >= buy_date].copy()
    future_data["收益率"] = (future_data["close"] - buy_price) / buy_price
    future_data["累计收益"] = future_data["收益率"] * buy_qty * buy_price

    final_yield = future_data["收益率"].iloc[-1]
    final_profit = future_data["累计收益"].iloc[-1]

    print(
        f"截止 {future_data['trade_date'].iloc[-1].date()}，累计收益率: {final_yield * 100:.2f}%，总收益: {final_profit:.2f} 元")

    # --- 4. 绘制收益曲线 ---
    plt.figure(figsize=(14, 7))
    plt.plot(future_data["trade_date"], future_data["收益率"] * 100, label="收益率(%)", color="green")
    plt.axhline(0, color="black", linestyle="--", linewidth=1)  # 零收益线
    plt.axvline(buy_date, color="red", linestyle=":", label="买入日期")

    plt.xlabel("日期")
    plt.ylabel("收益率 (%)")
    plt.title(f"{symbol} 收益曲线（买入日: {buy_date.date()}，数量: {buy_qty} 股）")
    plt.legend()
    plt.grid(True, linestyle=":", alpha=0.7)
    plt.tight_layout()
    plt.show()


# --- 使用示例 ---
# 中国平安（601318.SH），买入日期为 2025-03-03，买入 100 股
# analyze_stock_profit("sh601318", "2025-03-03", 100)

if __name__ == "__main__":
    analyze_stock_profit("sh601318", "2025-03-03", 100)
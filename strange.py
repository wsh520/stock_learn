import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt


def simulate_a_stock_strategy(stock_code, buy_date_str, end_date_str, init_invest=10000):
    """
    A股动态加仓+止盈策略回测（兼容最新版AkShare）
    stock_code: 股票代码，如 "601318"
    buy_date_str: 买入日期 "YYYY-MM-DD"
    end_date_str: 截止日期 "YYYY-MM-DD"
    init_invest: 初始投入资金
    """
    # 获取历史数据
    df = ak.stock_zh_a_daily(
        symbol=stock_code,
        start_date=buy_date_str.replace("-", ""),
        end_date=end_date_str.replace("-", "")
    )

    if df.empty:
        print("未获取到数据，请检查股票代码或日期")
        return

    # 兼容列名
    df = df.reset_index()
    if "trade_date" in df.columns:
        df.rename(columns={'trade_date': 'Date', 'close': 'Close'}, inplace=True)
    elif "date" in df.columns:
        df.rename(columns={'date': 'Date', 'close': 'Close'}, inplace=True)
    else:
        raise ValueError("未找到日期列，请检查 AkShare 版本或数据返回格式")

    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)
    df = df[(df['Date'] >= pd.to_datetime(buy_date_str)) & (df['Date'] <= pd.to_datetime(end_date_str))].reset_index(
        drop=True)

    if df.empty:
        print("买入日不在交易日范围内")
        return

    # 初始化买入
    buy_price = df.loc[0, 'Close']
    shares = init_invest / buy_price
    cash = 0
    invest_base = init_invest
    history_value = []

    # 交易点记录
    add_points = []  # 补仓
    sell_points = []  # 止盈

    for i in range(len(df)):
        price = df.loc[i, 'Close']
        value = shares * price + cash

        # 下跌补仓
        if price <= buy_price * 0.9:
            loss = invest_base - value
            if loss > 0:
                add_shares = loss / price
                shares += add_shares
                invest_base += loss
                add_points.append((df.loc[i, 'Date'], value + loss))
                print(f"{df.loc[i, 'Date'].date()} 下跌补仓: 追加 {loss:.2f}, 总投入 {invest_base:.2f}")

        # 上涨止盈
        elif price >= buy_price * 1.1:
            profit = value - invest_base
            if profit > 0:
                sell_shares = profit / price
                shares -= sell_shares
                cash += profit
                sell_points.append((df.loc[i, 'Date'], invest_base + profit))
                print(f"{df.loc[i, 'Date'].date()} 止盈卖出: 套现 {profit:.2f}, 保持本金 {invest_base:.2f}")

        history_value.append(value)

    # 最终结果
    final_value = shares * df.iloc[-1]['Close'] + cash
    profit = final_value - invest_base
    profit_rate = profit / invest_base * 100

    print(f"\n初始买入日: {buy_date_str}, 截止日: {end_date_str}")
    print(f"投入本金: {invest_base:.2f}")
    print(f"期末总市值: {final_value:.2f}")
    print(f"总收益: {profit:.2f}, 收益率: {profit_rate:.2f}%")

    # 绘制账户市值曲线
    plt.figure(figsize=(12, 6))
    plt.plot(df['Date'], history_value, label="账户市值", color="blue")
    plt.axhline(invest_base, color='red', linestyle='--', label="本金")
    plt.axvline(pd.to_datetime(buy_date_str), color='green', linestyle=':', label="买入日")

    # 标记交易点
    if add_points:
        add_dates, add_values = zip(*add_points)
        plt.scatter(add_dates, add_values, color='orange', label="补仓点", marker='^', s=100)
    if sell_points:
        sell_dates, sell_values = zip(*sell_points)
        plt.scatter(sell_dates, sell_values, color='purple', label="止盈点", marker='v', s=100)

    plt.xlabel("日期")
    plt.ylabel("市值 (元)")
    plt.title(f"{stock_code} 策略回测（加仓/止盈标记）")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.show()


# 示例调用
simulate_a_stock_strategy("sh601318", "2024-08-01", "2025-08-01", 10000)

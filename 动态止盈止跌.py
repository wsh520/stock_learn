import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt

def simulate_avg_strategy_with_plot(stock_code, buy_date_str, end_date_str, init_invest=10000, max_invest=50000, window=5):
    """
    动态均值止盈/止跌策略回测，支持最大投入金额和止盈资金再投入，图上标注均值和交易点
    """
    # 获取历史数据
    df = ak.stock_zh_a_hist(
        symbol=stock_code,
        period="daily",
        start_date=buy_date_str.replace("-", ""),
        end_date=end_date_str.replace("-", ""),
        adjust="qfq"
    )
    if df.empty:
        print("未获取到数据，请检查股票代码或日期")
        return

    df = df[['日期', '收盘']].copy()
    df.rename(columns={'日期': 'Date', '收盘': 'Close'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)
    df = df[(df['Date'] >= pd.to_datetime(buy_date_str)) & (df['Date'] <= pd.to_datetime(end_date_str))].reset_index(drop=True)
    if df.empty:
        print("买入日不在交易日范围内")
        return

    # 初始化
    buy_price = df.loc[0, 'Close']
    shares = init_invest / buy_price
    cash = 0
    total_invest = init_invest
    history_value = []

    add_points = []  # 补仓
    sell_points = []  # 止盈
    avg_list = []  # 每日均值

    for i in range(len(df)):
        price = df.loc[i, 'Close']

        # 计算前 window 个交易日均值
        if i < window:
            avg_price = df.loc[:i, 'Close'].mean()
        else:
            avg_price = df.loc[i-window+1:i, 'Close'].mean()
        avg_list.append(avg_price)

        value = shares * price + cash

        # 输出核对信息
        print(f"{df.loc[i, 'Date'].date()} 当前价={price:.2f}, {window}日均值={avg_price:.2f}, 当前市值={value:.2f}, 总投入={total_invest:.2f}")

        # 动态止跌
        if price <= avg_price * 0.95:
            target_value = shares * avg_price
            loss = max(target_value - value, 0)
            available_invest = max_invest - total_invest
            invest_amount = min(loss, available_invest, cash + loss)
            if invest_amount > 0:
                add_shares = invest_amount / price
                shares += add_shares
                total_invest += invest_amount
                cash -= max(0, invest_amount - loss)
                add_points.append((df.loc[i, 'Date'], price, avg_price, invest_amount))

        # 动态止盈
        elif price >= avg_price * 1.10:
            target_value = shares * avg_price
            profit = max(value - target_value, 0)
            if profit > 0:
                sell_shares = profit / price
                shares -= sell_shares
                cash += profit
                sell_points.append((df.loc[i, 'Date'], price, avg_price, profit))

        history_value.append(shares * price + cash)

    # 绘图
    plt.figure(figsize=(14,6))
    plt.plot(df['Date'], history_value, label="账户市值", color="blue")
    plt.plot(df['Date'], avg_list, label=f"{window}日均值", color="gray", linestyle='--')
    plt.axhline(total_invest, color='red', linestyle='--', label="本金")
    plt.axvline(pd.to_datetime(buy_date_str), color='green', linestyle=':', label="买入日")

    # 标记交易点
    if add_points:
        add_dates, add_prices, add_avgs, add_vals = zip(*add_points)
        plt.scatter(add_dates, add_vals, color='orange', label="补仓点", marker='^', s=100)
        for d, p, a in zip(add_dates, add_prices, add_avgs):
            plt.text(d, p, f"{p:.2f}/{a:.2f}", fontsize=8, color='orange', rotation=45)

    if sell_points:
        sell_dates, sell_prices, sell_avgs, sell_vals = zip(*sell_points)
        plt.scatter(sell_dates, sell_vals, color='purple', label="止盈点", marker='v', s=100)
        for d, p, a in zip(sell_dates, sell_prices, sell_avgs):
            plt.text(d, p, f"{p:.2f}/{a:.2f}", fontsize=8, color='purple', rotation=45)

    plt.xlabel("日期")
    plt.ylabel("市值 (元)")
    plt.title(f"{stock_code} 动态均值止盈/止跌策略回测（最大投入限制）")
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.7)
    plt.show()

    # 输出最终结果
    initial_capital = init_invest  # 初始本金
    final_value = shares * df.iloc[-1]['Close'] + cash
    profit = final_value - initial_capital
    profit_rate = profit / initial_capital * 100
    print(f"\n初始买入日: {buy_date_str}, 截止日: {end_date_str}")
    print(f"\n初始本金: {initial_capital:.2f}")
    print(f"期末总市值: {final_value:.2f}")
    print(f"总收益: {profit:.2f}, 收益率: {profit_rate:.2f}% (相对于初始本金)")

# 示例调用
simulate_avg_strategy_with_plot("000006", "2024-08-01", "2025-08-01", init_invest=10000, max_invest=50000, window=5)

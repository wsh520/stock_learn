import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt

def simulate_strategy_dynamic_max_correct(stock_code, buy_date_str, end_date_str,
                                          init_invest=10000, max_invest=50000, window=5,down_max_invest=0.2,up_max_invest=0.2):
    """
    动态均值止盈/止跌策略回测，收益基于期末市值减去当前投入本金
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
    shares = init_invest / df.loc[0, 'Close']
    cash = 0
    total_invest = init_invest
    current_max_invest = max_invest
    locked_shares = 0  # 补仓锁定股份
    history_value = []

    add_points = []
    sell_points = []
    avg_list = []

    for i in range(len(df)):
        price = df.loc[i, 'Close']

        # 前 window 日均值
        avg_price = df.loc[max(0, i-window+1):i, 'Close'].mean()
        avg_list.append(avg_price)

        value = shares * price + cash
        print(f"{df.loc[i, 'Date'].date()} 当前价={price:.2f}, {window}日均值={avg_price:.2f}, 市值={value:.2f}, 当前投入={total_invest:.2f}, max_invest可用={current_max_invest:.2f}")

        # 止跌补仓
        if price <= avg_price * down_max_invest:
            loss = max(shares * avg_price - value, 0)
            invest_amount = min(loss, current_max_invest)
            if invest_amount > 0:
                add_shares = invest_amount / price
                shares += add_shares
                locked_shares += add_shares
                total_invest += invest_amount
                current_max_invest -= invest_amount
                add_points.append((df.loc[i, 'Date'], price, avg_price, invest_amount, total_invest, current_max_invest))
                print(f"  → 止跌补仓: 补仓金额={invest_amount:.2f}, 当前价格={price:.2f}, 均值={avg_price:.2f}, 更新投入={total_invest:.2f}, max_invest可用={current_max_invest:.2f}")

        # 止盈卖出
        tradable_shares = shares - locked_shares
        if tradable_shares > 0 and price >= avg_price * up_max_invest:
            target_value = tradable_shares * avg_price
            profit = max(tradable_shares * price - target_value, 0)
            if profit > 0:
                sell_shares = profit / price
                sell_shares = min(sell_shares, tradable_shares)
                shares -= sell_shares
                cash += profit
                total_invest -= sell_shares * avg_price
                current_max_invest += profit
                sell_points.append((df.loc[i, 'Date'], price, avg_price, profit, total_invest, current_max_invest))
                print(f"  → 止盈卖出: 套现金额={profit:.2f}, 卖出股份={sell_shares:.4f}, 当前价格={price:.2f}, 均值={avg_price:.2f}, 更新投入={total_invest:.2f}, max_invest可用={current_max_invest:.2f}")

        history_value.append(shares * price + cash)

    # # 绘图
    # plt.figure(figsize=(14,6))
    # plt.plot(df['Date'], history_value, label="账户市值", color="blue")
    # plt.plot(df['Date'], avg_list, label=f"{window}日均值", color="gray", linestyle='--')
    # plt.axhline(init_invest, color='red', linestyle='--', label="初始本金")
    # plt.axvline(pd.to_datetime(buy_date_str), color='green', linestyle=':', label="买入日")
    #
    # if add_points:
    #     add_dates, add_prices, add_avgs, add_vals, add_total, add_max = zip(*add_points)
    #     plt.scatter(add_dates, add_vals, color='orange', label="补仓点", marker='^', s=100)
    # if sell_points:
    #     sell_dates, sell_prices, sell_avgs, sell_vals, sell_total, sell_max = zip(*sell_points)
    #     plt.scatter(sell_dates, sell_vals, color='purple', label="止盈点", marker='v', s=100)
    #
    # plt.xlabel("日期")
    # plt.ylabel("账户市值 (元)")
    # plt.title(f"{stock_code} 动态均值止盈/止跌策略回测（动态投入本金+动态max_invest）")
    # plt.legend()
    # plt.grid(True, linestyle=':', alpha=0.7)
    # plt.show()

    # 修正收益计算
    final_value = shares * df.iloc[-1]['Close'] + cash
    total_profit = final_value - total_invest  # 以当前投入为基准
    profit_rate = total_profit / total_invest * 100
    print(f"\n当前投入本金: {total_invest:.2f}")
    print(f"期末总市值: {final_value:.2f}")
    print(f"总收益: {total_profit:.2f}, 收益率: {profit_rate:.2f}%")

# 示例调用
simulate_strategy_dynamic_max_correct("601318", "2024-08-01", "2025-08-01",
                                      init_invest=10000, max_invest=50000, window=5, down_max_invest=0.95, up_max_invest=1.15)

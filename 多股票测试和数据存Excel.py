import akshare as ak
import pandas as pd


def simulate_strategy_dynamic_max_correct(stock_code, buy_date_str, end_date_str,
                                          init_invest=10000, max_invest=50000,
                                          window=5, down_factor=0.95, up_factor=1.15):
    """
    单个股票的动态均值止盈/止跌策略回测，返回交易明细 DataFrame.

    参数:
        stock_code (str): 股票代码.
        buy_date_str (str): 策略回测开始日期, 格式 'YYYY-MM-DD'.
        end_date_str (str): 策略回测结束日期, 格式 'YYYY-MM-DD'.
        init_invest (float): 初始投资金额.
        max_invest (float): 最大总投入本金限制.
        window (int): 计算均值的窗口天数.
        down_factor (float): 止跌因子, 当收盘价 <= 均值 * down_factor 时补仓.
        up_factor (float): 止盈因子, 当收盘价 >= 均值 * up_factor 时卖出.

    返回:
        pd.DataFrame: 包含交易明细和账户状态的DataFrame.
    """
    # 获取历史数据
    try:
        df = ak.stock_zh_a_hist(
            symbol=stock_code,
            period="daily",
            start_date=buy_date_str.replace("-", ""),
            end_date=end_date_str.replace("-", ""),
            adjust="qfq"
        )
    except Exception as e:
        print(f"{stock_code}: 获取数据失败 - {e}")
        return pd.DataFrame()

    if df.empty:
        print(f"{stock_code}: 未获取到数据")
        return pd.DataFrame()

    df = df[['日期', '收盘']].copy()
    df.rename(columns={'日期': 'Date', '收盘': 'Close'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df.sort_values('Date', inplace=True)

    start_date = pd.to_datetime(buy_date_str)
    end_date = pd.to_datetime(end_date_str)

    df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)].reset_index(drop=True)
    if df.empty:
        print(f"{stock_code}: 买入日不在交易日范围内")
        return pd.DataFrame()

    # 初始化账户状态
    shares = 0.0
    cash = init_invest
    total_invested_principal = 0.0

    records = []

    for i in range(len(df)):
        date = df.loc[i, 'Date']
        price = df.loc[i, 'Close']

        # 计算均价
        if i >= window - 1:
            avg_price = df.loc[i - window + 1:i, 'Close'].mean()
        else:
            avg_price = price  # 或其他策略，这里简化处理

        action = ""
        detail = ""

        # 初始买入
        if i == 0:
            buy_shares = cash / price
            shares += buy_shares
            total_invested_principal += cash
            cash = 0
            action = "初始买入"
            detail = f"买入={buy_shares:.2f}股"

        # 动态均值止跌补仓
        elif price <= avg_price * down_factor and total_invested_principal < max_invest:
            # 简单计算补仓金额，可以调整为更复杂的策略
            add_invest_amount = (max_invest - total_invested_principal) / 10  # 每次最多补仓剩余最大投资额的10%
            if add_invest_amount > 0:
                add_shares = add_invest_amount / price
                shares += add_shares
                total_invested_principal += add_invest_amount
                action = "止跌补仓"
                detail = f"补仓={add_invest_amount:.2f}"

        # 动态均值止盈卖出
        elif price >= avg_price * up_factor and shares > 0:
            # 卖出部分股份以实现盈利
            sell_ratio = 0.5  # 卖出持仓的50%
            sell_shares = shares * sell_ratio
            if sell_shares > 0:
                sell_value = sell_shares * price
                cash += sell_value
                shares -= sell_shares

                # 调整已投入本金，以反映卖出
                avg_cost = total_invested_principal / (shares + sell_shares)
                total_invested_principal = shares * avg_cost

                action = "止盈卖出"
                detail = f"卖出={sell_shares:.2f}股"

        current_value = shares * price + cash

        records.append({
            "日期": date,
            "收盘价": price,
            f"{window}日均值": avg_price,
            "操作": action,
            "详情": detail,
            "投入本金": total_invested_principal,
            "股票市值": shares * price,
            "账户现金": cash,
            "账户总市值": current_value
        })

    # 期末统计
    final_value = shares * df.iloc[-1]['Close'] + cash
    total_profit = final_value - init_invest
    profit_rate = total_profit / init_invest * 100 if init_invest > 0 else 0

    records.append({
        "日期": df.iloc[-1]['Date'],
        "收盘价": df.iloc[-1]['Close'],
        f"{window}日均值": avg_price,
        "操作": "期末统计",
        "详情": f"总收益={total_profit:.2f}, 收益率={profit_rate:.2f}%",
        "投入本金": total_invested_principal,
        "股票市值": shares * df.iloc[-1]['Close'],
        "账户现金": cash,
        "账户总市值": final_value
    })

    return pd.DataFrame(records)


def simulate_multiple_stocks_to_excel(stock_codes, buy_date_str, end_date_str, filename="回测结果.xlsx",
                                      init_invest=10000, max_invest=50000, window=5, down_factor=0.95, up_factor=1.15):
    """
    多股票回测，并写入 Excel，不同股票一个 sheet
    """
    with pd.ExcelWriter(filename, engine="openpyxl") as writer:
        for code in stock_codes:
            df = simulate_strategy_dynamic_max_correct(
                stock_code=code,
                buy_date_str=buy_date_str,
                end_date_str=end_date_str,
                init_invest=init_invest,
                max_invest=max_invest,
                window=window,
                down_factor=down_factor,
                up_factor=up_factor
            )
            if not df.empty:
                df.to_excel(writer, sheet_name=code, index=False)
                print(f"{code} 已写入 Excel")
    print(f"\n所有股票结果已保存到 {filename}")


# 示例调用
simulate_multiple_stocks_to_excel(
    stock_codes=["600104", "000063", "601127", "300750", "002982", "000559", "300251", "002466", "000895", "600585"],
    buy_date_str="2024-08-01",
    end_date_str="2025-08-01",
    filename="stocks_backtest_revised.xlsx",
    init_invest=10000,
    max_invest=50000,
    window=10,
    down_factor=0.95,
    up_factor=1.15
)
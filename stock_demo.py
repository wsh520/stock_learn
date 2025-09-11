import akshare as ak
import pandas as pd
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
from datetime import timedelta

print("正在获取中国平安（601318）2025年8月的历史股价数据，请稍候...")
try:
    # 1) 获取全量日线（注意上交所用 sh 前缀）
    stock_data = ak.stock_zh_a_daily(symbol="sh601318")

    # 2) 将索引还原为列；兼容不同版本的索引名
    stock_data = stock_data.reset_index()
    # 通常索引名为 'date'，若为 'index' 也一并兼容
    if "date" in stock_data.columns:
        stock_data.rename(columns={"date": "trade_date"}, inplace=True)
    elif "index" in stock_data.columns:
        stock_data.rename(columns={"index": "trade_date"}, inplace=True)
    else:
        raise ValueError("未发现日期列（既非 'date' 也非 'index'）。")

    # 3) **先统一日期类型**：避免 datetime.date 与 str 比较
    stock_data["trade_date"] = pd.to_datetime(stock_data["trade_date"])

    # 4) 用 pd.Timestamp 进行区间过滤（放在转换之后）
    start = pd.Timestamp("2025-08-01")
    end = pd.Timestamp("2025-08-31")
    stock_data = stock_data[(stock_data["trade_date"] >= start) & (stock_data["trade_date"] <= end)]

    if stock_data.empty:
        print("未获取到中国平安在指定日期范围内的历史股价数据。请检查股票代码或日期。")
    else:
        print("\n成功获取历史股价数据，前5行预览：")
        print(stock_data.head())

        # 5) 特征：交易日序号，避免跨年问题
        stock_data = stock_data.sort_values("trade_date").reset_index(drop=True)
        stock_data["day_index"] = range(len(stock_data))

        X = stock_data[["day_index"]].values
        y = stock_data["close"].values

        # 6) 训练线性回归
        print("\n正在训练线性回归模型...")
        model = LinearRegression()
        model.fit(X, y)
        print("模型训练完成。")

        # 7) 预测未来 30 个“交易日”（工作日近似）
        last_historical_date = stock_data["trade_date"].max()
        last_index = stock_data["day_index"].max()

        future_dates = pd.bdate_range(start=last_historical_date + timedelta(days=1), periods=30)
        future_day_index = [[last_index + i + 1] for i in range(len(future_dates))]
        future_predictions = model.predict(future_day_index)
        print(f"\n已预测未来 {len(future_dates)} 个交易日的股价。")

        # 8) 可视化
        plt.figure(figsize=(14, 7))
        plt.plot(stock_data["trade_date"], stock_data["close"], label="历史股价", color='blue', marker='o', markersize=4)
        plt.plot(future_dates, future_predictions, label="预测股价", linestyle="--", color='red', marker='x', markersize=6)

        # 简单预测区间（±2% 视觉带）
        plt.fill_between(future_dates,
                         future_predictions * 0.98,
                         future_predictions * 1.02,
                         color="red", alpha=0.1, label="预测区间")

        plt.xlabel("日期")
        plt.ylabel("收盘价")
        plt.title("中国平安股价预测 (基于线性回归)")
        plt.legend()
        plt.grid(True, linestyle=':', alpha=0.7)
        plt.tight_layout()
        plt.show()

        print("\n股价预测图已生成并显示（或准备在本地Python环境中显示）。")

except Exception as e:
    print(f"在获取数据、训练模型或绘图过程中发生错误: {e}")

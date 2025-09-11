import akshare as ak
import pandas as pd

# 获取东方财富-股票中心-A股板块的实时行情数据
# 数据源: https://quote.eastmoney.com/center/gridlist.html#hs_a_board
print("正在获取东方财富网A股实时行情数据，请稍候...")
try:
    # 调用 ak.stock_zh_a_spot_em() 函数获取数据
    # 这个函数直接对应了你提供的网页数据源
    df_stock_zh_a_spot_em = ak.stock_zh_a_spot_em()
    
    if not df_stock_zh_a_spot_em.empty:
        # 筛选出中国平安的股价信息
        # 假设“名称”列包含股票名称
        df_pingan = df_stock_zh_a_spot_em[df_stock_zh_a_spot_em['名称'] == '中国平安']

        if not df_pingan.empty:
            print("\n成功获取并筛选出中国平安的数据！部分数据预览：")
            print(df_pingan.head())

            # 将中国平安的数据保存到Excel文件
            file_name = "中国平安_实时行情.xlsx"
            df_pingan.to_excel(file_name, index=False)
            print(f"\n中国平安的实时行情数据已保存到文件: {file_name}")
        else:
            print("未在获取的数据中找到 '中国平安' 的信息。")
    else:
        print("从东方财富网获取的数据为空。")

except Exception as e:
    print(f"获取数据时发生错误: {e}")


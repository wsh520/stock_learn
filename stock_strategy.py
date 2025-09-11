import pandas as pd
import akshare as ak
import numpy as np
from datetime import datetime, timedelta
import time
from functools import lru_cache
import os
import json

# 新增: 列处理与列名适配工具函数
# -------------------------------------------------

def safe_float(val):
    """安全转换为 float, 非标量或无法转换返回 np.nan"""
    try:
        if isinstance(val, (list, tuple, dict, set)):
            return np.nan
        return float(val)
    except Exception:
        return np.nan

def drop_duplicate_columns(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    return df.loc[:, ~df.columns.duplicated()]

def pick_col(df: pd.DataFrame, candidates, alias=None):
    """宽松列名匹配"""
    if df is None or df.empty:
        return None
    cols = list(df.columns)
    for c in candidates:
        if c in cols:
            return c
    # 去除可能 BOM 或不可见字符
    cleaned_map = {col.replace('\ufeff','').replace('\u200b',''): col for col in cols}
    for c in candidates:
        if c in cleaned_map:
            return cleaned_map[c]
    # 部分包含匹配
    for col in cols:
        for c in candidates:
            if c in col:
                return col
    if alias:
        print(f"缺少列: {alias} (候选: {candidates})")
    return None

# ================== 新增函数: 财务指标与风险控制动态调参 ==================
@lru_cache(maxsize=512)
def get_fundamental_indicator(symbol: str):
    cfg = CONFIG.get('fundamental', {})
    if not cfg.get('enabled', False):
        return {"roe": np.nan, "net_margin": np.nan}
    try:
        df = ak.stock_financial_analysis_indicator(symbol=symbol)
    except Exception:
        return {"roe": np.nan, "net_margin": np.nan}
    if df is None or df.empty:
        return {"roe": np.nan, "net_margin": np.nan}
    if '日期' in df.columns:
        df = df.sort_values('日期')
    row = df.iloc[-1]
    def pick_val(cands):
        for c in cands:
            if c in df.columns and not pd.isna(row[c]):
                return safe_float(row[c])
        return np.nan
    roe = pick_val(['净资产收益率加权(%)','净资产收益率(%)','ROE加权(%)','ROE(%)','净资产收益率-加权(%)'])
    net_margin = pick_val(['销售净利率(%)','净利率(%)','销售净利率','净利率'])
    return {"roe": roe, "net_margin": net_margin}

def apply_risk_control_dynamic(adj_filter: dict, index_hist: pd.DataFrame):
    rc = CONFIG.get('risk_control', {})
    if not rc.get('enabled') or index_hist is None or index_hist.empty:
        return
    ma_days = CONFIG['market_timing']['ma_days']
    ma_col = f'MA{ma_days}'
    if ma_col not in index_hist.columns:
        index_hist[ma_col] = index_hist['收盘'].rolling(window=ma_days).mean()
    if len(index_hist) < ma_days:
        return
    ma_val = index_hist[ma_col].iloc[-1]
    close_val = index_hist['收盘'].iloc[-1]
    if pd.isna(ma_val) or ma_val == 0:
        return
    deviation = (close_val - ma_val) / ma_val
    if rc.get('log'):
        print(f"风险控制: 指数对MA{ma_days}乖离 {deviation*100:.2f}%")
    # 过热
    if deviation >= rc.get('overheat_deviation', 0.06):
        old_max = adj_filter['change_rate_max']
        old_turn = adj_filter['turnover_rate_max']
        adj_filter['change_rate_max'] = round(old_max * rc.get('overheat_change_max_factor', 0.8), 2)
        adj_filter['turnover_rate_max'] = round(old_turn * rc.get('overheat_turnover_max_factor', 0.85), 2)
        if rc.get('log'):
            print(f"  * 过热: 涨幅上限 {old_max}->{adj_filter['change_rate_max']} 换手上限 {old_turn}->{adj_filter['turnover_rate_max']}")
    # 偏弱
    elif deviation <= rc.get('weak_deviation', -0.03):
        if rc.get('weak_abort'):
            adj_filter['__abort__'] = True
            if rc.get('log'): print("  * 偏弱: 终止触发")
        else:
            old_min = adj_filter['change_rate_min']
            adj_filter['change_rate_min'] = round(old_min * rc.get('weak_change_min_factor', 0.7), 2)
            if rc.get('log'):
                print(f"  * 偏弱: 涨幅下限 {old_min}->{adj_filter['change_rate_min']}")

# ==============================================================================
# 策略配置文件
# ==============================================================================
CONFIG = {
    # 1. 大盘择时配置
    "market_timing": {
        "enabled": True,
        "index_code": "sh000001",
        "ma_days": 60,
        "max_retry": 3,
        "retry_delay": 1,
        "secondary_index_code": None,
        "secondary_enabled": False,
        "secondary_logic": "or"
    },
    # 新增: 风险控制配置（指数乖离动态调参）
    "risk_control": {
        "enabled": True,
        "overheat_deviation": 0.06,      # 指数 > MA60 超过 6% 视为过热
        "overheat_change_max_factor": 0.8,  # 降低涨幅上限系数
        "overheat_turnover_max_factor": 0.85,
        "weak_deviation": -0.03,         # 指数 < MA60 跌破 3% 视为偏弱
        "weak_abort": False,             # 若偏弱是否直接终止
        "weak_change_min_factor": 0.7,   # 偏弱时下调涨幅下限
        "log": True
    },
    # 2. 行业板块配置
    "sector": {
        "enabled": True,
        "top_n": 5,
        "debug": True  # 打印行业原始列名
    },
    # 3. 筛选参数
    "filter": {
        "change_rate_min": 2.0,   # 原3.0 -> 2.0 放宽初始涨幅下限
        "change_rate_max": 7.0,
        "volume_ratio_min": 1.0,
        "turnover_rate_min": 5.0,
        "turnover_rate_max": 15.0,
        "market_cap_min": 50 * 10 ** 8,
        "market_cap_max": 200 * 10 ** 8,
        "intraday_strength_min": 0.55  # 新增: 日内强度 (靠近高位)
    },
    # 4. 技术指标参数
    "technique": {
        "ma_list": [5, 10, 20, 60],
        "volume_step_days": 5,
        "volume_breakout_days": 20,
        "volume_breakout_ratio": 1.3,  # 原1.5 -> 1.3 放宽放量倍数
        "rs_days": 5,                   # 原10 -> 5 缩短相对强度窗口
        "atr_days": 14,
        "max_atr_pct": 9.5,             # 原8.0 -> 9.5 放宽波动率上限
        "atr_soft_margin": 1.15,
        "use_wilder_atr": True
    },
    # 5. 股票池
    "universe": {
        "hs300_only": False,
        "hs300": False,
        "zz500": False,
        "combine_mode": "union",
        "sh_main_only": True,
        "exclude_star": True,
        "exclude_chinext": True
    },
    # 6. 扩展指标配置
    "enhanced_metrics": {
        "limit_up_lookback": 30,      # 近30日涨停统计窗口
        "limit_up_threshold": 9.5,    # 判定阈值(%)，过滤已排除 ST，可用 9.5 近似 10%涨停
        "vol_contraction_recent": 5,  # 近期窗口
        "vol_contraction_prev": 10,   # 对比的前期窗口
        "enable_vol_contraction": True,
        "fund_flow_candidates": ["主力净流入-净额","主力净流入","主力资金净流入","主力净额"],
    },
    # 7. 基本面过滤配置
    "fundamental": {
        "enabled": True,
        "min_roe": 8.0,          # ROE 下限(%)
        "min_net_margin": 5.0,   # 净利率下限(%)
        "cache_days": 3
    }
}


# ==============================================================================
# 辅助函数
# ==============================================================================

def check_trading_time():
    """检查当前是否为交易日下午14:30之后"""
    now = datetime.now()
    if now.weekday() >= 5:
        print("周末非交易日，程序退出。")
        return False
    return True


def get_hist_data(symbol, days=100):
    """获取历史数据并缓存"""
    end_date = datetime.now().strftime('%Y%m%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
    
    # 增加重试机制
    max_retry = CONFIG["market_timing"].get("max_retry", 3)
    retry_delay = CONFIG["market_timing"].get("retry_delay", 1)
    
    for attempt in range(max_retry):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
            # 增加数据验证
            if not df.empty and len(df) > 0:
                return df
            else:
                print(f"获取 {symbol} 历史数据返回空数据 (尝试 {attempt+1}/{max_retry})")
        except Exception as e:
            print(f"获取 {symbol} 历史数据失败 (尝试 {attempt+1}/{max_retry}): {e}")
            if attempt < max_retry - 1:  # 不是最后一次尝试
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
            else:
                print(f"已达最大重试次数，获取 {symbol} 数据失败")

    return pd.DataFrame()


def calculate_atr(df_hist, n, wilder=False):
    """计算 ATR (可选 Wilder 平滑)"""
    high_low = df_hist['最高'] - df_hist['最低']
    high_prev_close = (df_hist['最高'] - df_hist['收盘'].shift(1)).abs()
    low_prev_close = (df_hist['最低'] - df_hist['收盘'].shift(1)).abs()
    tr = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    if not wilder:
        return tr.rolling(window=n).mean()
    atr = tr.copy()
    atr.iloc[0:n] = tr.iloc[0:n].rolling(window=n).mean()  # 初始化
    for i in range(n, len(tr)):
        atr.iloc[i] = (atr.iloc[i-1] * (n - 1) + tr.iloc[i]) / n
    return atr


def is_stair_step_volume(df_hist, n):
    """检查成交量是否“台阶式放大”"""
    if len(df_hist) < n + 1:
        return False
    recent_volumes = df_hist['成交量'].tail(n + 1)
    if recent_volumes.isna().any():
        return False
    vol_ma2 = recent_volumes.rolling(window=2).mean().dropna()
    return all(vol_ma2.iloc[i] > vol_ma2.iloc[i - 1] for i in range(1, len(vol_ma2)))


# ==============================================================================
# 核心逻辑模块
# ==============================================================================

@lru_cache(maxsize=8)
def get_index_hist_data(index_code: str, days: int = 160) -> pd.DataFrame:
    """获取指数历史数据，增加多种代码形��与备用接口尝试。
    优先: stock_zh_index_daily(symbol) 依次尝试 原码 / 去前缀 / 仅数字。
    备用: index_zh_a_hist(symbol_without_prefix)
    统一输出列: 开盘 最高 最低 收盘 成交量
    """
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)
    max_retry = CONFIG["market_timing"].get("max_retry", 3)
    retry_delay = CONFIG["market_timing"].get("retry_delay", 1)

    candidates = []
    if index_code:
        candidates.append(index_code)
        if index_code.startswith(('sh', 'sz')):
            pure = index_code[2:]
            candidates.append(pure)
        stripped = index_code.replace('sh', '').replace('sz', '')
        if stripped not in candidates:
            candidates.append(stripped)
    tried_msgs = []

    def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        rename_map = {
            'open': '开盘', 'high': '最高', 'low': '最低', 'close': '收盘', 'volume': '成交量',
            '日期': 'date', 'date': 'date'
        }
        for k, v in rename_map.items():
            if k in df.columns:
                df.rename(columns={k: v}, inplace=True)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        required = ['开盘', '最高', '最低', '收盘']
        if not all(c in df.columns for c in required):
            return pd.DataFrame()
        if '成交量' not in df.columns:
            df['成交量'] = np.nan
        return df.reset_index(drop=True)

    # 主接口多次+多代码尝试
    for attempt in range(max_retry):
        for symbol_try in candidates:
            try:
                df_main = ak.stock_zh_index_daily(symbol=symbol_try)
                nd = normalize_df(df_main)
                if not nd.empty:
                    return nd
                tried_msgs.append(f"主接口空 symbol={symbol_try} attempt={attempt+1}")
            except Exception as e:
                tried_msgs.append(f"主接口异常 symbol={symbol_try} attempt={attempt+1} err={e}")
        if attempt < max_retry - 1:
            time.sleep(retry_delay)

    # 备用接口（只用无前缀数字）
    backup_symbol = None
    for c in candidates:
        if c.isdigit():
            backup_symbol = c
            break
    if backup_symbol:
        for attempt in range(max_retry):
            try:
                df_bk = ak.index_zh_a_hist(symbol=backup_symbol)
                nd = normalize_df(df_bk)
                if not nd.empty:
                    return nd
                tried_msgs.append(f"备用接口空 symbol={backup_symbol} attempt={attempt+1}")
            except Exception as e:
                tried_msgs.append(f"备用接口异常 symbol={backup_symbol} attempt={attempt+1} err={e}")
            if attempt < max_retry - 1:
                time.sleep(retry_delay)

    print("指数数据获取失败日志:")
    for m in tried_msgs[-10:]:  # 只打印最近10条避免过长
        print("  ", m)
    return pd.DataFrame()


@lru_cache(maxsize=1)
def get_hs300_constituents(force_refresh: bool = False) -> set:
    """获取沪深300成分股代码集合（6位数字）
    策略：
      1. 若��在当日缓存且未强制刷新 -> 直接读取
      2. 多符号、多接口依次尝试
         a) index_stock_cons(symbol=符号候选)
         b) index_zh_index_weight_csindex(symbol="000300", 最近一段时间)
      3. 成功后写入缓存
    返回: set[str]
    """
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, 'hs300_constituents.json')
    today = datetime.now().strftime('%Y-%m-%d')

    # 读取缓存
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today and isinstance(data.get('codes'), list) and data['codes']:
                return set(data['codes'])
        except Exception:
            pass  # 忽略缓存读取���误

    def normalize_codes(df: pd.DataFrame, possible_cols) -> set:
        if df is None or df.empty:
            return set()
        for col in possible_cols:
            if col in df.columns:
                series = df[col].astype(str)
                codes = series.str.extract(r'(\d{6})')[0].dropna().unique().tolist()
                return set(codes)
        return set()

    candidates = ["沪深300", "000300", "399300", "sh000300", "sz399300"]
    max_retry = CONFIG['market_timing'].get('max_retry', 3)
    retry_delay = CONFIG['market_timing'].get('retry_delay', 1)
    collected = set()
    errors = []

    # 尝试主接口 index_stock_cons
    for attempt in range(max_retry):
        for sym in candidates:
            try:
                df = ak.index_stock_cons(symbol=sym)
                codes = normalize_codes(df, ['代码', '品种代码', '证券代码', 'ticker', 'symbol'])
                if codes:
                    collected |= codes
            except Exception as e:
                errors.append(f"index_stock_cons sym={sym} attempt={attempt+1} err={e}")
        if collected:
            break
        if attempt < max_retry - 1:
            time.sleep(retry_delay)

    # 备用接口：中证指数权重 (需要时间区间)
    if not collected:
        try:
            start = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            end = datetime.now().strftime('%Y%m%d')
            weight_func = getattr(ak, 'index_zh_index_weight_csindex', None)
            if callable(weight_func):
                wdf = weight_func(symbol="000300", start_date=start, end_date=end)
                if isinstance(wdf, pd.DataFrame) and not wdf.empty:
                    codes = normalize_codes(wdf, ['成分券代码Constituent Code', '代码'])
                    if codes:
                        collected |= codes
                else:
                    errors.append("index_zh_index_weight_csindex 返回异常类型或空数据")
            else:
                errors.append("index_zh_index_weight_csindex 函数不可用")
        except Exception as e:
            errors.append(f"index_zh_index_weight_csindex err={e}")

    # 缓存结果
    if collected:
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'date': today, 'codes': sorted(list(collected))}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入缓存失败: {e}")
        return collected

    # 输出错误信息（保留最近几条）
    if errors:
        print("获取沪深300成分股异常详情(截取):")
        for line in errors[-8:]:
            print("  ", line)
    print("获取沪深300成分股失败，返回空集合")
    return set()


@lru_cache(maxsize=1)
def get_zz500_constituents(force_refresh: bool = False) -> set:
    """获取中证500(000905)成分股集合，逻辑同沪深300。
    缓存文件: cache/zz500_constituents.json
    """
    cache_dir = os.path.join(os.path.dirname(__file__), 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, 'zz500_constituents.json')
    today = datetime.now().strftime('%Y-%m-%d')
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('date') == today and data.get('codes'):
                return set(data['codes'])
        except Exception:
            pass
    def normalize_codes(df: pd.DataFrame, cols) -> set:
        if df is None or df.empty: return set()
        for c in cols:
            if c in df.columns:
                return set(df[c].astype(str).str.extract(r'(\d{6})')[0].dropna().unique().tolist())
        return set()
    candidates = ["中证500", "000905", "399905", "sh000905", "sz399905"]
    max_retry = CONFIG['market_timing'].get('max_retry', 3)
    retry_delay = CONFIG['market_timing'].get('retry_delay', 1)
    collected = set(); errors = []
    for attempt in range(max_retry):
        for sym in candidates:
            try:
                df = ak.index_stock_cons(symbol=sym)
                codes = normalize_codes(df, ['代码', '品种代码', '证券代码', 'ticker', 'symbol'])
                if codes:
                    collected |= codes
            except Exception as e:
                errors.append(f"zz500 index_stock_cons sym={sym} attempt={attempt+1} err={e}")
        if collected: break
        if attempt < max_retry - 1: time.sleep(retry_delay)
    if not collected:
        try:
            start = (datetime.now() - timedelta(days=10)).strftime('%Y%m%d')
            end = datetime.now().strftime('%Y%m%d')
            weight_func = getattr(ak, 'index_zh_index_weight_csindex', None)
            if callable(weight_func):
                wdf = weight_func(symbol="000905", start_date=start, end_date=end)
                if isinstance(wdf, pd.DataFrame) and not wdf.empty:
                    codes = normalize_codes(wdf, ['成分券代码Constituent Code', '代码'])
                    if codes: collected |= codes
                else:
                    errors.append("index_zh_index_weight_csindex 返回异常类型或空数据")
            else:
                errors.append("index_zh_index_weight_csindex 函数不可用")
        except Exception as e:
            errors.append(f"zz500 weight err={e}")
    if collected:
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({'date': today, 'codes': sorted(list(collected))}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"写入zz500缓存失败: {e}")
        return collected
    if errors:
        print("获取中证500成分异常详情(截取):")
        for line in errors[-8:]:
            print("  ", line)
    print("获取中证500成分股失败，返回空集合")
    return set()


def check_market_regime():
    """扩展：支持次级指数择时逻辑 (secondary_logic)"""
    if not CONFIG["market_timing"]["enabled"]:
        print("大盘择时模块已禁用。")
        return True
    print("开始进行大盘择时分析...")
    primary_code = CONFIG["market_timing"]["index_code"]
    ma_days = CONFIG["market_timing"]["ma_days"]
    p_hist = get_index_hist_data(primary_code, days=max(160, ma_days + 20))
    def healthy(hist):
        if hist.empty or len(hist) < ma_days: return False
        ma_col = f'MA{ma_days}'
        if ma_col not in hist.columns:
            hist[ma_col] = hist['收盘'].rolling(window=ma_days).mean()
        return hist['收盘'].iloc[-1] > hist[ma_col].iloc[-1]
    p_ok = healthy(p_hist)
    if p_ok:
        print(f"主指数健康: {primary_code} 收盘({p_hist['收盘'].iloc[-1]:.2f}) > MA{ma_days}({p_hist[f'MA{ma_days}'].iloc[-1]:.2f})")
    else:
        print(f"主指数弱势: {primary_code} 收盘或MA数据不足")
    sec_logic = True
    if CONFIG['market_timing'].get('secondary_enabled'):
        sec_code = CONFIG['market_timing'].get('secondary_index_code')
        s_hist = get_index_hist_data(sec_code, days=max(160, ma_days + 20))
        s_ok = healthy(s_hist)
        if s_ok:
            print(f"次级指数健康: {sec_code} 收盘({s_hist['收盘'].iloc[-1]:.2f}) > MA{ma_days}({s_hist[f'MA{ma_days}'].iloc[-1]:.2f})")
        else:
            print(f"次级指数弱势: {sec_code} 收盘或MA数据不足")
        logic = CONFIG['market_timing'].get('secondary_logic', 'or')
        if logic == 'and':
            sec_logic = p_ok and s_ok
        else:  # default or
            sec_logic = p_ok or s_ok
        print(f"择时判定(模式={logic}) => {sec_logic}")
    else:
        sec_logic = p_ok
    if not sec_logic:
        print("择时不通过，策略停止执行。")
    return sec_logic


def get_strong_sectors():
    """获取强势行业板块及其成分股(自适应列名)"""
    if not CONFIG["sector"]["enabled"]:
        print("强势行业过滤已禁用。")
        return None, None
    print("正在获取强势行业板块...")
    try:
        sector_spot_df = ak.stock_board_industry_spot_em()
        if sector_spot_df is None or sector_spot_df.empty:
            print("行业数据为空")
            return None, None
        # 若接口仅返回占位列
        if set(sector_spot_df.columns) <= {"item","value"}:
            print("行业接口返回占位数据，跳过行业过滤。")
            return None, None
        if CONFIG['sector'].get('debug'):
            print("行业原始列:", list(sector_spot_df.columns))
        sector_spot_df = drop_duplicate_columns(sector_spot_df)
        # 可能列名集合
        name_col = pick_col(sector_spot_df, ['板块名称','名称','行业名称'], '板块名称')
        avg_col = pick_col(sector_spot_df, ['平均涨跌幅','平均涨跌幅(%)','涨跌幅','涨跌幅(%)','涨幅'], '平均涨跌幅')
        code_col = pick_col(sector_spot_df, ['板块代码','代码','行业代码'], '板块代码')
        if not (name_col and avg_col and code_col):
            print("行业列名匹配失败，跳过行业过滤。")
            return None, None
        # 统一重命名便于后续处理
        sector_spot_df = sector_spot_df.rename(columns={name_col:'板块名称', avg_col:'平均涨跌幅', code_col:'板块代码'})
        # 排序
        top_sectors = sector_spot_df.sort_values('平均涨跌幅', ascending=False).head(CONFIG["sector"]["top_n"])
        strong_stocks = set(); stock_to_sector = {}
        print("\n当日强势板块 Top", CONFIG["sector"]["top_n"], ":")
        for _, row in top_sectors.iterrows():
            sector_name = row['板块名称']
            sector_code = str(row['板块代码'])
            print(f"  - {sector_name} (平均涨幅: {row['平均涨跌幅']:.2f}%)")
            try:
                cons_df = ak.stock_board_industry_cons_em(symbol=sector_code)
                if cons_df is None or cons_df.empty:
                    continue
                cons_df = drop_duplicate_columns(cons_df)
                code_c = pick_col(cons_df, ['代码','证券代码','股票代码'], '成分代码')
                if not code_c:
                    continue
                for sc in cons_df[code_c].astype(str):
                    strong_stocks.add(sc)
                    stock_to_sector[sc] = sector_name
            except Exception as e:
                print(f"    * 成分获取失败 {sector_code}: {e}")
            time.sleep(0.25)
        if not strong_stocks:
            print("未获取到成分股，行业过滤失效。")
            return None, None
        print(f"\n共找到 {len(strong_stocks)} 只强势板块成分股。")
        return strong_stocks, stock_to_sector
    except Exception as e:
        print(f"获取强势行业失败: {e}，将不进行行业过滤。")
        return None, None


def build_universe():
    """根据配置构建股票池��合与指数归属映������此处若仅需上证主板则直接全市场上证主板集合(从实时行情获取时再截取)。"""
    uconf = CONFIG['universe']
    # 如果只需要上证主板，不依赖指数成分
    if uconf.get('sh_main_only'):
        return set(), {}  # 返回空集合占位，后续在���情阶段用代码规则筛
    # 旧逻辑保留（当前已关闭）
    if uconf.get('hs300_only'):
        hs = get_hs300_constituents()
        membership = {c: ['HS300'] for c in hs}
        return hs, membership
    candidate = set(); membership = {}
    # 若启用仍可扩展
    if uconf.get('hs300'):
        hs = get_hs300_constituents()
        for c in hs:
            candidate.add(c); membership.setdefault(c, []).append('HS300')
    if uconf.get('zz500'):
        zz = get_zz500_constituents()
        for c in zz:
            candidate.add(c); membership.setdefault(c, []).append('ZZ500')
    return candidate, membership


def run_stock_screener():
    print("\n开始执行选股���略...")
    universe_set, membership_map = build_universe()
    uconf = CONFIG['universe']
    print("正在获取所有A股实时行情并进行初步筛选...")
    stock_spot_df = ak.stock_zh_a_spot_em()
    if stock_spot_df is None or stock_spot_df.empty:
        print("实时行情获取失败。")
        return
    stock_spot_df = drop_duplicate_columns(stock_spot_df)
    # 动态识别关键列
    col_change = pick_col(stock_spot_df, ['涨跌幅','涨跌幅(%)','涨幅'], '涨跌幅')
    col_volume_ratio = pick_col(stock_spot_df, ['量比','量比(%)'], '量比')
    col_turnover = pick_col(stock_spot_df, ['换手率','换手率(%)'], '换手率')
    col_mv = pick_col(stock_spot_df, ['流通市值','流通市值(元)','市值','总市值'], '流通市值')
    col_amount = pick_col(stock_spot_df, ['成交额','成交额(元)'], '成交额')
    col_volume = pick_col(stock_spot_df, ['成交量','成交量(手)'], '成交量')
    col_price = pick_col(stock_spot_df, ['最新价','现价','收盘价'], '最新价')
    col_high = pick_col(stock_spot_df, ['最高','当日最高','最高价'], '最高')
    col_low = pick_col(stock_spot_df, ['最低','当日最低','最低价'], '最低')
    # 新增主力资金列
    col_fund_flow = pick_col(stock_spot_df, CONFIG['enhanced_metrics']['fund_flow_candidates'], '主力净流入')
    if not all([col_change,col_volume_ratio,col_turnover,col_mv,col_amount,col_volume,col_price]):
        print("行情列名缺失，无法继续。")
        return
    # 仅上证主板过滤
    if uconf.get('sh_main_only'):
        mask = stock_spot_df['代码'].str.startswith(tuple(['600','601','603','605']))
        if uconf.get('exclude_star'):
            mask &= ~stock_spot_df['代码'].str.startswith('688')
        if uconf.get('exclude_chinext'):
            mask &= ~stock_spot_df['代码'].str.startswith(('300','301'))
        stock_spot_df = stock_spot_df[mask]
    else:
        if universe_set:
            stock_spot_df = stock_spot_df[stock_spot_df['代码'].isin(universe_set)]
    if stock_spot_df.empty:
        print("过滤后无上证主板股票。")
        return
    print(f"上证主板候选数: {len(stock_spot_df)}")
    strong_stocks_set, stock_to_sector_map = get_strong_sectors()
    # 行业映射容错：接口可能返回 None
    if not isinstance(stock_to_sector_map, dict):
        stock_to_sector_map = {}
    # 强势股集合容错：确保为集合
    if isinstance(strong_stocks_set, (list, tuple, set)):
        strong_stocks_set = set(strong_stocks_set)
    else:
        strong_stocks_set = set()
    f = CONFIG['filter']
    # 在动态调整前复制一份可调参数
    adj_filter = f.copy()
    # 获取指数数据用于风险控制
    idx_hist_for_risk = get_index_hist_data(CONFIG['market_timing']['index_code'], days=120)
    apply_risk_control_dynamic(adj_filter, idx_hist_for_risk)
    if adj_filter.get('__abort__'):
        print("风险控制触发终止。")
        return
    # 转数值列
    numeric_cols = [col_change,col_volume_ratio,col_turnover,col_mv,col_amount,col_volume,col_price]
    if col_high: numeric_cols.append(col_high)
    if col_low: numeric_cols.append(col_low)
    if col_fund_flow:
        numeric_cols.append(col_fund_flow)
    for c in numeric_cols:
        stock_spot_df[c] = pd.to_numeric(stock_spot_df[c], errors='coerce')
    # ��内强度 (靠近高位) = (价-低)/(高-低)
    intraday_strength = None
    if col_high and col_low and col_price:
        rng = (stock_spot_df[col_high] - stock_spot_df[col_low]).replace(0, np.nan)
        stock_spot_df['日内强度'] = (stock_spot_df[col_price] - stock_spot_df[col_low]) / rng
        intraday_strength = '日内强度'
    # 使用调整后的参数构建条件
    conditions = (
        (stock_spot_df[col_change] >= adj_filter['change_rate_min']) &
        (stock_spot_df[col_change] <= adj_filter['change_rate_max']) &
        (stock_spot_df[col_volume_ratio] >= adj_filter['volume_ratio_min']) &
        (stock_spot_df[col_turnover] >= adj_filter['turnover_rate_min']) &
        (stock_spot_df[col_turnover] <= adj_filter['turnover_rate_max']) &
        (stock_spot_df[col_mv] >= adj_filter['market_cap_min']) &
        (stock_spot_df[col_mv] <= adj_filter['market_cap_max']) &
        (~stock_spot_df['名称'].str.contains('ST')) &
        (~stock_spot_df['名称'].str.startswith('N'))
    )
    if intraday_strength:
        conditions &= (stock_spot_df['日内强度'] >= adj_filter.get('intraday_strength_min', 0))
    if strong_stocks_set:
        conditions &= stock_spot_df['代码'].isin(strong_stocks_set)
    pre_selected_df = stock_spot_df[conditions].copy()
    if pre_selected_df.empty:
        print("初步筛选后无符合条件的股票。")
        return
    print(f"初步筛选完成，共 {len(pre_selected_df)} 只股票进入精选阶段。")
    # --- 新增：导出进入精选阶段股票快照 ---
    snapshot_time = datetime.now()
    snapshot_filename = snapshot_time.strftime('%Y%m%d %H%M%S') + '.csv'
    snapshot_cols = ['代码','名称', col_price, col_change]
    if intraday_strength: snapshot_cols.append('日内强度')
    snapshot_df = pre_selected_df[snapshot_cols].copy()
    # 统一列名
    if col_price != '最新价':
        snapshot_df.rename(columns={col_price:'最新价'}, inplace=True)
    if col_change not in ['涨跌幅','涨跌幅(%)']:
        snapshot_df.rename(columns={col_change:'涨跌幅(%)'}, inplace=True)
    else:
        snapshot_df.rename(columns={col_change:'涨跌幅(%)'}, inplace=True)
    if col_fund_flow and col_fund_flow != '主力净流入-净额':
        snapshot_df.rename(columns={col_fund_flow:'主力净流入-净额'}, inplace=True)
    snapshot_df.insert(0, '截取时间', snapshot_time.strftime('%Y-%m-%d %H:%M:%S'))
    try:
        snapshot_df.to_csv(snapshot_filename, index=False, encoding='utf-8-sig')
        print(f"进入精选阶段快照已保存: {snapshot_filename}")
    except Exception as e:
        print(f"保存精选阶段快照失败: {e}")
    # --- 精选逻辑继续 ---
    final_selection = []
    # 移除过滤原因统计与剔除逻辑，改为对每只股票标注指标通过情况
    index_hist_main = get_index_hist_data(CONFIG['market_timing']['index_code'], days=120)
    rs_days = CONFIG['technique']['rs_days']
    atr_soft = CONFIG['technique']['max_atr_pct'] * CONFIG['technique'].get('atr_soft_margin', 1.0)
    use_wilder = CONFIG['technique'].get('use_wilder_atr', False)
    rel_col_name = f'{rs_days}日相对强度(%)'
    em_conf = CONFIG['enhanced_metrics']
    for _, row in pre_selected_df.iterrows():
        stock_code = row['代码']; stock_name = row['名称']
        print(f"\n分析 -> {stock_name} ({stock_code})")
        # 默认值
        latest_price = safe_float(row[col_price])
        atr_pct = np.nan
        hard_atr_ok = None
        rs_ok = None
        rs_value = np.nan
        amount = safe_float(row[col_amount]); vol = safe_float(row[col_volume])
        vwap = np.nan; vwap_ok = None
        ma_bull_ok = None
        stair_ok = None
        breakout_ok = None
        main_flow_wan = np.nan
        limit_up_col = f"近{em_conf['limit_up_lookback']}日涨停数"; limit_up_count = np.nan
        vol_contraction = np.nan
        roe_v = np.nan; nm_v = np.nan; fundamental_ok = None
        try:
            # 历史数据与技术指标
            hist_df = get_hist_data(stock_code, 200)
            if hist_df is not None and not hist_df.empty:
                for ma in CONFIG['technique']['ma_list']:
                    hist_df[f'MA{ma}'] = hist_df['收盘'].rolling(window=ma).mean()
                hist_df['ATR'] = calculate_atr(hist_df, CONFIG['technique']['atr_days'], wilder=use_wilder)
                # 涨跌幅%
                if '涨跌幅' in hist_df.columns and '涨跌幅%' not in hist_df.columns:
                    try:
                        hist_df['涨跌幅%'] = pd.to_numeric(hist_df['涨跌幅'].astype(str).str.replace('%',''), errors='coerce')
                    except Exception:
                        hist_df['涨跌幅%'] = hist_df['收盘'].pct_change()*100
                elif '涨跌幅%' not in hist_df.columns:
                    hist_df['涨跌幅%'] = hist_df['收盘'].pct_change()*100
                latest = hist_df.iloc[-1]
                close_val = safe_float(latest['收盘'])
                atr_val = safe_float(latest.get('ATR', np.nan))
                if close_val and not np.isnan(close_val) and atr_val and not np.isnan(atr_val):
                    atr_pct = atr_val / close_val * 100.0
                    hard_atr_ok = bool(atr_pct <= CONFIG['technique']['max_atr_pct'])
                    # 宽松提示仅打印，不影响标记
                    if not hard_atr_ok and atr_pct <= atr_soft:
                        print(f"  * [宽松提醒] ATR边缘 {atr_pct:.2f}% > {CONFIG['technique']['max_atr_pct']}%")
                # 相对强度
                if len(hist_df['收盘']) >= rs_days:
                    if index_hist_main is None or index_hist_main.empty or len(index_hist_main) < rs_days:
                        bench_return = 0.0
                    else:
                        bench_return = float((index_hist_main['收盘'].iloc[-1] / index_hist_main['收盘'].iloc[-rs_days]) - 1)
                    stock_return = float((close_val / hist_df['收盘'].iloc[-rs_days]) - 1) if close_val and not np.isnan(close_val) else np.nan
                    if not np.isnan(stock_return):
                        rs_ok = stock_return >= bench_return
                        rs_value = (stock_return - bench_return) * 100.0
                # VWAP
                if vol is not None and not np.isnan(vol) and vol > 0 and amount is not None and not np.isnan(amount):
                    vwap_guess = amount / vol if vol != 0 else np.nan
                    if latest_price and not np.isnan(latest_price) and latest_price * 0.7 <= vwap_guess <= latest_price * 1.3:
                        vwap = vwap_guess
                    else:
                        vwap = amount / (vol * 100) if vol and vol * 100 != 0 else np.nan
                    if vwap and not np.isnan(vwap) and latest_price and not np.isnan(latest_price):
                        vwap_ok = latest_price >= vwap * 0.98
                # 均线多头
                try:
                    ma_values = [safe_float(latest.get(f'MA{d}', np.nan)) for d in CONFIG['technique']['ma_list']]
                    if all(v is not None and not np.isnan(v) for v in ma_values) and not np.isnan(safe_float(latest.get('收盘', np.nan))):
                        ma_bull_ok = (ma_values[0] > ma_values[1] > ma_values[2] > ma_values[3] and safe_float(latest.get('收盘')) > ma_values[0])
                except Exception:
                    pass
                # 台阶放量
                try:
                    stair_ok = is_stair_step_volume(hist_df, CONFIG['technique']['volume_step_days']) if len(hist_df) >= CONFIG['technique']['volume_step_days'] + 1 else None
                except Exception:
                    stair_ok = None
                # 放量突破
                try:
                    if len(hist_df) >= CONFIG['technique']['volume_breakout_days'] + 1:
                        avg_vol = hist_df['成交量'].iloc[-CONFIG['technique']['volume_breakout_days']:-1].mean()
                        breakout_ok = bool(hist_df['成交量'].iloc[-1] >= avg_vol * CONFIG['technique']['volume_breakout_ratio'])
                    else:
                        breakout_ok = None
                except Exception:
                    breakout_ok = None
                # 涨停计数
                try:
                    look = em_conf['limit_up_lookback']
                    if len(hist_df) >= look:
                        recent_pct = hist_df['涨跌幅%'].iloc[-look:]
                    else:
                        recent_pct = hist_df['涨跌幅%']
                    limit_up_count = int((recent_pct >= em_conf['limit_up_threshold']).sum())
                except Exception:
                    limit_up_count = np.nan
                # 波动收缩度
                try:
                    if em_conf.get('enable_vol_contraction') and hist_df['ATR'].notna().sum() > 0:
                        r_win = em_conf['vol_contraction_recent']
                        p_win = em_conf['vol_contraction_prev']
                        if len(hist_df) >= r_win + p_win + 5 and hist_df['ATR'].notna().sum() > (r_win + p_win//2):
                            recent_atr_mean = hist_df['ATR'].iloc[-r_win:].mean()
                            prev_atr_mean = hist_df['ATR'].iloc[-(r_win + p_win):-r_win].mean()
                            if prev_atr_mean and not np.isnan(prev_atr_mean) and prev_atr_mean != 0:
                                vol_contraction = recent_atr_mean / prev_atr_mean
                except Exception:
                    vol_contraction = np.nan
            # 基本面
            fund = get_fundamental_indicator(stock_code)
            roe_need = CONFIG['fundamental']['min_roe']
            nm_need = CONFIG['fundamental']['min_net_margin']
            roe_v = fund.get('roe', np.nan)
            nm_v = fund.get('net_margin', np.nan)
            if CONFIG['fundamental']['enabled']:
                if (pd.isna(roe_v) or pd.isna(nm_v)):
                    fundamental_ok = None
                else:
                    fundamental_ok = bool(roe_v >= roe_need and nm_v >= nm_need)
            else:
                fundamental_ok = None
        except Exception as e:
            print(f"  - [提示] 计算指标时出错: {e}")
        # 主力净流入标准化为万
        try:
            if col_fund_flow and col_fund_flow in row.index:
                raw_flow = safe_float(row[col_fund_flow])
                if not np.isnan(raw_flow):
                    main_flow_wan = raw_flow / 10000.0 if abs(raw_flow) > 1e6 else raw_flow
        except Exception:
            pass
        # 预筛指标标记（用于展示）
        prelim_flags = {
            '涨幅区间': (row[col_change] >= adj_filter['change_rate_min']) and (row[col_change] <= adj_filter['change_rate_max']),
            '量比≥下限': (row[col_volume_ratio] >= adj_filter['volume_ratio_min']),
            '换手率区间': (row[col_turnover] >= adj_filter['turnover_rate_min']) and (row[col_turnover] <= adj_filter['turnover_rate_max']),
            '流通市值区间': (row[col_mv] >= adj_filter['market_cap_min']) and (row[col_mv] <= adj_filter['market_cap_max']),
            '非ST/非N': (not str(row['名称']).startswith('N')) and ('ST' not in str(row['名称'])),
        }
        if intraday_strength:
            prelim_flags['日内强度≥阈值'] = (row['日内强度'] >= adj_filter.get('intraday_strength_min', 0))
        if strong_stocks_set:
            prelim_flags['强势行业'] = (stock_code in strong_stocks_set)
        # 精选指标标记
        final_flags = {
            'ATR≤硬阈值': hard_atr_ok,
            'RS优于指数': rs_ok,
            '价≥VWAP(98%)': vwap_ok,
            '均线多头': ma_bull_ok,
            '台阶放量': stair_ok,
            '放量突破': breakout_ok,
            '基本面合格': fundamental_ok,
        }
        # 计算匹配率
        all_flags = {**prelim_flags, **final_flags}
        applicable_vals = [v for v in all_flags.values() if isinstance(v, bool)]
        passed_cnt = int(sum(1 for v in applicable_vals if v))
        total_cnt = int(len(applicable_vals))
        match_rate = round((passed_cnt / total_cnt * 100.0), 2) if total_cnt > 0 else np.nan
        pretty_flags = {k: ('✓' if v else '✗') if isinstance(v, bool) else '-' for k, v in all_flags.items()}
        # 记录
        record = {
            '代码': stock_code,
            '名称': stock_name,
            '最新价': latest_price,
            '涨跌幅(%)': row[col_change],
            '换手率(%)': row[col_turnover],
            '量比': row[col_volume_ratio],
            rel_col_name: rs_value,
            'ATR%': atr_pct,
            '流通市值(亿)': row[col_mv] / 10 ** 8,
            '主力净流入(万)': main_flow_wan,
            limit_up_col: limit_up_count,
            '波动收缩度': vol_contraction,
            'ROE(%)': roe_v,
            '净利率(%)': nm_v,
            '所属行业': stock_to_sector_map.get(stock_code, '未知'),
            '匹配率(%)': match_rate,
        }
        record.update(pretty_flags)
        final_selection.append(record)
    # 不再打印或导出过滤原因统计
    if not final_selection:
        print("\n最终筛选结果：没有记录。")
        return
    result_df = pd.DataFrame(final_selection)
    # 排序：核心优先 相对强度↓ 主力净流入↓ ATR%↑; 次级再参考 涨跌幅↓ 换手率↓ 流通市值↑
    core_keys = []
    if rel_col_name in result_df.columns: core_keys.append(rel_col_name)
    if '主力净流入(万)' in result_df.columns: core_keys.append('主力净流入(万)')
    if 'ATR%' in result_df.columns: core_keys.append('ATR%')
    secondary = [k for k in ['匹配率(%)','涨跌幅(%)','换手率(%)','流通市值(亿)','ROE(%)','净利率(%)'] if k in result_df.columns]
    sort_keys = core_keys + secondary
    if sort_keys:
        ascending_flags = []
        for k in sort_keys:
            if k in ('ATR%','流通市值(亿)'):
                ascending_flags.append(True)
            else:
                ascending_flags.append(False)
        if '主力净流入(万)' in result_df.columns:
            if '主力净��入(万)' in result_df.columns:
                result_df.rename(columns={'主力净��入(万)':'主力净流入(万)'}, inplace=True)
            result_df['主力净流入(万)'] = result_df['主力净流入(万)'].fillna(-1e12)
        result_df.sort_values(by=sort_keys, ascending=ascending_flags, inplace=True)
    pd.options.display.float_format = '{:.2f}'.format
    print("\n\n========================= 精选列表（不筛除，含指标匹配与匹配率） =========================")
    print(result_df)
    print("================================================================================================\n")
    filename = f"stock_selection_sh_main_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    result_df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"选股结果已保存到文件: {filename}")


if __name__ == "__main__":
    if check_trading_time():
        if check_market_regime():
            run_stock_screener()
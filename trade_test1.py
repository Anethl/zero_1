import os
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
from datetime import datetime, timedelta
import time
import matplotlib.pyplot as plt
from threading import Thread

# ===================== 用户配置区 =====================
INIT_CASH = 690  # 初始本金（美元）
STOP_LOSS = 0.93  # 止损比例（7%）
PORTFOLIO = {
    'KLAC': {'entry_price': 85.5, 'shares': 3.508, 'stop_price': 79.9},
    'ENPH': {'entry_price': 151.0, 'shares': 1.656, 'stop_price': 140.4},
    'SOFI': {'entry_price': 10.2, 'shares': 13.725, 'stop_price': 9.5}
}
# ====================================================

def get_top_sectors():
    """获取实时行业动量Top3"""
    sectors = {
        'Semiconductor': 'SOXX',  # 半导体
        'Clean Energy': 'ICLN',   # 清洁能源
        'Fintech': 'FINX',        # 金融科技
        'Biotech': 'IBB',         # 生物科技
        'REIT': 'VNQ',            # 房地产
        'Gold': 'GLD'             # 黄金
    }
    
    sector_returns = {}
    for name, ticker in sectors.items():
        try:
            data = yf.download(ticker, period='3mo', progress=False)
            ret = (data['Close'][-1]/data['Close'][0] - 1) * 100
            sector_returns[name] = round(ret, 2)
        except:
            continue
    
    return dict(sorted(sector_returns.items(), key=lambda x: x[1], reverse=True)[:3])

def check_breakout(ticker):
    """检测个股突破信号"""
    try:
        data = yf.download(ticker, period='100d', progress=False)
        if len(data) < 50: return False
        
        # 计算技术指标
        high_50d = data['High'].rolling(50).max().iloc[-1]
        current_close = data['Close'].iloc[-1]
        volume_avg = data['Volume'].rolling(30).mean().iloc[-1]
        rsi = ta.rsi(data['Close'], length=14).iloc[-1]
        
        # 突破条件
        breakout_condition = (
            current_close > high_50d and 
            data['Volume'].iloc[-1] > volume_avg * 1.3 and
            rsi < 65
        )
        
        return {
            'ticker': ticker,
            'breakout': breakout_condition,
            'price': current_close,
            '50d_high': high_50d,
            'volume_ratio': round(data['Volume'].iloc[-1]/volume_avg, 2),
            'rsi': round(rsi, 2)
        }
    except:
        return {'ticker': ticker, 'breakout': False}

def monitor_portfolio():
    """监控持仓止损信号"""
    while True:
        print("\n" + "="*50)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 持仓监控中...")
        print("="*50)
        
        # 1. 行业动量分析
        top_sectors = get_top_sectors()
        print("\n🔥 行业动量Top3:")
        for sector, ret in top_sectors.items():
            print(f"  - {sector}: {ret}%")
        
        # 2. 个股突破检测
        print("\n🚀 突破信号检测:")
        for ticker in PORTFOLIO.keys():
            result = check_breakout(ticker)
            if result['breakout']:
                status = "✅ 突破确认" if result['price'] > PORTFOLIO[ticker]['entry_price'] else "⚠️ 突破待确认"
                print(f"  - {ticker}: {status} | 现价: ${result['price']} | 50日高点: ${result['50d_high']} | 量比: {result['volume_ratio']}x | RSI: {result['rsi']}")
            else:
                print(f"  - {ticker}: ❌ 未突破 | 现价: ${result['price']} | 50日高点: ${result['50d_high']}")
        
        # 3. 止损监控
        print("\n🛡️ 止损监控:")
        for ticker, info in PORTFOLIO.items():
            try:
                current_price = yf.download(ticker, period='1d', progress=False)['Close'].iloc[-1]
                stop_price = info['stop_price']
                if current_price <= stop_price:
                    loss_percent = (current_price/info['entry_price'] - 1) * 100
                    print(f"  ‼️【止损触发】{ticker} 现价: ${current_price} | 止损价: ${stop_price} | 亏损: {loss_percent:.2f}%")
                else:
                    profit_percent = (current_price/info['entry_price'] - 1) * 100
                    print(f"  - {ticker} 现价: ${current_price} | 止损价: ${stop_price} | 盈亏: {profit_percent:.2f}%")
            except:
                print(f"  - {ticker} 数据获取失败")
        
        # 4. 生成净值曲线
        update_equity_curve()
        
        # 每小时更新一次
        time.sleep(3600)

def update_equity_curve():
    """更新净值曲线图"""
    equity = INIT_CASH
    equity_data = []
    dates = pd.date_range(end=datetime.now(), periods=30)
    
    for date in dates:
        daily_equity = INIT_CASH
        for ticker, info in PORTFOLIO.items():
            try:
                # 获取历史价格
                hist = yf.download(ticker, start=date.date(), end=date.date() + timedelta(days=1))
                if not hist.empty:
                    price = hist['Close'].iloc[0]
                    position_value = price * info['shares']
                    daily_equity += position_value - (info['entry_price'] * info['shares'])
            except:
                continue
        equity_data.append(daily_equity)
    
    plt.figure(figsize=(10, 5))
    plt.plot(dates, equity_data, 'b-')
    plt.title('Portfolio Equity Curve')
    plt.xlabel('Date')
    plt.ylabel('Value ($)')
    plt.grid(True)
    plt.savefig('equity_curve.png')
    print("\n📈 净值曲线已更新至 equity_curve.png")

def get_alternative_stocks():
    """获取备选突破股"""
    print("\n🔍 扫描备选突破股...")
    watchlist = ['KLAC', 'ENPH', 'SOFI', 'PLTR', 'RIVN', 'AMD', 'SQ', 'PYPL']
    results = []
    
    for ticker in watchlist:
        if ticker not in PORTFOLIO:
            result = check_breakout(ticker)
            if result['breakout']:
                results.append(result)
    
    if results:
        print("\n💎 推荐备选股:")
        for res in results:
            print(f"  - {res['ticker']} | 现价: ${res['price']} | 突破50日高点: ${res['50d_high']}")
    else:
        print("  - 暂无符合突破条件的备选股")

if __name__ == "__main__":
    # 创建监控线程
    monitor_thread = Thread(target=monitor_portfolio)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # 主线程提供用户交互
    while True:
        print("\n===== 美股动量监控系统 =====")
        print("1. 手动刷新监控")
        print("2. 查看备选突破股")
        print("3. 更新持仓信息")
        print("4. 退出系统")
        
        choice = input("请选择操作: ")
        
        if choice == '1':
            # 手动触发监控
            monitor_portfolio()
        elif choice == '2':
            get_alternative_stocks()
        elif choice == '3':
            # 持仓更新功能
            print("输入新持仓 (格式: 代码,入场价,股数,止损价)")
            new_portfolio = {}
            while True:
                data = input("输入持仓 (或输入'done'结束): ")
                if data.lower() == 'done':
                    break
                try:
                    ticker, entry, shares, stop = data.split(',')
                    new_portfolio[ticker] = {
                        'entry_price': float(entry),
                        'shares': float(shares),
                        'stop_price': float(stop)
                    }
                except:
                    print("输入格式错误! 示例: SOFI,10.2,13.725,9.5")
            
            PORTFOLIO = new_portfolio
            print("持仓更新完成!")
        elif choice == '4':
            print("系统退出")
            break
        else:
            print("无效选择")

        time.sleep(1)

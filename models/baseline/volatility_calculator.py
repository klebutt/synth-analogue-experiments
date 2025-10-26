import yfinance as yf

def get_volatility(time, ticker):
    """
    Calculate volatility for a given asset over a time period.
    
    Args:
        time: Period string (e.g., "1d", "2d")
        ticker: Yahoo Finance ticker symbol
        
    Returns:
        float: Standard deviation of returns (per 5-min interval)
    """
    try:
        asset = yf.Ticker(ticker)
        hist = asset.history(period=time, interval="5m")
        if hist.empty:
            return None
        returns = hist['Close'].pct_change().dropna()
        vol = returns.std()
        drift = returns.mean()
        return (vol, drift)
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

# Asset ticker mapping
ASSET_TICKERS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD", 
    "SOL": "SOL-USD",
    "XAU": "GC=F"
}

def get_all_volatilities(period="2d"):
    """Get volatilities for all Synth subnet assets."""
    vols = {}
    for asset, ticker in ASSET_TICKERS.items():
        result = get_volatility(period,ticker)
        if result is not None:
            vol, drift = result
            vols[asset] = {"volatility": vol, "drift": drift}
    return vols
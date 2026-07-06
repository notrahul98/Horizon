"""
swing_trader/core/data_pipeline.py
Enhanced data pipeline with technical analysis integration
"""

import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataPipeline:
    """Enhanced data pipeline for swing trading"""
    
    def __init__(self):
        self.cache = {}
    
    def get_historical_data(self, symbol, days=60):
        """Get historical data for a stock"""
        try:
            # Convert to yfinance format
            yf_symbol = symbol if '.NS' in symbol else f"{symbol}.NS"
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(period='6mo')
            
            if df.empty:
                logger.warning(f"No data for {symbol}")
                return None
            
            # Rename columns
            df.columns = ['open', 'high', 'low', 'close', 'volume']
            df['symbol'] = symbol
            df['date'] = df.index
            
            return df
        
        except Exception as e:
            logger.error(f"Error fetching {symbol}: {str(e)}")
            return None
    
    def get_latest_price(self, symbol):
        """Get latest price for a stock"""
        try:
            yf_symbol = symbol if '.NS' in symbol else f"{symbol}.NS"
            ticker = yf.Ticker(yf_symbol)
            data = ticker.history(period='1d')
            
            if data.empty:
                return None
            
            return {
                'symbol': symbol,
                'close': data['Close'].iloc[-1],
                'date': data.index[-1],
                'volume': data['Volume'].iloc[-1]
            }
        except Exception as e:
            logger.error(f"Error getting latest price for {symbol}: {str(e)}")
            return None
    
    def validate_ohlcv(self, df):
        """Validate OHLCV data"""
        try:
            assert (df['high'] >= df['low']).all(), "High < Low"
            assert (df['high'] >= df['open']).all(), "High < Open"
            assert (df['high'] >= df['close']).all(), "High < Close"
            assert (df['volume'] > 0).all(), "Zero volume"
            return True
        except AssertionError as e:
            logger.error(f"Data validation failed: {e}")
            return False

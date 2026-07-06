"""
swing_trader/core/technical_analysis.py
Technical indicators and pattern recognition
"""

import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Technical analysis engine with indicators"""
    
    def __init__(self):
        self.indicators = {}
    
    def calculate_ema(self, df, period=20):
        """Calculate Exponential Moving Average"""
        return df['close'].ewm(span=period, adjust=False).mean()
    
    def calculate_rsi(self, df, period=14):
        """Calculate Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_macd(self, df):
        """Calculate MACD"""
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9, adjust=False).mean()
        histogram = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, df, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        upper_band = sma + (std_dev * std)
        lower_band = sma - (std_dev * std)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def analyze_stock(self, df):
        """Complete technical analysis for a stock"""
        try:
            if df is None or len(df) < 30:
                return None
            
            analysis = {
                'symbol': df['symbol'].iloc[0] if 'symbol' in df.columns else 'UNKNOWN',
                'date': df['date'].iloc[-1] if 'date' in df.columns else datetime.now(),
                'price': df['close'].iloc[-1],
                'ema_20': self.calculate_ema(df, 20).iloc[-1],
                'ema_50': self.calculate_ema(df, 50).iloc[-1],
                'ema_200': self.calculate_ema(df, 200).iloc[-1],
                'rsi': self.calculate_rsi(df).iloc[-1],
                'macd': self.calculate_macd(df)['macd'].iloc[-1],
                'signal': self.calculate_macd(df)['signal'].iloc[-1],
            }
            
            # Add Bollinger Bands
            bb = self.calculate_bollinger_bands(df)
            analysis['bb_upper'] = bb['upper'].iloc[-1]
            analysis['bb_lower'] = bb['lower'].iloc[-1]
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing stock: {str(e)}")
            return None
    
    def identify_patterns(self, df):
        """Identify chart patterns"""
        patterns = []
        
        try:
            # Golden Cross (EMA 20 > EMA 50)
            ema_20 = self.calculate_ema(df, 20)
            ema_50 = self.calculate_ema(df, 50)
            
            if len(ema_20) >= 2:
                if ema_20.iloc[-1] > ema_50.iloc[-1] and ema_20.iloc[-2] <= ema_50.iloc[-2]:
                    patterns.append({
                        'pattern': 'GOLDEN_CROSS',
                        'signal': 'BUY',
                        'strength': 'HIGH'
                    })
            
            # Death Cross (EMA 20 < EMA 50)
            if len(ema_20) >= 2:
                if ema_20.iloc[-1] < ema_50.iloc[-1] and ema_20.iloc[-2] >= ema_50.iloc[-2]:
                    patterns.append({
                        'pattern': 'DEATH_CROSS',
                        'signal': 'SELL',
                        'strength': 'HIGH'
                    })
            
            # RSI Oversold (RSI < 30)
            rsi = self.calculate_rsi(df)
            if rsi.iloc[-1] < 30:
                patterns.append({
                    'pattern': 'RSI_OVERSOLD',
                    'signal': 'BUY',
                    'strength': 'MEDIUM'
                })
            
            # RSI Overbought (RSI > 70)
            if rsi.iloc[-1] > 70:
                patterns.append({
                    'pattern': 'RSI_OVERBOUGHT',
                    'signal': 'SELL',
                    'strength': 'MEDIUM'
                })
            
            return patterns
        
        except Exception as e:
            logger.error(f"Error identifying patterns: {str(e)}")
            return []

from datetime import datetime

"""
swing_trader/agents/deepseek_agent.py
DeepSeek agent for quantitative analysis
"""

import logging
import json

logger = logging.getLogger(__name__)

class DeepSeekAgent:
    """
    DeepSeek Agent - Quantitative Pattern Analyst
    Analyzes technical patterns, support/resistance, momentum
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.enabled = api_key is not None
        self.name = "DeepSeek"
    
    def analyze(self, stock_data, technical_analysis):
        """
        Analyze stock using quantitative methods
        Returns: {'signal': 'BUY'/'SELL'/'HOLD', 'reasoning': '...', 'confidence': 0-100}
        """
        
        if not self.enabled:
            return self._offline_analysis(stock_data, technical_analysis)
        
        try:
            # For now, return offline analysis
            # Will integrate real API when available
            return self._offline_analysis(stock_data, technical_analysis)
        
        except Exception as e:
            logger.error(f"DeepSeek error: {str(e)}")
            return self._offline_analysis(stock_data, technical_analysis)
    
    def _offline_analysis(self, stock_data, analysis):
        """Offline quantitative analysis"""
        
        try:
            if not analysis:
                return {
                    'agent': self.name,
                    'signal': 'HOLD',
                    'reasoning': 'Insufficient data',
                    'confidence': 0
                }
            
            price = analysis['price']
            ema_20 = analysis['ema_20']
            ema_50 = analysis['ema_50']
            rsi = analysis['rsi']
            
            signal = 'HOLD'
            confidence = 0
            reasoning = []
            
            # Quantitative rules
            # Rule 1: Strong uptrend + RSI not overbought
            if price > ema_20 > ema_50 and rsi < 70:
                signal = 'BUY'
                confidence = 75
                reasoning.append("Strong uptrend with EMA alignment")
                reasoning.append("RSI indicating room for upside")
            
            # Rule 2: RSI oversold in uptrend
            elif price > ema_50 and rsi < 30:
                signal = 'BUY'
                confidence = 60
                reasoning.append("Oversold in uptrend (RSI < 30)")
                reasoning.append("Good risk-reward setup")
            
            # Rule 3: Strong downtrend + RSI not oversold
            elif price < ema_20 < ema_50 and rsi > 30:
                signal = 'SELL'
                confidence = 75
                reasoning.append("Strong downtrend with EMA alignment")
                reasoning.append("RSI indicating room for downside")
            
            # Rule 4: RSI overbought in downtrend
            elif price < ema_50 and rsi > 70:
                signal = 'SELL'
                confidence = 60
                reasoning.append("Overbought in downtrend (RSI > 70)")
                reasoning.append("Reversal potential")
            
            return {
                'agent': self.name,
                'signal': signal,
                'reasoning': ' | '.join(reasoning) if reasoning else 'Neutral technicals',
                'confidence': confidence
            }
        
        except Exception as e:
            logger.error(f"Error in offline analysis: {str(e)}")
            return {
                'agent': self.name,
                'signal': 'HOLD',
                'reasoning': 'Analysis error',
                'confidence': 0
            }

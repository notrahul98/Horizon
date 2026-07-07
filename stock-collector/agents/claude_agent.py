"""
stock-collector/agents/claude_agent.py
Claude agent for narrative and risk analysis
"""

import logging

logger = logging.getLogger(__name__)

class ClaudeAgent:
    """
    Claude Agent - Narrative & Risk Analyst
    Analyzes market context, news sentiment, risk factors
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.enabled = api_key is not None
        self.name = "Claude"
    
    def analyze(self, stock_data, technical_analysis):
        """
        Analyze stock from narrative and risk perspective
        Returns: {'signal': 'BUY'/'SELL'/'HOLD', 'reasoning': '...', 'confidence': 0-100}
        """
        
        if not self.enabled:
            return self._offline_analysis(stock_data, technical_analysis)
        
        try:
            # For now, return offline analysis
            # Will integrate Claude API when you add ANTHROPIC_API_KEY
            return self._offline_analysis(stock_data, technical_analysis)
        
        except Exception as e:
            logger.error(f"Claude error: {str(e)}")
            return self._offline_analysis(stock_data, technical_analysis)
    
    def _offline_analysis(self, stock_data, analysis):
        """Offline narrative analysis"""
        
        try:
            if not analysis:
                return {
                    'agent': self.name,
                    'signal': 'HOLD',
                    'reasoning': 'Insufficient data',
                    'confidence': 0
                }
            
            ema_20 = analysis['ema_20']
            ema_50 = analysis['ema_50']
            ema_200 = analysis['ema_200']
            rsi = analysis['rsi']
            price = analysis['price']
            
            signal = 'HOLD'
            confidence = 0
            reasoning = []
            
            # Long-term trend assessment
            if ema_50 > ema_200:
                trend_bias = "bullish"
                reasoning.append("Long-term uptrend confirmed (EMA 50 > 200)")
            elif ema_50 < ema_200:
                trend_bias = "bearish"
                reasoning.append("Long-term downtrend confirmed (EMA 50 < 200)")
            else:
                trend_bias = "neutral"
                reasoning.append("No clear long-term trend")
            
            # Medium-term risk assessment
            if price > ema_20:
                ma_support = "bullish"
                reasoning.append("Above 20-day MA (near-term support)")
            else:
                ma_support = "bearish"
                reasoning.append("Below 20-day MA (potential weakness)")
            
            # Momentum risk
            if rsi > 70:
                reasoning.append("⚠️ WARNING: Overbought conditions (RSI > 70)")
            elif rsi < 30:
                reasoning.append("💡 NOTE: Oversold conditions (RSI < 30) - potential bounce")
            
            # Decision logic
            if trend_bias == "bullish" and ma_support == "bullish" and rsi < 70:
                signal = 'BUY'
                confidence = 70
                reasoning.append("Aligned signals: Long-term bullish + MA support + momentum room")
            elif trend_bias == "bearish" and ma_support == "bearish" and rsi > 30:
                signal = 'SELL'
                confidence = 70
                reasoning.append("Aligned signals: Long-term bearish + MA weakness + momentum room")
            elif rsi < 30 and trend_bias == "bullish":
                signal = 'BUY'
                confidence = 50
                reasoning.append("Low-risk entry in established uptrend")
            elif rsi > 70 and trend_bias == "bearish":
                signal = 'SELL'
                confidence = 50
                reasoning.append("Exit opportunity in established downtrend")
            
            return {
                'agent': self.name,
                'signal': signal,
                'reasoning': ' | '.join(reasoning),
                'confidence': confidence
            }
        
        except Exception as e:
            logger.error(f"Error in narrative analysis: {str(e)}")
            return {
                'agent': self.name,
                'signal': 'HOLD',
                'reasoning': 'Analysis error',
                'confidence': 0
            }

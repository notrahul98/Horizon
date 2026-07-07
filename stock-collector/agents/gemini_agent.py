"""
stock-collector/agents/gemini_agent.py
Gemini agent for market sentiment and macro analysis
"""

import logging

logger = logging.getLogger(__name__)

class GeminiAgent:
    """
    Gemini Agent - Sentiment & Macro Analyst
    Analyzes market sentiment, volatility, macro factors
    """
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.enabled = api_key is not None
        self.name = "Gemini"
    
    def analyze(self, stock_data, technical_analysis):
        """
        Analyze stock from sentiment and macro perspective
        Returns: {'signal': 'BUY'/'SELL'/'HOLD', 'reasoning': '...', 'confidence': 0-100}
        """
        
        if not self.enabled:
            return self._offline_analysis(stock_data, technical_analysis)
        
        try:
            # For now, return offline analysis
            # Will integrate Gemini API when you add GEMINI_API_KEY
            return self._offline_analysis(stock_data, technical_analysis)
        
        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            return self._offline_analysis(stock_data, technical_analysis)
    
    def _offline_analysis(self, stock_data, analysis):
        """Offline sentiment and volatility analysis"""
        
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
            ema_200 = analysis['ema_200']
            rsi = analysis['rsi']
            bb_upper = analysis.get('bb_upper', price * 1.05)
            bb_lower = analysis.get('bb_lower', price * 0.95)
            
            signal = 'HOLD'
            confidence = 0
            reasoning = []
            
            # Volatility assessment
            bb_width = bb_upper - bb_lower
            bb_width_pct = (bb_width / price) * 100
            
            if bb_width_pct > 10:
                reasoning.append("High volatility environment")
                vol_profile = "high"
            elif bb_width_pct > 5:
                reasoning.append("Normal volatility")
                vol_profile = "normal"
            else:
                reasoning.append("Low volatility - possible squeeze")
                vol_profile = "low"
            
            # Price position in Bollinger Bands
            price_position = (price - bb_lower) / bb_width if bb_width > 0 else 0.5
            
            if price_position > 0.8:
                reasoning.append("Price near upper Bollinger Band")
                sentiment = "bullish_extreme"
            elif price_position < 0.2:
                reasoning.append("Price near lower Bollinger Band")
                sentiment = "bearish_extreme"
            elif price_position > 0.6:
                reasoning.append("Price in upper half of range")
                sentiment = "bullish"
            elif price_position < 0.4:
                reasoning.append("Price in lower half of range")
                sentiment = "bearish"
            else:
                reasoning.append("Price in middle of range")
                sentiment = "neutral"
            
            # Sentiment-based signals
            if vol_profile == "low" and sentiment == "neutral":
                reasoning.append("💡 Setup: Low volatility + neutral position = potential breakout coming")
                signal = 'HOLD'
                confidence = 40
            
            elif sentiment == "bullish_extreme" and rsi > 70:
                reasoning.append("⚡ Extended move: Overbought + at upper band = profit-taking risk")
                signal = 'SELL'
                confidence = 55
            
            elif sentiment == "bearish_extreme" and rsi < 30:
                reasoning.append("💰 Oversold: At lower band + RSI extreme = reversal opportunity")
                signal = 'BUY'
                confidence = 60
            
            elif sentiment == "bullish" and vol_profile != "high":
                signal = 'BUY'
                confidence = 50
                reasoning.append("Bullish sentiment with manageable risk")
            
            elif sentiment == "bearish" and vol_profile != "high":
                signal = 'SELL'
                confidence = 50
                reasoning.append("Bearish sentiment with manageable risk")
            
            return {
                'agent': self.name,
                'signal': signal,
                'reasoning': ' | '.join(reasoning),
                'confidence': confidence
            }
        
        except Exception as e:
            logger.error(f"Error in sentiment analysis: {str(e)}")
            return {
                'agent': self.name,
                'signal': 'HOLD',
                'reasoning': 'Analysis error',
                'confidence': 0
            }

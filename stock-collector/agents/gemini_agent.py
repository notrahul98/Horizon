"""
stock-collector/agents/gemini_agent.py
Gemini agent for market sentiment and macro analysis
"""

import json
import logging
import os
import threading
import time

import requests

logger = logging.getLogger(__name__)

# Called via plain REST (like trades_store.py's Turso client) so no google-genai
# package is needed — keeps uv.lock untouched. flash-lite has the most generous
# free-tier limits (well above the ~150 calls/day the scanner needs) and is
# plenty for a signal/confidence classification task.
_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
_GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent"

# The daily scanner runs consensus over all ~150 watchlist symbols in one loop;
# unthrottled, that hits the free tier's requests-per-minute cap within the
# first minute and every later symbol silently degrades to the offline
# heuristic. ~4.1s between calls stays under 15 RPM (the flash-lite free-tier
# limit) — the scan takes ~10 min inside its background thread, which is fine.
# The lock also serializes concurrent Flask request threads.
_MIN_CALL_INTERVAL = 4.1
_throttle_lock = threading.Lock()
_last_call_at = 0.0
# After a 429, skip live calls entirely for a while instead of queueing more.
_cooldown_until = 0.0


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

        result = self._live_analysis(stock_data, technical_analysis)
        if result is not None:
            return result

        # Live call failed — fall back, but say so rather than letting the
        # rule-based output pass as a model response.
        fallback = self._offline_analysis(stock_data, technical_analysis)
        fallback['reasoning'] = '[Gemini API unavailable — offline heuristic] ' + fallback['reasoning']
        return fallback

    def _live_analysis(self, stock_data, technical_analysis):
        """Call the Gemini API. Returns the signal dict, or None on any failure."""
        global _last_call_at, _cooldown_until

        if not technical_analysis:
            return None
        if time.monotonic() < _cooldown_until:
            logger.debug("Gemini in rate-limit cooldown, using offline analysis")
            return None

        try:
            prompt = self._build_prompt(stock_data, technical_analysis)

            with _throttle_lock:
                wait = _last_call_at + _MIN_CALL_INTERVAL - time.monotonic()
                if wait > 0:
                    time.sleep(wait)
                _last_call_at = time.monotonic()

            resp = requests.post(
                _GEMINI_URL,
                headers={"x-goog-api-key": self.api_key,
                         "Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=25,
            )

            if resp.status_code == 429:
                _cooldown_until = time.monotonic() + 60
                logger.warning("Gemini rate-limited (429); offline fallback for 60s")
                return None
            if resp.status_code != 200:
                logger.warning("Gemini API HTTP %s: %s", resp.status_code, resp.text[:300])
                return None

            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)

            signal = str(parsed.get("signal", "")).upper()
            if signal not in ("BUY", "SELL", "HOLD"):
                logger.warning("Gemini returned unexpected signal %r", parsed.get("signal"))
                return None
            confidence = max(0, min(100, int(parsed.get("confidence", 0))))
            reasoning = str(parsed.get("reasoning", "")).strip() or "No reasoning provided"

            return {
                'agent': self.name,
                'signal': signal,
                'reasoning': reasoning,
                'confidence': confidence,
            }

        except Exception as e:
            logger.error(f"Gemini error: {str(e)}")
            return None

    def _build_prompt(self, stock_data, analysis):
        stock_data = stock_data or {}
        lines = [
            "You are a market sentiment and volatility analyst evaluating an NSE (India) stock",
            "for a multi-day swing trade. Focus on volatility regime, price positioning,",
            "momentum extremes, and mean-reversion vs continuation risk — a separate agent",
            "already covers pure trend-following, so add a distinct sentiment/risk perspective.",
            "",
            f"Symbol: {stock_data.get('symbol', 'unknown')}",
            f"Last close: {analysis['price']}",
        ]
        # Core indicators always present via dashboard.get_ai_consensus();
        # the rest is included only when the caller passed a full detail dict.
        lines += [
            f"EMA20: {analysis['ema_20']}  EMA50: {analysis['ema_50']}  EMA200: {analysis['ema_200']}",
            f"RSI(14): {analysis['rsi']}",
            f"Bollinger upper: {analysis.get('bb_upper')}  lower: {analysis.get('bb_lower')}",
        ]
        for label, key in [
            ("Day change %", "day_chg"), ("52-week high", "high_52w"),
            ("52-week low", "low_52w"), ("Volume vs 50-day avg (ratio)", "vol_ratio"),
            ("MACD", "macd"), ("MACD signal line", "macd_signal"),
            ("Stochastic %K", "stoch_k"), ("Williams %R", "williams_r"), ("CCI", "cci"),
        ]:
            if stock_data.get(key) is not None:
                lines.append(f"{label}: {stock_data[key]}")
        lines += [
            "",
            'Respond with ONLY a JSON object: {"signal": "BUY"|"SELL"|"HOLD",',
            '"confidence": <integer 0-100>, "reasoning": "<one or two concise sentences>"}',
        ]
        return "\n".join(lines)
    
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

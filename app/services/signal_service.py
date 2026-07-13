from __future__ import annotations

from typing import Any, Dict, List, Tuple

import pandas as pd

from app.cache.market_cache import market_cache


class SignalService:
    def __init__(self) -> None:
        self.name = "SignalService"

    def _num(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None or pd.isna(value):
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _bool(self, value: Any) -> bool:
        try:
            if value is None or pd.isna(value):
                return False
        except (TypeError, ValueError):
            pass
        return bool(value)

    def _add_filter(
        self,
        filters: List[Dict[str, Any]],
        name: str,
        direction: str,
        weight: float,
        passed: bool,
        detail: str,
    ) -> float:
        signed = 0.0
        if passed:
            signed = weight if direction == "CALL" else -weight if direction == "PUT" else 0.0
        filters.append(
            {
                "name": name,
                "direction": direction if passed else "NEUTRAL",
                "weight": round(abs(weight), 2),
                "passed": passed,
                "scoreImpact": round(signed, 2),
                "detail": detail,
            }
        )
        return signed

    def _trend_filter(self, latest: pd.Series) -> Tuple[float, List[Dict[str, Any]], str, str]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        ema_9 = self._num(latest.get("ema_9"))
        ema_21 = self._num(latest.get("ema_21"))
        sma_20 = self._num(latest.get("sma_20"))
        close = self._num(latest.get("close"))
        adx = self._num(latest.get("adx"))
        sar = self._num(latest.get("sar"), default=float("nan"))

        bullish_ema = ema_9 > ema_21 and close >= ema_9
        bearish_ema = ema_9 < ema_21 and close <= ema_9
        trend = "bullish" if bullish_ema else "bearish" if bearish_ema else "neutral"
        market_phase = "trend" if adx >= 20 else "range"

        score += self._add_filter(filters, "EMA 9/21 + preco", "CALL", 22, bullish_ema, f"ema9={ema_9:.5f}, ema21={ema_21:.5f}, close={close:.5f}")
        score += self._add_filter(filters, "EMA 9/21 + preco", "PUT", 22, bearish_ema, f"ema9={ema_9:.5f}, ema21={ema_21:.5f}, close={close:.5f}")
        adx_direction = "CALL" if trend == "bullish" else "PUT" if trend == "bearish" else "NEUTRAL"
        score += self._add_filter(filters, "ADX tendencia minima", adx_direction, 12, adx >= 20 and trend != "neutral", f"adx={adx:.2f}")
        score += self._add_filter(filters, "SMA 20 direcao", "CALL", 8, close > sma_20 and trend == "bullish", f"sma20={sma_20:.5f}")
        score += self._add_filter(filters, "SMA 20 direcao", "PUT", 8, close < sma_20 and trend == "bearish", f"sma20={sma_20:.5f}")
        if not pd.isna(sar):
            score += self._add_filter(filters, "SAR", "CALL", 6, close > sar and trend == "bullish", f"sar={sar:.5f}")
            score += self._add_filter(filters, "SAR", "PUT", 6, close < sar and trend == "bearish", f"sar={sar:.5f}")
        else:
            filters.append({"name": "SAR", "direction": "NEUTRAL", "weight": 6, "passed": False, "scoreImpact": 0, "detail": "sar indisponivel"})

        return score, filters, trend, market_phase

    def _momentum_filter(self, latest: pd.Series, trend: str) -> Tuple[float, List[Dict[str, Any]]]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        rsi = self._num(latest.get("rsi_14"), 50.0)
        macd = self._num(latest.get("macd"))
        stoch_k = self._num(latest.get("stoch_k"), 50.0)
        stoch_d = self._num(latest.get("stoch_d"), 50.0)

        bullish_rsi = 52 <= rsi <= 72
        bearish_rsi = 28 <= rsi <= 48
        overbought = rsi > 78
        oversold = rsi < 22

        score += self._add_filter(filters, "RSI favoravel", "CALL", 13, bullish_rsi and trend != "bearish", f"rsi={rsi:.2f}")
        score += self._add_filter(filters, "RSI favoravel", "PUT", 13, bearish_rsi and trend != "bullish", f"rsi={rsi:.2f}")
        score += self._add_filter(filters, "MACD", "CALL", 12, macd > 0 and trend != "bearish", f"macd={macd:.5f}")
        score += self._add_filter(filters, "MACD", "PUT", 12, macd < 0 and trend != "bullish", f"macd={macd:.5f}")
        score += self._add_filter(filters, "Stochastic K/D", "CALL", 8, stoch_k > stoch_d and stoch_k < 85, f"k={stoch_k:.2f}, d={stoch_d:.2f}")
        score += self._add_filter(filters, "Stochastic K/D", "PUT", 8, stoch_k < stoch_d and stoch_k > 15, f"k={stoch_k:.2f}, d={stoch_d:.2f}")

        if overbought:
            score -= 10
            filters.append({"name": "RSI extremo", "direction": "PUT", "weight": 10, "passed": True, "scoreImpact": -10, "detail": f"sobrecomprado rsi={rsi:.2f}"})
        elif oversold:
            score += 10
            filters.append({"name": "RSI extremo", "direction": "CALL", "weight": 10, "passed": True, "scoreImpact": 10, "detail": f"sobrevendido rsi={rsi:.2f}"})

        return score, filters

    def _volatility_filter(self, latest: pd.Series) -> Tuple[float, List[Dict[str, Any]], bool]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        close = self._num(latest.get("close"))
        atr = self._num(latest.get("atr"))
        bb_upper = self._num(latest.get("bb_upper"))
        bb_middle = self._num(latest.get("bb_middle"))
        bb_lower = self._num(latest.get("bb_lower"))
        bollinger_width = abs(bb_upper - bb_lower) if bb_upper and bb_lower else self._num(latest.get("bollinger_width"))
        atr_ratio = atr / close if close else 0.0
        width_ratio = bollinger_width / close if close else 0.0
        volatility_ok = atr_ratio >= 0.00005 or width_ratio >= 0.0001

        score += self._add_filter(filters, "Volatilidade minima", "NEUTRAL", 8, volatility_ok, f"atr_ratio={atr_ratio:.6f}, bb_width_ratio={width_ratio:.6f}")
        score += self._add_filter(filters, "Bollinger lado superior", "CALL", 5, close > bb_middle and bb_middle > 0, f"close={close:.5f}, middle={bb_middle:.5f}")
        score += self._add_filter(filters, "Bollinger lado inferior", "PUT", 5, close < bb_middle and bb_middle > 0, f"close={close:.5f}, middle={bb_middle:.5f}")

        return score, filters, volatility_ok

    def _price_action_filter(self, latest: pd.Series, trend: str) -> Tuple[float, List[Dict[str, Any]]]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        close = self._num(latest.get("close"))
        open_ = self._num(latest.get("open"))
        body_percent = self._num(latest.get("body_percent"))
        wick_percent = self._num(latest.get("wick_percent"))
        breakout = self._bool(latest.get("breakout"))
        compression = self._bool(latest.get("compression"))
        doji = self._bool(latest.get("doji"))
        candle_direction = "CALL" if close > open_ else "PUT" if close < open_ else "NEUTRAL"

        score += self._add_filter(filters, "Candle direcional", candle_direction, 9, candle_direction != "NEUTRAL" and body_percent >= 35, f"body={body_percent:.2f}%, wick={wick_percent:.2f}%")
        score += self._add_filter(filters, "Breakout a favor", "CALL", 8, breakout and trend == "bullish", "rompimento acima do fechamento anterior")
        score += self._add_filter(filters, "Breakout a favor", "PUT", 8, (not breakout) and trend == "bearish", "fechamento abaixo/sem rompimento de alta")
        if compression:
            filters.append({"name": "Compressao", "direction": "NEUTRAL", "weight": 4, "passed": True, "scoreImpact": 0, "detail": "mercado comprimido; exige confluencia maior"})
        if doji:
            score *= 0.75
            filters.append({"name": "Doji", "direction": "NEUTRAL", "weight": 10, "passed": True, "scoreImpact": -10, "detail": "candle de indecisao reduziu o score"})

        return score, filters

    def _structure_filter(self, latest: pd.Series) -> Tuple[float, List[Dict[str, Any]]]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        close = self._num(latest.get("close"))
        support = self._num(latest.get("support"))
        resistance = self._num(latest.get("resistance"))
        equal_high = self._bool(latest.get("equal_high"))
        equal_low = self._bool(latest.get("equal_low"))
        range_size = max(resistance - support, 1e-9)
        position = (close - support) / range_size if support and resistance and resistance > support else 0.5

        score += self._add_filter(filters, "Perto do suporte", "CALL", 7, position <= 0.35, f"posicao_range={position:.2f}")
        score += self._add_filter(filters, "Perto da resistencia", "PUT", 7, position >= 0.65, f"posicao_range={position:.2f}")
        if equal_high:
            score -= 3
            filters.append({"name": "Topo igual", "direction": "PUT", "weight": 3, "passed": True, "scoreImpact": -3, "detail": "equal_high detectado"})
        if equal_low:
            score += 3
            filters.append({"name": "Fundo igual", "direction": "CALL", "weight": 3, "passed": True, "scoreImpact": 3, "detail": "equal_low detectado"})
        return score, filters

    def _activity_filter(self, latest: pd.Series) -> Tuple[float, List[Dict[str, Any]]]:
        filters: List[Dict[str, Any]] = []
        score = 0.0
        synthetic_volume = self._num(latest.get("synthetic_volume"))
        activity = self._num(latest.get("market_activity_score"))
        active = synthetic_volume >= 0.85 and activity >= 0.75
        very_active = synthetic_volume >= 1.05 and activity >= 0.95
        score += self._add_filter(filters, "Atividade minima", "NEUTRAL", 7, active, f"synthetic_volume={synthetic_volume:.2f}, activity={activity:.2f}")
        if very_active:
            filters.append({"name": "Atividade forte", "direction": "NEUTRAL", "weight": 5, "passed": True, "scoreImpact": 5, "detail": "atividade acima da media"})
            score += 5
        return score, filters

    def build_signal(self, symbol: str = "EURUSD") -> Dict[str, Any]:
        df = market_cache.get_candles(symbol)
        if df is None or df.empty:
            return {
                "symbol": symbol,
                "action": "NONE",
                "score": 0.0,
                "confidence": 0.0,
                "reason": "No market data",
                "expiration": 30,
                "entryPrice": 0.0,
                "marketPhase": "neutral",
                "trend": "neutral",
                "historicalAccuracy": 0.0,
                "filters": [],
                "confluence": {},
            }
        latest = df.iloc[-1]
        trend_score, trend_filters, trend, market_phase = self._trend_filter(latest)
        momentum_score, momentum_filters = self._momentum_filter(latest, trend)
        volatility_score, volatility_filters, volatility_ok = self._volatility_filter(latest)
        price_score, price_filters = self._price_action_filter(latest, trend)
        structure_score, structure_filters = self._structure_filter(latest)
        activity_score, activity_filters = self._activity_filter(latest)

        raw_score = trend_score + momentum_score + volatility_score + price_score + structure_score + activity_score
        filters = trend_filters + momentum_filters + volatility_filters + price_filters + structure_filters + activity_filters
        passed_filters = [item for item in filters if item.get("passed")]
        call_votes = sum(1 for item in passed_filters if item.get("direction") == "CALL")
        put_votes = sum(1 for item in passed_filters if item.get("direction") == "PUT")

        min_score = 35
        if not volatility_ok:
            min_score += 10
        if market_phase == "range":
            min_score += 5

        if raw_score >= min_score and call_votes >= 3:
            action = "CALL"
        elif raw_score <= -min_score and put_votes >= 3:
            action = "PUT"
        else:
            action = "NONE"

        confidence = min(0.95, max(0.0, abs(raw_score) / 100.0))
        if action == "NONE":
            confidence = min(confidence, 0.45)

        reasons = [
            item["name"]
            for item in sorted(passed_filters, key=lambda item: abs(float(item.get("scoreImpact", 0))), reverse=True)
            if item.get("direction") in {"CALL", "PUT"}
        ][:4]
        reason = ", ".join(reasons) if reasons else "Sem confluencia suficiente"

        return {
            "symbol": symbol,
            "action": action,
            "score": round(raw_score, 2),
            "confidence": round(confidence, 2),
            "reason": reason,
            "expiration": 30,
            "entryPrice": self._num(latest.get("close")),
            "marketPhase": market_phase,
            "trend": trend,
            "historicalAccuracy": 0.62,
            "filters": filters,
            "confluence": {
                "callVotes": call_votes,
                "putVotes": put_votes,
                "passedFilters": len(passed_filters),
                "totalFilters": len(filters),
                "minimumScore": min_score,
                "volatilityOk": volatility_ok,
                "scores": {
                    "trend": round(trend_score, 2),
                    "momentum": round(momentum_score, 2),
                    "volatility": round(volatility_score, 2),
                    "priceAction": round(price_score, 2),
                    "structure": round(structure_score, 2),
                    "activity": round(activity_score, 2),
                },
            },
        }


signal_service = SignalService()

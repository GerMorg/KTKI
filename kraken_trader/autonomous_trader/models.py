from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal
from enum import Enum
from typing import Any
import hashlib, json, time, uuid

def dec(value: Any, default: Decimal = Decimal("0")) -> Decimal:
    if value is None or value == "":
        return default
    return Decimal(str(value))

def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"

class Stage(str, Enum):
    BOOT="BOOT"; CONFIG_VALIDATING="CONFIG_VALIDATING"; KRAKEN_AUTH_CHECK="KRAKEN_AUTH_CHECK"
    PRODUCT_DISCOVERY="PRODUCT_DISCOVERY"; INSTRUMENT_SYNC="INSTRUMENT_SYNC"; PUBLIC_DATA_CONNECT="PUBLIC_DATA_CONNECT"
    PRIVATE_DATA_CONNECT="PRIVATE_DATA_CONNECT"; ACCOUNT_SYNC="ACCOUNT_SYNC"; PORTFOLIO_SYNC="PORTFOLIO_SYNC"
    HISTORY_BACKFILL="HISTORY_BACKFILL"; MODEL_INITIALIZATION="MODEL_INITIALIZATION"; HEALTH_CHECK="HEALTH_CHECK"; READY="READY"
    CYCLE_START="CYCLE_START"; MARKET_DISCOVERY="MARKET_DISCOVERY"; MARKET_FILTER="MARKET_FILTER"; MARKET_SNAPSHOT="MARKET_SNAPSHOT"
    FEATURE_CALCULATION="FEATURE_CALCULATION"; REGIME_DETECTION="REGIME_DETECTION"; NEWS_ANALYSIS="NEWS_ANALYSIS"
    GEMINI_ANALYSIS="GEMINI_ANALYSIS"; SIGNAL_EVALUATION="SIGNAL_EVALUATION"; COST_ESTIMATION="COST_ESTIMATION"
    EXPECTED_EDGE="EXPECTED_EDGE"; PORTFOLIO_TARGET="PORTFOLIO_TARGET"; LEVERAGE_SELECTION="LEVERAGE_SELECTION"
    MARGIN_CHECK="MARGIN_CHECK"; RISK_CHECK="RISK_CHECK"; DECISION_CREATED="DECISION_CREATED"; PRETRADE_CHECK="PRETRADE_CHECK"
    ORDER_SUBMITTING="ORDER_SUBMITTING"; RECONCILIATION="RECONCILIATION"; PORTFOLIO_UPDATED="PORTFOLIO_UPDATED"
    OUTCOME_TRACKING="OUTCOME_TRACKING"; LEARNING_EVENT="LEARNING_EVENT"; CALIBRATION="CALIBRATION"; CYCLE_COMPLETE="CYCLE_COMPLETE"

class OrderState(str, Enum):
    INTENT_CREATED="INTENT_CREATED"; PRECHECK_PASSED="PRECHECK_PASSED"; SUBMITTING="SUBMITTING"
    ACKNOWLEDGED="ACKNOWLEDGED"; LIVE="LIVE"; PARTIALLY_FILLED="PARTIALLY_FILLED"; FILLED="FILLED"
    CANCELED="CANCELED"; EXPIRED="EXPIRED"; REJECTED="REJECTED"; UNKNOWN_RECONCILING="UNKNOWN_RECONCILING"

class DecisionAction(str, Enum):
    NO_POSITION="NO_POSITION"; OPEN_LONG="OPEN_LONG"; INCREASE_LONG="INCREASE_LONG"; REDUCE_LONG="REDUCE_LONG"; CLOSE_LONG="CLOSE_LONG"
    OPEN_SHORT="OPEN_SHORT"; INCREASE_SHORT="INCREASE_SHORT"; REDUCE_SHORT="REDUCE_SHORT"; CLOSE_SHORT="CLOSE_SHORT"
    REVERSE_LONG_TO_SHORT="REVERSE_LONG_TO_SHORT"; REVERSE_SHORT_TO_LONG="REVERSE_SHORT_TO_LONG"

class Blocker(str, Enum):
    BLOCKED_CONFIG="BLOCKED_CONFIG"; BLOCKED_API_PERMISSIONS="BLOCKED_API_PERMISSIONS"; BLOCKED_KRAKEN_STATUS="BLOCKED_KRAKEN_STATUS"
    BLOCKED_INSTRUMENT="BLOCKED_INSTRUMENT"; BLOCKED_MARKET_DATA="BLOCKED_MARKET_DATA"; BLOCKED_PRIVATE_DATA="BLOCKED_PRIVATE_DATA"
    BLOCKED_HISTORY="BLOCKED_HISTORY"; BLOCKED_NEWS="BLOCKED_NEWS"; BLOCKED_GEMINI="BLOCKED_GEMINI"; BLOCKED_STRATEGY="BLOCKED_STRATEGY"
    BLOCKED_EXPECTED_EDGE="BLOCKED_EXPECTED_EDGE"; BLOCKED_COST="BLOCKED_COST"; BLOCKED_LIQUIDITY="BLOCKED_LIQUIDITY"
    BLOCKED_MARGIN="BLOCKED_MARGIN"; BLOCKED_LEVERAGE="BLOCKED_LEVERAGE"; BLOCKED_RISK="BLOCKED_RISK"; BLOCKED_POSITION_SIZE="BLOCKED_POSITION_SIZE"
    BLOCKED_PORTFOLIO="BLOCKED_PORTFOLIO"; BLOCKED_ORDER_LIMIT="BLOCKED_ORDER_LIMIT"; BLOCKED_RECONCILIATION="BLOCKED_RECONCILIATION"
    CIRCUIT_BREAKER="CIRCUIT_BREAKER"; SAFE_STOP="SAFE_STOP"

class ErrorCode(str, Enum):
    DATA_ERROR="DATA_ERROR"; MARKET_DATA_STALE="MARKET_DATA_STALE"; PRIVATE_DATA_STALE="PRIVATE_DATA_STALE"; API_ERROR="API_ERROR"
    AUTH_ERROR="AUTH_ERROR"; PERMISSION_ERROR="PERMISSION_ERROR"; ORDER_REJECTED="ORDER_REJECTED"; INVALID_PRICE="INVALID_PRICE"
    INVALID_VOLUME="INVALID_VOLUME"; INSUFFICIENT_FUNDS="INSUFFICIENT_FUNDS"; INSUFFICIENT_MARGIN="INSUFFICIENT_MARGIN"
    LIQUIDATION_RISK="LIQUIDATION_RISK"; STALE_DECISION="STALE_DECISION"; DUPLICATE_ORDER_RISK="DUPLICATE_ORDER_RISK"
    NETWORK_AMBIGUITY="NETWORK_AMBIGUITY"; MODEL_ERROR="MODEL_ERROR"; BAD_SIGNAL="BAD_SIGNAL"; BAD_EXIT="BAD_EXIT"
    EXCESSIVE_SLIPPAGE="EXCESSIVE_SLIPPAGE"; EXCESSIVE_SPREAD="EXCESSIVE_SPREAD"; NEWS_MISINTERPRETATION="NEWS_MISINTERPRETATION"
    GEMINI_MISINTERPRETATION="GEMINI_MISINTERPRETATION"; REGIME_MISCLASSIFICATION="REGIME_MISCLASSIFICATION"

@dataclass(frozen=True)
class Instrument:
    venue: str; product_type: str; symbol: str; instrument_id: str; altname: str
    base: str; quote: str; status: str = "unknown"; contract_type: str = "spot"
    margin: bool = False; long_short: bool = False; leverage_levels: tuple[str,...] = ()
    max_leverage: Decimal = Decimal("1"); order_min: Decimal = Decimal("0"); cost_min: Decimal = Decimal("0")
    lot_precision: int = 8; price_precision: int = 8; tick_size: Decimal = Decimal("0")
    position_limit_long: Decimal = Decimal("0"); position_limit_short: Decimal = Decimal("0")
    margin_class: str = ""; collateral: str = ""; funding: Decimal = Decimal("0")
    fee_model: str = ""; updated_at: float = 0.0; metadata: dict[str,Any] = field(default_factory=dict)

@dataclass
class Signal:
    symbol: str; direction: str; long_score: Decimal; short_score: Decimal
    expected_return: Decimal; confidence: Decimal; uncertainty: Decimal; regime: str
    reasons: list[str] = field(default_factory=list); features: dict[str,Any] = field(default_factory=dict)
    model_version: str = "ensemble-v1"

@dataclass
class Decision:
    cycle_id: str; symbol: str; action: DecisionAction; side: str
    target_notional: Decimal; current_notional: Decimal; delta_notional: Decimal
    expected_edge: Decimal; confidence: Decimal; uncertainty: Decimal; leverage: Decimal; margin: bool
    status: str = "NO_ACTION"; blocker: str = ""; strategy_version: str = "strategy-v1"; model_version: str = "ensemble-v1"
    decision_id: str = field(default_factory=lambda: new_id("decision")); intent_id: str | None = None; config_hash: str = ""
    evidence: dict[str,Any] = field(default_factory=dict)
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self),sort_keys=True,default=str).encode()).hexdigest()

@dataclass
class OrderIntent:
    cycle_id: str; decision_id: str; symbol: str; side: str; volume: Decimal
    order_type: str; price: Decimal | None; leverage: Decimal; margin: bool; reduce_only: bool
    strategy_version: str; model_version: str; config_hash: str
    intent_id: str = field(default_factory=lambda: new_id("intent"))
    client_order_id: str = field(default_factory=lambda: new_id("client"))

@dataclass
class MarketSnapshot:
    symbol: str; bid: Decimal; ask: Decimal; last: Decimal; volume: Decimal
    timestamp: float; depth_bid: Decimal = Decimal("0"); depth_ask: Decimal = Decimal("0")
    imbalance: Decimal = Decimal("0")
    @property
    def spread(self) -> Decimal:
        return (self.ask-self.bid)/self.last if self.last>0 else Decimal("1")

def unix_now(): return time.time()

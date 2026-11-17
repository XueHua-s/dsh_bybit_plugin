"""Offline gross-risk veto over server-owned snapshots, never execution authorization.

Call evaluate(intent, context, policy). Only the intent may originate from an agent;
context, policy, timestamps, instrument estimates and correlations belong to the
engine/operator. Every notional/depth/equity/margin amount uses common fresh USDT
valuation; the caller owns mark/FX provenance and complete private reconciliation.

Each position leg and reservation counts as one concurrent position and consumes
gross exposure; BUY/SELL never net and reductions get no bypass. Position limits
aggregate by symbol; account/leverage limits aggregate all symbols. Concentration
and correlated-cluster limits use equity as denominator. Correlation uses absolute
coefficients, complete pair coverage and connected clusters. Fee-buffered pending
margin is charged in addition to reported available margin, conservatively.

Policy equality at maxima is allowed except daily loss/drawdown, which freeze at
their threshold. Snapshot age equal to TTL is allowed; approved-plan expiry is the
earliest required timestamp plus TTL. Atomic reservation, durable audit, rejection
notification, emergency cancellations and sole Nautilus submission are caller work.
"""

from .evaluator import evaluate
from .models import (
    AccountSnapshot,
    ApprovedPlan,
    Correlation,
    Environment,
    Exposure,
    MarketSnapshot,
    OrderIntent,
    RiskContext,
    RiskDecision,
    RiskPolicy,
    Side,
)

__all__ = [
    "AccountSnapshot",
    "ApprovedPlan",
    "Correlation",
    "Environment",
    "Exposure",
    "MarketSnapshot",
    "OrderIntent",
    "RiskContext",
    "RiskDecision",
    "RiskPolicy",
    "Side",
    "evaluate",
]

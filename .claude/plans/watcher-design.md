# Watcher Design for Post-Earnings Trades

**Created**: 2026-03-30
**Status**: DESIGN — approved architecture, not yet implemented

---

## Core Decision

The watcher should be **mostly deterministic**, not a full-time agent.

- **Opus** analyzes the 8-K and decides the trade
- **Opus also outputs a MonitoringSpec**
- **Watcher** monitors live conditions against that spec
- **Primary agent** is only invoked when watcher decides a re-review is needed
- **Execution/risk layer** remains deterministic and separate

---

## Main Principle

Do **not** make the watcher decide whether "market conditions changed."

Instead, make it decide whether:

- the **trade thesis may be weakening**
- the **trade may be invalidated**
- the **trade now requires review**

So the watcher is not a market-intelligence engine.
It is a **thesis drift / downside / stale-thesis detector**.

---

## What MonitoringSpec Should Contain

MonitoringSpec should be produced at trade creation by Opus.

Minimal version:

- **hard triggers**
- **soft triggers**
- **scheduled reviews**
- **fallback rules**

### Hard Triggers
Immediate wake-up conditions.

Examples:
- break of post-earnings low/high
- guidance-related negative follow-up
- sector repricing on same driver
- unexpected adverse move beyond threshold

### Soft Triggers
Warning signs that accumulate.

Examples:
- no follow-through after expected time
- relative weakness vs sector/index
- volatility expansion against position
- deteriorating microstructure

### Scheduled Reviews
Forced re-checks even if nothing obvious happened.

Examples:
- 30 minutes
- 2 hours
- next open
- end of day

### Fallback Rules
Generic safety net in case Opus missed something important.

Examples:
- adverse excursion beyond generic threshold
- no progress by deadline
- new event in ticker / sector / macro domain
- unusual behavior relative to normal post-earnings pattern

---

## Most Important Finalized Insight

The weakest part of the design is **MonitoringSpec incompleteness**.

If Opus misses the true failure mode, a deterministic watcher may watch the wrong things.

### Final Fix
Every trade must include:
- **Opus-specific rules**
- plus a **generic fallback layer**

This prevents blindness to uncaptured failure modes.

---

## Final Watcher Role

Watcher should do only this:

1. load trade MonitoringSpec
2. listen to market/news/order/time events
3. compare events to MonitoringSpec
4. score severity
5. decide:
   - ignore
   - batch for later
   - wake primary now

That is all.

---

## Should Watcher Be Deterministic?

### Final Answer
Yes — **90-95% deterministic**.

Use LLM only optionally for **ambiguous text triage**, such as unclear headlines.

### Good Use of Tiny Model
- headline arrived
- deterministic filter says "maybe relevant"
- small model classifies:
  - irrelevant
  - maybe relevant / batch
  - wake now

### Bad Use
- having an LLM continuously "watch markets"
- having the watcher act like a second primary agent

So the finalized design is:

- **watcher = deterministic**
- **optional tiny LLM triage = only for ambiguous text**
- **primary agent = reactive, resumable, deeper reasoning**

---

## How APIs Fit In

APIs like **IBKR** and **Polygon** do not directly tell you "market regime changed."

They provide raw or semi-structured streams:
- prices
- quotes
- aggregates
- news
- order events
- scanners
- portfolio updates

So the watcher should use APIs to detect that **something happened**, not to conclude what it means.

**Data sources for watcher (2026-03-30):**
- **IBKR** (funded account, $0/mo): real-time streaming prices, portfolio state, order events via existing MCP tools
- **Benzinga** (via existing pipeline): news headlines for text triage
- **Polygon** (current subscription): delayed/historical aggregates as needed

---

## Minimal Architecture

### 1. Opus at Trade Creation
Outputs:
- thesis
- trade decision
- MonitoringSpec

### 2. Deterministic Watcher
Continuously monitors:
- price/path deviations
- event arrivals
- order/risk state
- time checkpoints

### 3. Optional Tiny Text Triage
Used only for ambiguous news relevance.

### 4. Primary Agent
Resumable and reactive.
Invoked only when watcher says review is needed.

### 5. Deterministic Execution Guard
Owns broker/risk decisions.
Primary agent does not directly own execution.

---

## Clean Operating Logic

### When Watcher Wakes Primary
- hard trigger fires
- multiple soft triggers accumulate
- scheduled review time arrives
- fallback rule fires

### When Watcher Does Not Wake Primary
- event is irrelevant
- event is weak and below threshold
- event is queued for batch review

---

## CRM Q4 FY2025 Retroactive Application

How this design would have handled the CRM trade (from predictionLearnings.md):

**MonitoringSpec Opus would have output:**
- Hard trigger: XLK pre-market < -2% from filing snapshot (macro was already hostile at filing)
- Hard trigger: CRM breaks below prior close ($307.33)
- Soft trigger: gap fades > 50% within first 30 minutes
- Soft trigger: CRM underperforming XLK by > 2% intraday
- Scheduled review: 8 AM pre-market, open+30min, EOD
- Fallback: adverse excursion > 3% from entry, no progress after 2 hours

**What would have happened:**
- Feb 27, ~8 AM: XLK futures showing -2%+ → **hard trigger fires** → wake primary
- Primary reviews: "macro deteriorating severely, thesis intact but environment hostile" → **exit at +2-3%**
- Even without the Opus-specific hard trigger, the 8 AM **scheduled review** would have caught it
- Even without that, the **fallback** "adverse excursion > 3%" would have fired by midday

Result: **+2-3% captured instead of -4% loss**.

---

## One-Line Summary

**Opus decides the trade and what failure looks like; the watcher deterministically checks for that failure and only then wakes the primary agent.**

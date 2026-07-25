# Restore Trading Cognition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the complete "尼克｜交易性格" trading-cognition workflow inside the unified Content Production page without removing the legacy page or changing the distilled knowledge base.

**Architecture:** Keep `app.trading_cognition` and the existing FastAPI route as the single generation implementation. Extend the unified Streamlit API adapter for direct mode, then rebuild the new trading section around the same request and response contract used by the legacy page.

**Tech Stack:** Python, Streamlit, FastAPI, SQLAlchemy, SQLite, unittest

## Global Constraints

- Preserve the existing "尼克｜交易性格（公开内容蒸馏）" knowledge cards and source notice.
- Preserve the legacy standalone trading-cognition page for compatibility.
- Support remote FastAPI mode and direct Streamlit mode.
- Restore question, platform, duration, LLM toggle, structured content package, source notice, and matched knowledge evidence.
- Keep the safety boundary that the module does not provide trading signals or investment advice.

---

### Task 1: Unified API Adapter

**Files:**
- Modify: `ui/core/api_client.py`
- Test: `tests/test_trading_cognition.py`

**Interfaces:**
- Consumes: `app.trading_cognition.service.generate_trading_cognition(db, question, duration, platform, use_llm, knowledge_limit)`
- Produces: `_direct_request("POST", "/api/trading-cognition/generate", payload, None) -> dict`

- [x] **Step 1: Write the failing direct-mode API test**

Add a test that creates a temporary SQLite session, calls the unified direct adapter with `use_llm=False`, and asserts that the response contains `script_text`, `matched_knowledge`, and the "尼克｜交易性格" source identity.

- [x] **Step 2: Run the focused test and verify RED**

Run: `python -m unittest tests.test_trading_cognition.TradingCognitionTests.test_unified_api_client_supports_direct_trading_generation -v`

Expected: failure with `Unsupported direct request: POST /api/trading-cognition/generate`.

- [x] **Step 3: Add the direct route**

Import `generate_trading_cognition` inside `_direct_request` and dispatch the existing payload fields without changing their defaults.

- [x] **Step 4: Run the focused test and verify GREEN**

Run the focused unittest again and expect `OK`.

### Task 2: Unified Trading Cognition UI

**Files:**
- Modify: `ui/modules/content_production.py`
- Modify: `ui/core/state.py`

**Interfaces:**
- Consumes: `api_request("POST", "/api/trading-cognition/generate", payload=...)`
- Produces session values: `content.trading.result`, `content.trading.matches`, `content.trading.source_notice`, `content.trading.source_name`

- [x] **Step 1: Restore the complete input workflow**

Show the original question field, all five platforms, all five durations, the LLM toggle, validation, spinner, and enabled generation button.

- [x] **Step 2: Restore the complete output workflow**

Render the structured JSON content package, download action, source identity and notice, plus an expander containing each matched card's title, belief, and action rule.

- [x] **Step 3: Preserve results across Streamlit reruns**

Initialize dedicated trading-cognition state values in `ui/core/state.py` and update them only after successful generation.

### Task 3: Verification

**Files:**
- Test: `tests/test_trading_cognition.py`

**Interfaces:**
- Consumes: completed direct adapter and unified UI
- Produces: regression evidence for backend generation and application importability

- [x] **Step 1: Run trading-cognition tests**

Run: `python -m unittest tests.test_trading_cognition -v`

Expected: all tests pass.

- [x] **Step 2: Run syntax compilation**

Run: `python -m compileall app ui tests`

Expected: command exits with status 0.

- [x] **Step 3: Smoke-test the local application**

Run the Streamlit AppTest regression with a local rules-mode response and confirm the structured package, source notice, and matched evidence are visible.

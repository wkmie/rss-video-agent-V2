# X Key Accounts Collection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Import the supplied 45 X accounts and restore a working key-account feed that automatically fetches once per Streamlit session, supports manual refresh, stores posts in the existing hot-feed database, and displays posts by account.

**Architecture:** Add a versioned account configuration and a dedicated `XKeyAccountsCollector` beside the existing keyword collector. Reuse the current `/api/web3-hot/fetch-now` and `/api/web3-hot/list` contracts, extend the unified direct API adapter, and replace the new UI placeholder with a session-safe account feed.

**Tech Stack:** Python 3.9, FastAPI, Streamlit, SQLAlchemy, SQLite, HTTPX, unittest

## Global Constraints

- Preserve the existing keyword-based `XRecentSearchCollector`.
- Use `X_BEARER_TOKEN`; never store the token in source control.
- Keep every Recent Search query at or below 512 characters.
- Do not add a background scheduler or filtered-stream connection.
- Automatic collection runs at most once per Streamlit session; manual refresh is unrestricted.
- Store and score posts through the existing `Web3HotItem` pipeline.
- One failed X query batch must not prevent later batches from running.

---

### Task 1: Account Configuration and Query Batching

**Files:**
- Create: `config/x_key_accounts.json`
- Modify: `app/services/web3_hot_collectors/social.py`
- Create: `tests/test_x_key_accounts.py`

**Interfaces:**
- Produces: `load_x_key_accounts() -> list[dict[str, Any]]`
- Produces: `build_account_queries(accounts: list[dict[str, Any]], max_length: int = 512) -> list[str]`

- [x] **Step 1: Write failing configuration and batching tests**

Tests assert that 45 valid accounts load, usernames contain only `[A-Za-z0-9_]`, disabled accounts are excluded from queries, every enabled account appears once, and every query is at most 512 characters.

- [x] **Step 2: Run tests and verify RED**

Run: `.venv/bin/python -m unittest tests.test_x_key_accounts.XKeyAccountConfigurationTests -v`

Expected: import failure because the loader and batching functions do not exist.

- [x] **Step 3: Add normalized JSON configuration and minimal loader**

Create `config/x_key_accounts.json` with `username`, `display_name`, `region`, `priority`, and `enabled`. Implement validation and query batching using parenthesized `from:` clauses plus `-is:retweet`.

- [x] **Step 4: Run tests and verify GREEN**

Run the focused test class and expect all tests to pass.

### Task 2: X Key Account Collector

**Files:**
- Modify: `app/services/web3_hot_collectors/social.py`
- Modify: `app/services/web3_hot_collectors/__init__.py`
- Modify: `config/web3_hot_sources.json`
- Test: `tests/test_x_key_accounts.py`

**Interfaces:**
- Consumes: `load_x_key_accounts`, `build_account_queries`
- Produces: `XKeyAccountsCollector.fetch(source_type, keyword) -> HotCollectorResult`

- [x] **Step 1: Write failing response parsing and batch-isolation tests**

Mock HTTPX responses with `includes.users`; assert the collector uses the username in `author`, `source_name`, and post URL, maps public metrics, and continues after a failed batch.

- [x] **Step 2: Run collector tests and verify RED**

Expected: failure because `XKeyAccountsCollector` is not defined or registered.

- [x] **Step 3: Implement the collector and register the source**

Request `expansions=author_id`, map user IDs to usernames, convert each post to `HotFeedItem`, and append concise 401/403/429 or batch errors without raising out of the collector.

- [x] **Step 4: Run collector tests and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_x_key_accounts -v`

Expected: all account and collector tests pass.

### Task 3: Unified Direct API Support

**Files:**
- Modify: `ui/core/api_client.py`
- Test: `tests/test_x_key_accounts.py`

**Interfaces:**
- Produces direct dispatch for:
  - `POST /api/web3-hot/fetch-now`
  - `GET /api/web3-hot/list`

- [x] **Step 1: Write a failing direct list test**

Patch the session factory with an in-memory SQLite database and assert `_direct_request("GET", "/api/web3-hot/list", ...)` returns an `items` list.

- [x] **Step 2: Run the direct API test and verify RED**

Expected: `Unsupported direct request`.

- [x] **Step 3: Add minimal Web3 fetch/list dispatch**

Call `fetch_and_store_hot_items` for POST and `list_hot_items` for GET, preserving current defaults and filter parameters.

- [x] **Step 4: Run the direct API test and verify GREEN**

Run the focused test and expect `OK`.

### Task 4: Session-Safe Streamlit Account Feed

**Files:**
- Modify: `ui/core/state.py`
- Modify: `ui/modules/information_hotspots.py`
- Create: `tests/test_x_key_accounts_ui.py`

**Interfaces:**
- Consumes:
  - `api_request("POST", "/api/web3-hot/fetch-now", payload={"source_type": "x_key_accounts"})`
  - `api_request("GET", "/api/web3-hot/list", params=...)`
- Produces session keys:
  - `info.x.accounts.auto_fetch_attempted`
  - `info.x.accounts.fetch_result`
  - `info.x.accounts.items`

- [x] **Step 1: Write a failing Streamlit page test**

Use `AppTest` with a fake API adapter. Assert the first render fetches once, a rerun does not fetch again, manual refresh triggers a second fetch, and account groups show metrics and links.

- [x] **Step 2: Run the UI test and verify RED**

Expected: placeholder UI does not call the API and has no active refresh button.

- [x] **Step 3: Implement metrics, filters, automatic fetch, manual refresh, and grouped display**

Set the automatic-attempt flag before calling the API, always reload the list after a fetch attempt, filter locally by region/account, and render posts under one expander per username.

- [x] **Step 4: Run the UI test and verify GREEN**

Run: `.venv/bin/python -m unittest tests.test_x_key_accounts_ui -v`

Expected: all UI tests pass.

### Task 5: Regression Verification

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documents the new `x_key_accounts` source type and page behavior.

- [x] **Step 1: Update documentation**

Describe automatic session-level collection, manual refresh, account configuration path, and the fact that X API billing still applies.

- [x] **Step 2: Run all tests**

Run: `.venv/bin/python -m unittest discover -s tests -v`

Expected: zero failures.

- [x] **Step 3: Compile Python sources**

Run: `PYTHONPYCACHEPREFIX=/tmp/rss-video-agent-pycache .venv/bin/python -m compileall -q app ui tests`

Expected: exit code 0.

- [x] **Step 4: Check repository diff**

Run: `git diff --check`

Expected: no whitespace errors and no key material in added files.

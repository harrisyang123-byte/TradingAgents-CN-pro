## ADDED Requirements

### Requirement: Fund NAV lookup via instrument_type routing

`PortfolioService._get_last_price` SHALL accept an `instrument_type` parameter and route `"fund"` type to AKShare fund NAV lookup.

#### Scenario: Fund position gets NAV as last_price

- **WHEN** `_get_last_price("270042", "CN", "fund")` is called
- **THEN** the system fetches the latest NAV from AKShare `fund_open_fund_info_em(symbol="270042")`
- **AND** returns the `单位净值` column value as a float
- **AND** caches the result in `fund_nav_cache` collection with 24h TTL

#### Scenario: Stock position unaffected

- **WHEN** `_get_last_price("600519", "CN")` is called (no instrument_type, default "stock")
- **THEN** the system routes to existing stock price lookup (market_quotes / stock_basic_info)
- **AND** fund logic is NOT triggered

#### Scenario: ETF position routes to stock branch

- **WHEN** `_get_last_price("159919", "CN", "etf")` is called
- **THEN** the system routes to existing CN stock price lookup
- **AND** fund logic is NOT triggered

### Requirement: Fund NAV 24h caching

The system SHALL cache fund NAV results in MongoDB `fund_nav_cache` collection and expire the cache at 21:00 Beijing time daily, aligned with fund NAV publishing schedule (~20:00-22:00).

#### Scenario: Cache hit before 21:00 cut-off

- **WHEN** `_get_fund_nav("270042")` is called at 14:00 Beijing time
- **AND** a cache document exists from the previous day after 21:00
- **THEN** the cached `nav` value is returned immediately
- **AND** AKShare is NOT called

#### Scenario: Cache expired after 21:00 cut-off

- **WHEN** `_get_fund_nav("270042")` is called at 21:30 Beijing time
- **AND** the cache document was created before 21:00 today
- **THEN** the system calls AKShare for fresh NAV (today's published NAV)
- **AND** updates the cache document with new `nav`, `nav_date`, and `cached_at`
- **AND** returns the fresh NAV

#### Scenario: No cache, first fetch

- **WHEN** `_get_fund_nav("270042")` is called and no cache document exists
- **THEN** the system calls AKShare for NAV
- **AND** creates a new cache document
- **AND** returns the fetched NAV

### Requirement: Graceful degradation on AKShare failure

The system SHALL gracefully handle AKShare failures by falling back to cached values or returning `None`.

#### Scenario: AKShare fails, cached value exists

- **WHEN** `_get_fund_nav("270042")` is called and AKShare raises an exception
- **AND** a cache document exists (even if expired)
- **THEN** the cached `nav` value is returned as fallback
- **AND** the error is logged at warning level

#### Scenario: AKShare fails, no cache

- **WHEN** `_get_fund_nav("270042")` is called and AKShare raises an exception
- **AND** no cache document exists
- **THEN** `None` is returned
- **AND** the error is logged at warning level

#### Scenario: Fund code not found in AKShare

- **WHEN** `_get_fund_nav("999999")` is called and AKShare returns empty or invalid data
- **THEN** `None` is returned
- **AND** no cache document is written

### Requirement: NAV value validation

The system SHALL validate fetched NAV values before caching to prevent corrupted data.

#### Scenario: NAV is zero or negative

- **WHEN** AKShare returns a NAV value of 0 or NaN for fund "270042"
- **THEN** the value is NOT written to cache
- **AND** `None` is returned

#### Scenario: Same nav_date, non-trading day

- **WHEN** `_get_fund_nav("270042")` is called on a weekend
- **AND** AKShare returns the same `nav_date` as already cached
- **THEN** only `cached_at` is updated (extending expiry to next 21:00 cut-off)
- **AND** the cached `nav` value is preserved unchanged

### Requirement: Exception isolation

The system SHALL isolate `_get_fund_nav` exceptions so that a single fund lookup failure does not abort the entire `get_portfolio_summary` call.

#### Scenario: One fund fails, others succeed

- **WHEN** `get_portfolio_summary` processes 3 positions (2 stock, 1 fund)
- **AND** the fund's AKShare call raises a network timeout
- **THEN** the fund position gets `last_price=None`
- **AND** the 2 stock positions complete normally
- **AND** the overall summary is returned successfully

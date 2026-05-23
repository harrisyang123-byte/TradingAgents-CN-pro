# Proposal: Fund → Tier 2 Data Flow Fix

## Why

Tier 1 fund analysis produces reports stored in `analysis_reports`, but Tier 2's `_prepare_tier1_reports` queries `analysis_results` (a dead collection with no writers). Fund positions are invisible to the portfolio advisor — L3 agents and CIO have no fund-specific context for decision-making.

Additionally, the PE percentile pipeline tries to look up fund codes as stocks, wasting API calls.

## What

1. Fix `_prepare_tier1_reports` to query `analysis_reports` and extract fund-specific fields
2. Inject fund context into L3 Analyst and Strategist prompts
3. Add fund decision criteria to CIO prompt
4. Skip fund/ETF codes in PE pipeline

## Scope

Backend-only. No frontend changes. No new data sources.

## Verification

- `_prepare_tier1_reports` returns fund reports with correct fields
- PE pipeline skips fund codes gracefully
- Pure stock portfolios unaffected (regression)
- Fund-only portfolios get fund-specific analysis in L3/CIO output

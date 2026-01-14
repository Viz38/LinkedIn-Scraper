# CHANGELOG
All notable changes to this project are documented here.

## [2026-01-14] Switch to DDGS Library for Searching
- [Search Snippet/scrape_fast.py]: Updated to use `ddgs` library instead of Playwright-based search.
- [Search Snippet/scrape_fast.py]: Implemented logic to retry rows previously marked with "Error".
- Reason: Playwright encountered consistent `net::ERR_CONNECTION_TIMED_OUT` errors on DuckDuckGo, likely due to browser-level bot detection. `ddgs` library proved to be more reliable and faster.

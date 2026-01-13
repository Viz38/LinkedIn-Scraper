import asyncio
import pandas as pd
import sys
import os
from pathlib import Path
import random
import urllib.parse

# Add project root to path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from linkedin_scraper.core.browser import BrowserManager
from playwright.async_api import Page

async def search_duckduckgo(page: Page, query: str):
    """
    Search DuckDuckGo directly for the URL without quotes.
    """
    encoded = urllib.parse.quote(query)
    url = f"https://duckduckgo.com/?q={encoded}"
    
    try:
        await page.goto(url)
        # Random wait for human-like behavior
        await asyncio.sleep(random.uniform(2.5, 4.0))
        
        result_selector = "article[data-testid='result']"
        
        count = await page.locator(result_selector).count()
        if count == 0:
            return None, None, None

        # Iterate to find relevant result
        for i in range(min(count, 5)):
            res = page.locator(result_selector).nth(i)
            title = await res.locator("h2").inner_text()
            
            display_url = ""
            try:
                url_el = res.locator("a[data-testid='result-extras-url-link']")
                if await url_el.count() > 0:
                    display_url = await url_el.inner_text()
            except:
                pass
            
            snippet = ""
            try:
                snippet = await res.locator("div[data-testid='result-snippet']").inner_text()
            except:
                pass
            
            # Relevance check: Ensure LinkedIn is mentioned in title, URL, or snippet
            if "linkedin" in title.lower() or "linkedin" in display_url.lower() or "linkedin" in snippet.lower():
                return title, display_url, snippet
        
        return None, None, None
    except Exception as e:
        print(f"   Error: {e}")
        return None, None, None

async def main():
    input_file = current_dir / "test_founder.xlsx"
    if not input_file.exists():
        print(f"❌ File not found: {input_file}")
        return
        
    df = pd.read_excel(input_file)
    target_column = 'Search Result Detail'
    
    if target_column not in df.columns:
        df[target_column] = None

    rows_to_process = []
    for idx, row in df.iterrows():
        # Process if empty or previously failed
        if pd.isna(row[target_column]) or row[target_column] == "" or "No Relevant Result" in str(row[target_column]):
            rows_to_process.append(idx)

    if not rows_to_process:
        print("✅ All entries already processed.")
        return

    print(f"🚀 Starting Optimized Search for {len(rows_to_process)} profiles...")

    async with BrowserManager(headless=False) as browser:
        page = browser.page
        
        for i, idx in enumerate(rows_to_process):
            url = df.at[idx, 'LinkedIn URL']
            print(f"🔍 [{i+1}/{len(rows_to_process)}] Searching: {url}")
            
            try:
                title, d_url, snippet = await search_duckduckgo(page, url)
                
                if title:
                    # Clean the snippet of extra newlines
                    snippet = snippet.replace('\n', ' ').strip()
                    combined = f"{title}\n{d_url}\n{snippet}"
                    df.at[idx, target_column] = combined
                    print(f"   ✅ Success: {title[:40]}...")
                else:
                    print("   ⚠️ No relevant result found.")
                    df.at[index, target_column] = "No Relevant Result Found"
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                df.at[idx, target_column] = f"Error: {e}"
            
            # Save progress
            df.to_excel(input_file, index=False)
            
            # Delay to mimic browsing
            await asyncio.sleep(random.uniform(2.0, 4.0))

    print("\n" + "="*60)
    print(f"✅ Complete. Results saved in {input_file}")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

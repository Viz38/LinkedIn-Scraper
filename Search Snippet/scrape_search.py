import asyncio
import pandas as pd
import sys
import os
from pathlib import Path
import random
import urllib.parse
from playwright.async_api import async_playwright

current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

async def search_duckduckgo(page, query):
    """
    Search DuckDuckGo directly for the URL without quotes.
    """
    encoded = urllib.parse.quote(query)
    url = f"https://duckduckgo.com/?q={encoded}"
    
    try:
        await page.goto(url, timeout=30000)
        await asyncio.sleep(random.uniform(2.0, 3.5))
        
        result_selector = "article[data-testid='result']"
        try:
            await page.wait_for_selector(result_selector, timeout=10000)
        except:
            pass

        count = await page.locator(result_selector).count()
        if count == 0:
            return None, None, None

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
            
            if "linkedin" in title.lower() or "linkedin" in display_url.lower() or "linkedin" in snippet.lower():
                return title, display_url, snippet
        
        return None, None, None
    except Exception as e:
        print(f"   Error: {e}")
        return None, None, None

async def main():
    input_file = current_dir / "test_founder.xlsx"
    if not input_file.exists(): return
        
    df = pd.read_excel(input_file, engine='openpyxl')
    target_column = 'Search Result Detail'
    
    # 🧹 Clean column
    df[target_column] = None

    limit = 10
    rows_to_process = df.index[:limit]

    print(f"🚀 Starting Headless Test for first {limit} profiles...")

    async with async_playwright() as p:
        # HEADLESS=TRUE as requested
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        for i, idx in enumerate(rows_to_process):
            url = df.at[idx, 'LinkedIn URL']
            print(f"🔍 [{i+1}/{limit}] Searching: {url}")
            
            title, d_url, snippet = await search_duckduckgo(page, url)
            
            if title:
                snippet = snippet.replace('\n', ' ').strip()
                combined = f"{title}\n{d_url}\n{snippet}"
                df.at[idx, target_column] = combined
                print(f"   ✅ Success: {title[:40]}...")
            else:
                df.at[idx, target_column] = "No Relevant Result Found"
                print("   ⚠️ No relevant result found.")
            
            # Save after each row to avoid loss
            df.to_excel(input_file, index=False)
            await asyncio.sleep(random.uniform(2.0, 4.0))

        await browser.close()

    print(f"✅ Complete. Results saved in {input_file}")

if __name__ == "__main__":
    asyncio.run(main())

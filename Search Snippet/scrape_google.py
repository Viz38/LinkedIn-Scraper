import asyncio
import pandas as pd
import sys
import os
from pathlib import Path
import urllib.parse
import random

# Add project root to path to import linkedin_scraper
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root))

from linkedin_scraper.core.browser import BrowserManager
from playwright.async_api import Page

async def search_google(page: Page, query: str):
    """
    Search Google and extract the first result's title, URL, and snippet.
    """
    encoded_query = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded_query}"
    
    try:
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(random.uniform(2, 4)) # Human-like wait

        # Handle "Before you continue" cookie consent (English/European)
        try:
            # Look for common consent buttons
            consent_buttons = page.locator("button, div[role='button']").filter(has_text=pd.compile(r"^(Accept all|I agree|Reject all)$", flags=pd.re.IGNORECASE))
            if await consent_buttons.count() > 0:
                await consent_buttons.first.click()
                await asyncio.sleep(1)
        except:
            pass

        # Wait for the results to load
        try:
            await page.wait_for_selector("div#search", timeout=5000)
        except:
            print("   ⚠️ specific #search container not found, checking generic...")

    except Exception as e:
        print(f"   Error loading Google: {e}")
        return None, None, None

    # Debug: Take a screenshot if we suspect failure
    if await page.locator("div.g").count() == 0:
        await page.screenshot(path="debug_google_failure.png")
        print("   📸 Saved debug_google_failure.png (No results found)")
        
        # Check for CAPTCHA
        if await page.locator("text='Our systems have detected unusual traffic'").count() > 0:
            print("   ⛔ CAPTCHA detected!")
            return None, None, None

    # Selector for the first organic result
    # We look for 'div.g' which is the standard container for a result
    results = page.locator("div.g")
    
    count = await results.count()
    if count == 0:
        return None, None, None

    # Get the first VALID organic result (sometimes div.g is used for other widgets)
    first_result = None
    for i in range(count):
        res = results.nth(i)
        if await res.is_visible():
            # Must have a link and a title
            if await res.locator("a").count() > 0 and await res.locator("h3").count() > 0:
                first_result = res
                break
    
    if not first_result:
        return None, None, None

    # 1. Extract Title
    title = ""
    try:
        title = await first_result.locator("h3").first.inner_text()
    except:
        pass

    # 2. Extract Display URL
    display_url = ""
    try:
        # Try to find the cite tag or the breadcrumb
        display_url = await first_result.locator("cite").first.inner_text()
    except:
        try:
            display_url = await first_result.locator("a").first.get_attribute("href")
        except:
            pass

    # 3. Extract Snippet
    snippet = ""
    try:
        # Common classes for snippet text
        # VwiC3b: Standard snippet
        # yDmY0d: Sometimes used
        snippet_el = first_result.locator("div.VwiC3b").first
        if await snippet_el.count() > 0:
            snippet = await snippet_el.inner_text()
        else:
            # Fallback: look for any text block that isn't the title or url
            # This is heuristic and might be messy
            snippet_el = first_result.locator("div[style*='-webkit-line-clamp']").first
            if await snippet_el.count() > 0:
                snippet = await snippet_el.inner_text()
    except:
        pass

    return title, display_url, snippet

async def main():
    input_file = current_dir / "test_founder.xlsx"
    if not input_file.exists():
        print(f"❌ Input file not found: {input_file}")
        return

    print(f"📂 Reading {input_file}...")
    df = pd.read_excel(input_file)

    target_column = 'Search Result Detail'
    if target_column not in df.columns:
        df[target_column] = None

    print(f"🚀 Starting Google search for {len(df)} profiles...")
    
    # Use HEADLESS=FALSE to avoid simple bot detection
    async with BrowserManager(headless=False) as browser:
        page = browser.page
        
        for index, row in df.iterrows():
            linkedin_url = row['LinkedIn URL']
            
            if pd.isna(linkedin_url) or str(linkedin_url).strip() == "":
                continue
                
            if pd.notna(row[target_column]) and str(row[target_column]) != "":
                continue

            print(f"🔍 [{index+1}/{len(df)}] Searching Google: {linkedin_url}")
            
            try:
                title, d_url, snippet = await search_google(page, linkedin_url)
                
                if title:
                    # Format: Title \n URL \n Snippet
                    combined_result = f"{title}\n{d_url}\n{snippet}"
                    df.at[index, target_column] = combined_result
                    print(f"   ✅ Success: {title[:30]}...")
                else:
                    print("   ⚠️ No result found")
                    df.at[index, target_column] = "No Result Found"

                if index % 5 == 0:
                    df.to_excel(input_file, index=False)

            except Exception as e:
                print(f"   ❌ Error: {e}")
            
            # Longer random wait to be safe
            await asyncio.sleep(random.uniform(3, 6))

    df.to_excel(input_file, index=False)
    print("\n" + "="*60)
    print(f"✅ Complete. Results in '{target_column}' column.")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
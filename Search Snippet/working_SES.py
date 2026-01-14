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

async def search_worker(context, semaphore, idx, url, df, target_column):
    async with semaphore:
        # Stagger start
        await asyncio.sleep(random.uniform(0.1, 3.0))
        
        page = await context.new_page()
        try:
            encoded = urllib.parse.quote(str(url))
            search_url = f"https://duckduckgo.com/?q={encoded}"
            
            # 60s timeout
            await page.goto(search_url, timeout=60000)
            
            # Robust wait (Increased for safety)
            await asyncio.sleep(random.uniform(6.0, 12.0))
            
            result_selector = "article[data-testid='result']"
            try:
                await page.wait_for_selector(result_selector, timeout=20000)
            except:
                pass

            count = await page.locator(result_selector).count()
            if count == 0:
                df.at[idx, target_column] = "No Result Found"
                await page.close()
                return

            found = False
            for i in range(min(count, 5)):
                res = page.locator(result_selector).nth(i)
                title = await res.locator("h2").inner_text()
                
                display_url = ""
                try:
                    display_url = await res.locator("a[data-testid='result-extras-url-link']").inner_text()
                except:
                    pass
                
                snippet = ""
                try:
                    snippet = await res.locator("div[data-testid='result-snippet']").inner_text()
                except:
                    pass
                
                if "linkedin" in title.lower() or "linkedin" in display_url.lower() or "linkedin" in snippet.lower():
                    combined = f"{title}\n{display_url}\n{snippet}"
                    df.at[idx, target_column] = combined
                    found = True
                    break
            
            if not found:
                 df.at[idx, target_column] = "No Relevant Result"

        except Exception as e:
            df.at[idx, target_column] = f"Error: {e}"
        finally:
            await page.close()

async def process_sheet(sheet_name, input_file, browser_context):
    print(f"\n📂 Reading {input_file} (Sheet: {sheet_name})...")
    try:
        df = pd.read_excel(input_file, sheet_name=sheet_name, engine='openpyxl')
    except Exception as e:
        print(f"   ❌ Error reading sheet {sheet_name}: {e}")
        return

    target_column = 'Search Result Detail'
    if target_column not in df.columns:
        df[target_column] = None

    rows_to_process = []
    for idx, row in df.iterrows():
        # Smart column detection
        url_col = 'LinkedIn URL' if 'LinkedIn URL' in df.columns else df.columns[0]
        url = row[url_col]
        
        if pd.isna(url) or str(url).strip() == "": continue
        if pd.notna(row[target_column]): continue # Skip already done
        
        rows_to_process.append((idx, url))

    if not rows_to_process:
        print(f"   ✅ Sheet {sheet_name} is already complete.")
        return

    import time

    print(f"🚀 Starting Search for {len(rows_to_process)} profiles in {sheet_name}...")
    
    # Reduced concurrency for safety (aiming for ~6 hours total)
    semaphore = asyncio.Semaphore(15) 
    batch_size = 15
    
    output_filename = f"live_processed_{sheet_name}.xlsx"
    output_file = current_dir / output_filename
    
    start_time = time.time()
    total_rows = len(rows_to_process)

    for i in range(0, total_rows, batch_size):
        batch = rows_to_process[i:i + batch_size]
        print(f"   Processing {sheet_name}: {i} to {i + len(batch)}...")
        
        batch_tasks = []
        for idx, url in batch:
            task = asyncio.create_task(search_worker(browser_context, semaphore, idx, url, df, target_column))
            batch_tasks.append(task)
        
        await asyncio.gather(*batch_tasks)
        
        # Calculate Stats
        elapsed = time.time() - start_time
        processed_count = i + len(batch)
        rate = processed_count / elapsed if elapsed > 0 else 0
        remaining = total_rows - processed_count
        eta_seconds = remaining / rate if rate > 0 else 0
        
        print(f"   Stats: {rate:.2f} links/sec | ETA: {eta_seconds/60:.1f} min | Elapsed: {elapsed/60:.1f} min")

        # Save batch
        df.to_excel(output_file, index=False)
        print(f"   💾 Saved {output_filename}")

    print(f"✅ Sheet {sheet_name} Complete.")

async def main():
    input_file = current_dir / "live.xlsx"
    if not input_file.exists(): return
    
    # Get all sheet names
    xls = pd.ExcelFile(input_file, engine='openpyxl')
    sheet_names = xls.sheet_names
    
    print(f"found sheets: {sheet_names}")

    # Launch browser once
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        
        for sheet in sheet_names:
            # Skip Sheet1 if we already did it manually, OR verify if it's done.
            # I will check if output file exists.
            output_filename = f"live_processed_{sheet}.xlsx"
            if (current_dir / output_filename).exists():
                print(f"⚠️ Skipping {sheet} (Output file {output_filename} exists). Delete it to re-run.")
                continue
                
            await process_sheet(sheet, input_file, context)
            
            # Cool down between sheets
            await asyncio.sleep(5)

        await browser.close()

    print("\n✅ All Sheets Processed.")

if __name__ == "__main__":
    asyncio.run(main())

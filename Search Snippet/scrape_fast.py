import asyncio
import pandas as pd
import sys
import os
import re
import time
import random
from pathlib import Path
from ddgs import DDGS

# Add project root to path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir.parent))

def extract_linkedin_id(url):
    match = re.search(r'linkedin\.com/in/([^/?]+)', str(url))
    if match: return match.group(1)
    return str(url).split('/')[-1]

def sync_search(idx, url):
    """
    Synchronous search function to be run in threads.
    Includes retry logic and delays.
    """
    # Optimized delay for speed vs safety
    time.sleep(random.uniform(0.5, 1.5))
    
    slug = extract_linkedin_id(url)

    query1 = f'site:linkedin.com/in/{slug}'
    query2 = f'{slug} LinkedIn'
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with DDGS(timeout=30) as ddgs:
                # Attempt Primary Search
                try:
                    results = ddgs.text(query1, max_results=1)
                    if results:
                        res = results[0]
                        return {
                            'idx': idx,
                            'status': 'Primary Success',
                            'result': f"{res.get('title','')}\n{res.get('href','')}\n{res.get('body','')}"
                        }
                except:
                    pass # Silence intermediate primary failure
                
                # Attempt Fallback Search
                try:
                    results = ddgs.text(query2, max_results=1)
                    if results:
                        res = results[0]
                        return {
                            'idx': idx,
                            'status': 'Fallback Success',
                            'result': f"{res.get('title','')}\n{res.get('href','')}\n{res.get('body','')}"
                        }
                except:
                    pass # Silence intermediate fallback failure
                
                return {'idx': idx, 'status': 'No Results', 'result': "Error: No results found."}
                    
        except Exception as e:
            if attempt == max_retries - 1:
                return {'idx': idx, 'status': 'Failed', 'error': str(e)}
            time.sleep(5 * (attempt + 1))

    return {'idx': idx, 'status': 'Failed', 'error': 'Unknown failure'}

async def process_sheet(sheet_name, input_file, output_file):
    print(f"\n📂 Reading {input_file} (Sheet: {sheet_name})...")
    try:
        df = pd.read_excel(input_file, sheet_name=sheet_name, engine='openpyxl')
    except Exception:
        df = pd.read_excel(input_file, sheet_name=0, engine='openpyxl')

    target_column = 'Search Result Detail'
    if target_column not in df.columns:
        df[target_column] = None

    while True: # Outer loop to ensure all errors are rectified
        rows = []
        for idx, row in df.iterrows():
            url_col = 'LinkedIn URL' if 'LinkedIn URL' in df.columns else df.columns[0]
            url = row[url_col]
            if pd.isna(url) or str(url).strip() == "": continue
            
            val = row[target_column]
            if pd.isna(val) or "Error" in str(val):
                rows.append((idx, url))

        total = len(rows)
        if total == 0:
            print(f"   ✅ Sheet {sheet_name} is complete with no errors.")
            break

        print(f"🚀 Processing {total} profiles in {sheet_name}...")
        start_time = time.time()
        
        # Concurrency of 3 for optimized speed (Target: ~6-10 hours for 22k)
        chunk_size = 3
        
        for i in range(0, total, chunk_size):
            chunk = rows[i:i + chunk_size]
            loop = asyncio.get_running_loop()
            
            tasks = [loop.run_in_executor(None, sync_search, idx, url) for idx, url in chunk]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                # Update DataFrame
                df.at[res['idx'], target_column] = f"Error: {res['error']}" if res['status'] == 'Failed' else res['result']
            
            # Calculate stats
            processed = i + len(chunk)
            elapsed = time.time() - start_time
            rate = processed / elapsed if elapsed > 0 else 0
            remaining = total - processed
            eta_min = (remaining / rate) / 60 if rate > 0 else 0
            
            # Log the last result in the chunk as a sample
            last_res = results[-1]
            status_symbol = "✅" if "Success" in last_res['status'] else "❌"
            print(f"   [{sheet_name}] {processed}/{total} | {status_symbol} {last_res['status']:<15} | Rate: {rate:.2f} l/s | ETA: {eta_min:.1f}m")
            
            # Save every 5 entries (reduced from 30) to maximize persistence
            if processed % 5 == 0 or processed >= total:
                df.to_excel(output_file, index=False)
                
            # Minimal safety sleep
            await asyncio.sleep(random.uniform(0.3, 0.7))



        # After finishing the rows, check if there are still errors
        errors_remaining = df[df[target_column].str.contains("Error", na=True)].shape[0]
        if errors_remaining > 0:
            print(f"   🔄 {errors_remaining} errors remain. Retrying sheet...")
            await asyncio.sleep(10) # Cooldown before re-scanning sheet
        else:
            break


    elapsed = time.time() - start_time
    print(f"✅ Sheet {sheet_name} Complete. {total} processed in {elapsed:.2f}s")

async def finalize_logs(total_processed, total_success, total_errors, start_time):
    end_time = time.time()
    duration_hrs = (end_time - start_time) / 3600
    date_str = time.strftime("%Y-%m-%d")
    
    log_entry = f"""
## Session Log - {date_str} (Automated Completion)
- **Task:** Bulk Search Completion for 22k profiles.
- **Total Processed:** {total_processed}
- **Success Rate:** {total_success} successful, {total_errors} failed.
- **Duration:** {duration_hrs:.2f} hours.
- **Outcome:** All sheets (Jul 1 - Jul 7) processed and saved.
"""
    changelog_entry = f"## [{date_str}] Bulk Scraping Completion\n- Completed processing of all 7 sheets in Live.xlsx.\n- Finalized {total_processed} records with {total_success} successes.\n"

    try:
        with open(current_dir.parent / "LOG.md", "a", encoding="utf-8") as f:
            f.write(log_entry)
        
        # Prepend to CHANGELOG or append? Usually append for simple logs
        with open(current_dir.parent / "CHANGELOG.md", "a", encoding="utf-8") as f:
            f.write(changelog_entry)
            
        print("\n📝 LOG.md and CHANGELOG.md updated successfully.")
    except Exception as e:
        print(f"⚠️ Failed to update markdown files: {e}")

async def main():
    input_file = current_dir / "Live.xlsx"
    if not input_file.exists():
        print(f"❌ Input file {input_file} not found.")
        return
        
    xls = pd.ExcelFile(input_file, engine='openpyxl')
    sheet_names = xls.sheet_names
    print(f"Found sheets: {sheet_names}")

    overall_start = time.time()
    overall_processed = 0
    overall_success = 0
    overall_errors = 0

    for sheet in sheet_names:
        output_filename = f"live_processed_{sheet}.xlsx"
        output_file = current_dir / output_filename
        file_to_work_on = output_file if output_file.exists() else input_file
        
        await process_sheet(sheet, file_to_work_on, output_file)
        
        # Gather stats for logging
        final_df = pd.read_excel(output_file)
        target_col = 'Search Result Detail'
        overall_processed += len(final_df)
        overall_errors += final_df[target_col].str.contains("Error", na=True).sum()
        overall_success += (len(final_df) - final_df[target_col].str.contains("Error", na=True).sum())
        
        await asyncio.sleep(2)

    await finalize_logs(overall_processed, overall_success, overall_errors, overall_start)
    print("\n✅ All Sheets Processed and Logged.")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
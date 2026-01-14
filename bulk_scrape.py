#!/usr/bin/env python3
"""
Bulk LinkedIn Scraper from Excel

This script reads LinkedIn URLs from an Excel file, scrapes the profiles,
and saves the data back to the same file in new columns.

Usage:
    python bulk_scrape.py --input profiles.xlsx --workers 3 --headless
"""

import asyncio
import argparse
import pandas as pd
from pathlib import Path
from linkedin_scraper import BrowserManager, PersonScraper
from linkedin_scraper.core.exceptions import LinkedInScraperException

# Global lock for saving files to prevent write conflicts
save_lock = asyncio.Lock()

async def save_data(df, file_path):
    """Save DataFrame to Excel safely."""
    async with save_lock:
        print(f"Saving progress to {file_path}...")
        # Run synchronous pandas I/O in a separate thread to avoid blocking the event loop
        await asyncio.to_thread(df.to_excel, file_path, index=False)

async def scrape_worker(worker_id: int, queue: asyncio.Queue, browser: BrowserManager, df: pd.DataFrame, file_path: Path, url_column: str):
    """
    Worker task to process URLs from the queue.
    """
    print(f"Worker {worker_id} started.")
    
    while True:
        try:
            # Get a "unit of work" from the queue
            index, row = await queue.get()
        except asyncio.CancelledError:
            break
            
        url = row[url_column]
        print(f"[Worker {worker_id}] Processing row {index+1}: {url}")

        # Create a new isolated page for this task
        page = await browser.new_page()
        scraper = PersonScraper(page)

        try:
            person = await scraper.scrape(url)

            # Update DataFrame (Asyncio is single-threaded, so memory updates are atomic between awaits)
            df.at[index, 'Name'] = person.name
            # Person model doesn't have headline, removing it or keeping empty
            df.at[index, 'Headline'] = "" 
            df.at[index, 'Location'] = person.location
            df.at[index, 'About'] = person.about[:500] + "..." if person.about else ""

            # Use helper properties from Person model
            df.at[index, 'Job Title'] = person.job_title
            df.at[index, 'Company'] = person.company

            # Extract 'Founder Of' companies
            founder_companies = []
            if person.experiences:
                for exp in person.experiences:
                    if not exp.position_title or not exp.institution_name:
                        continue
                    
                    # Check if title indicates founder status
                    title_lower = exp.position_title.lower()
                    is_founder = "founder" in title_lower
                    
                    # Check if currently active (to_date is None, 'Present', or empty)
                    is_current = not exp.to_date or str(exp.to_date).lower() == "present"
                    
                    if is_founder and is_current:
                        founder_companies.append(exp.institution_name)
            
            df.at[index, 'Founder Of'] = ", ".join(founder_companies) if founder_companies else ""
            
            print(f"   [Worker {worker_id}] Scraped: {person.name}")

        except LinkedInScraperException as e:
            print(f"   [Worker {worker_id}] Failed to scrape {url}: {e}")
            df.at[index, 'Name'] = f"Error: {str(e)}"
        except Exception as e:
            print(f"   [Worker {worker_id}] Unexpected error on {url}: {e}")
            df.at[index, 'Name'] = f"Error: {str(e)}"
        finally:
            # Cleanup page
            await page.close()
            # Mark task as done
            queue.task_done()
            
            # Save periodically (e.g., every 5 items globally, but here we can just trigger a save)
            # To avoid saving too often, we could check queue size or just save. 
            # For simplicity in parallel, we'll save after every successful scrape but use the lock.
            # Ideally, we would batch this, but safety first.
            await save_data(df, file_path)

async def process_excel(input_path: str, url_column: str, headless: bool, num_workers: int):
    """
    Read Excel, scrape profiles in parallel, and update the file.
    """
    file_path = Path(input_path)
    if not file_path.exists():
        print(f"Error: File not found: {input_path}")
        return

    print(f"Reading {input_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    if url_column not in df.columns:
        print(f"Error: Column '{url_column}' not found in Excel file.")
        print(f"   Available columns: {', '.join(df.columns)}")
        return

    # Initialize new columns if they don't exist
    new_columns = ['Name', 'Headline', 'Location', 'About', 'Job Title', 'Company', 'Founder Of']
    for col in new_columns:
        if col not in df.columns:
            df[col] = None

    # Filter rows that need processing
    queue = asyncio.Queue()
    tasks_count = 0
    
    for index, row in df.iterrows():
        url = row[url_column]
        
        # Skip empty or already scraped rows
        if pd.isna(url) or (pd.notna(row['Name']) and str(row['Name']) != "" and not str(row['Name']).startswith("Error:")):
            continue
            
        queue.put_nowait((index, row))
        tasks_count += 1

    if tasks_count == 0:
        print("No new profiles to scrape.")
        return

    print(f"Starting bulk scrape for {tasks_count} profiles with {num_workers} workers (Headless: {headless})...")
    
    async with BrowserManager(headless=headless) as browser:
        # Load session
        try:
            await browser.load_session("linkedin_session.json")
            print("Session loaded")
        except Exception:
            print("Warning: No session file found. You may hit auth walls.")
        
        # Create workers
        workers = []
        for i in range(min(num_workers, tasks_count)):
            task = asyncio.create_task(scrape_worker(i+1, queue, browser, df, file_path, url_column))
            workers.append(task)
        
        # Wait for queue to be fully processed
        await queue.join()
        
        # Cancel workers
        for task in workers:
            task.cancel()
        
        # Wait for workers to finish cancelling
        await asyncio.gather(*workers, return_exceptions=True)

    print("\n" + "="*60)
    print(f"Bulk scraping complete. Data saved to {input_path}")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Bulk scrape LinkedIn profiles from Excel")
    parser.add_argument("--input", "-i", required=True, help="Path to input Excel file (.xlsx)")
    parser.add_argument("--column", "-c", default="LinkedIn URL", help="Column name containing LinkedIn URLs")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode (no browser window)")
    parser.add_argument("--workers", "-w", type=int, default=1, help="Number of concurrent workers (default: 1)")
    
    args = parser.parse_args()
    
    asyncio.run(process_excel(args.input, args.column, args.headless, args.workers))

if __name__ == "__main__":
    main()

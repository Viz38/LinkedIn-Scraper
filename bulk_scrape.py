#!/usr/bin/env python3
"""
Bulk LinkedIn Scraper from Excel

This script reads LinkedIn URLs from an Excel file, scrapes the profiles,
and saves the data back to the same file in new columns.

Usage:
    python samples/bulk_scrape.py --input profiles.xlsx --column "LinkedIn URL"
"""

import asyncio
import argparse
import pandas as pd
from pathlib import Path
from linkedin_scraper import BrowserManager, PersonScraper
from linkedin_scraper.core.exceptions import LinkedInScraperException

async def process_excel(input_path: str, url_column: str):
    """
    Read Excel, scrape profiles, and update the file.
    """
    file_path = Path(input_path)
    if not file_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return

    print(f"📂 Reading {input_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return

    if url_column not in df.columns:
        print(f"❌ Error: Column '{url_column}' not found in Excel file.")
        print(f"   Available columns: {', '.join(df.columns)}")
        return

    # Initialize new columns if they don't exist
    new_columns = ['Name', 'Headline', 'Location', 'About', 'Job Title', 'Company', 'Founder Of']
    for col in new_columns:
        if col not in df.columns:
            df[col] = None

    print(f"🚀 Starting bulk scrape for {len(df)} profiles...")
    
    async with BrowserManager(headless=False) as browser:
        # Load session
        try:
            await browser.load_session("linkedin_session.json")
            print("✓ Session loaded")
        except Exception:
            print("⚠️ Warning: No session file found. You may hit auth walls.")
        
        scraper = PersonScraper(browser.page)

        # Iterate through rows
        for index, row in df.iterrows():
            url = row[url_column]
            
            # Skip empty or already scraped rows (optional: remove 'pd.notna(row["Name"])' to force rescrape)
            if pd.isna(url) or (pd.notna(row['Name']) and row['Name'] != ""):
                print(f"⏭️ Skipping row {index+1}: {url} (Already scraped or empty)")
                continue

            print(f"🔍 [{index+1}/{len(df)}] Scraping: {url}")
            
            try:
                person = await scraper.scrape(url)
                
                # Update DataFrame
                df.at[index, 'Name'] = person.name
                # Person model doesn't have headline, removing it
                df.at[index, 'Headline'] = "" 
                df.at[index, 'Location'] = person.location
                df.at[index, 'About'] = person.about[:500] + "..." if person.about else ""
                
                # Use helper properties from Person model
                df.at[index, 'Job Title'] = person.job_title
                df.at[index, 'Company'] = person.company
                
                # Extract 'Founder Of' companies
                founder_companies = []
                for exp in person.experiences:
                    if not exp.position_title or not exp.institution_name:
                        continue
                        
                    # Check if title indicates founder status
                    title_lower = exp.position_title.lower()
                    is_founder = "founder" in title_lower
                    
                    # Check if currently active (to_date is None, 'Present', or empty)
                    is_current = not exp.to_date or exp.to_date.lower() == "present"
                    
                    if is_founder and is_current:
                        founder_companies.append(exp.institution_name)
                
                df.at[index, 'Founder Of'] = ", ".join(founder_companies) if founder_companies else ""
                
                # Save intermediate results (in case of crash)
                df.to_excel(file_path, index=False)
                print(f"   ✅ Saved: {person.name}")
                
                # Brief pause to be polite
                await asyncio.sleep(2)
                
            except LinkedInScraperException as e:
                print(f"   ❌ Failed to scrape: {e}")
                df.at[index, 'Name'] = f"Error: {str(e)}"
            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
                df.at[index, 'Name'] = f"Error: {str(e)}"

    print("\n" + "="*60)
    print(f"✅ Bulk scraping complete. Data saved to {input_path}")
    print("="*60)

def main():
    parser = argparse.ArgumentParser(description="Bulk scrape LinkedIn profiles from Excel")
    parser.add_argument("--input", "-i", required=True, help="Path to input Excel file (.xlsx)")
    parser.add_argument("--column", "-c", default="LinkedIn URL", help="Column name containing LinkedIn URLs")
    
    args = parser.parse_args()
    
    asyncio.run(process_excel(args.input, args.column))

if __name__ == "__main__":
    main()

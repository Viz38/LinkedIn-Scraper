# LinkedIn Scraper Toolkit

A complete toolkit for scraping LinkedIn profiles, companies, and finding founders data.

## 📦 Installation

1.  **Install Python:** Ensure you have Python 3.8+ installed.
2.  **Run Setup:** Double-click `install_dependencies.bat` (Windows) or run:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

## 🚀 Usage Guide

### 1. Authentication (Step 1 - Required)
Before scraping, you must log in and save your session.
1.  Run `python create_session.py`
2.  A browser will open. Log in to LinkedIn manually.
3.  Wait until your feed loads. The script will save `linkedin_session.json`.

### 2. Bulk Scraping (Profiles & Founders)
Scrape multiple profiles from an Excel file. This tool extracts:
- Basic Info (Name, Location, About)
- Current Job & Company
- **Founder Status:** Lists companies where the person is a Founder/Co-Founder.

**Steps:**
1.  Create an Excel file (e.g., `leads.xlsx`).
2.  Add a column named `LinkedIn URL` with the profile links.
3.  Run the script:
    ```bash
    python bulk_scrape.py --input leads.xlsx
    ```
4.  The script will add new columns (Name, Job Title, Founder Of, etc.) to the **same file**.

### 3. Individual Scraping
- **Profile:** Edit `scrape_single_profile.py` to change the URL, then run it:
  ```bash
  python scrape_single_profile.py
  ```
- **Company:** Edit `scrape_single_company.py` to change the URL, then run it:
  ```bash
  python scrape_single_company.py
  ```

## ⚠️ Important Notes
- **Safety:** Do not scrape too fast. The scripts have built-in delays, but aggressive scraping can get your account restricted.
- **Session:** If you get authentication errors, your session might have expired. Run `create_session.py` again.
- **Excel:** Close the Excel file before running the bulk scraper, or it will fail to save.

## 📁 File Structure
- `linkedin_scraper/` - Core library code.
- `bulk_scrape.py` - Main tool for bulk processing.
- `create_session.py` - Login tool.
- `requirements.txt` - Dependency list.

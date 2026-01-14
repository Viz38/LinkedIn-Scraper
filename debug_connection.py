import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            print("Navigating to DuckDuckGo...")
            await page.goto("https://duckduckgo.com/", timeout=30000)
            print(f"Title: {await page.title()}")
            
            # Try a search
            await page.fill('input[name="q"]', "LinkedIn")
            await page.press('input[name="q"]', "Enter")
            await page.wait_for_selector('article[data-testid="result"]', timeout=10000)
            print("Search results loaded successfully.")
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())

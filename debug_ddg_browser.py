import asyncio
from playwright.async_api import async_playwright
import urllib.parse

async def debug_single():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        url = "https://www.linkedin.com/in/maanasamahesh/"
        encoded = urllib.parse.quote(url)
        search_url = f"https://duckduckgo.com/?q={encoded}"
        
        print(f"Navigating to: {search_url}")
        try:
            await page.goto(search_url, timeout=60000)
            print("Waiting 10 seconds to see state...")
            await asyncio.sleep(10)
            
            # Check for results or blocking
            title = await page.title()
            print(f"Page Title: {title}")
            
            content = await page.content()
            if "Please prove you're a human" in content or "Robot Check" in content:
                print("🚨 BLOCKED: CAPTCHA/Robot check detected.")
            elif "No results found" in content:
                 print("⚠️ No results found on page.")
            else:
                 result_selector = "article[data-testid='result']"
                 count = await page.locator(result_selector).count()
                 print(f"Success! Found {count} results.")
                 
            await page.screenshot(path="ddg_debug.png")
            print("Screenshot saved to ddg_debug.png")

        except Exception as e:
            print(f"Error during goto: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_single())

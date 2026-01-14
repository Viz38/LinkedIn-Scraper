from ddgs import DDGS

def test_search():
    # Test with a known public profile (e.g., Satya Nadella) and one from the file
    queries = [
        "Sagar Jadhav LinkedIn"
    ]

    print("Testing DDGS...")
    try:
        with DDGS() as ddgs:
            for q in queries:
                print(f"\nQuery: {q}")
                results = ddgs.text(q, max_results=1)
                if results:
                    print(f"✅ Found: {results[0]['title']}")
                    print(f"   Link: {results[0]['href']}")
                else:
                    print("❌ No results found.")
    except Exception as e:
        print(f"🔥 Error: {e}")

if __name__ == "__main__":
    test_search()

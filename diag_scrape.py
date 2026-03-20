import requests
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
url = "https://www.moneycontrol.com/news/tags/tata-consultancy-services.html"

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        # Find all h2 tags
        h2s = soup.find_all("h2")
        print(f"Found {len(h2s)} h2 tags:")
        for h in h2s[:10]:
            print(f" - {h.get_text(strip=True)}")
        
        # Try finding <li> tags with class clearfix
        articles = soup.find_all("li", class_="clearfix")
        print(f"Found {len(articles)} clearfix articles")
except Exception as e:
    print(f"Error: {e}")

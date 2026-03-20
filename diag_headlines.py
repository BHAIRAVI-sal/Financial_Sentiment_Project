import requests
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
url = "https://www.moneycontrol.com/news/tags/tata-consultancy-services.html"

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")
        print("--- H2 Tags ---")
        for h in soup.find_all("h2"):
            print(f"- {h.get_text(strip=True)}")
        
        print("\n--- H3 Tags ---")
        for h in soup.find_all("h3"):
            print(f"- {h.get_text(strip=True)}")
            
        print("\n--- Links (A) with titles ---")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            if len(text) > 30 and ("TCS" in text or "Tata" in text):
                print(f"- {text}")
except Exception as e:
    print(f"Error: {e}")

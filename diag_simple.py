import requests

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
url = "https://www.moneycontrol.com/news/tags/tata-consultancy-services.html"

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("Body length:", len(response.text))
        print("Excerpt:")
        print(response.text[:2000])
except Exception as e:
    print(f"Error: {e}")

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from django.http import JsonResponse
from transformers import pipeline
import re
import random

# Load model once
finbert = pipeline("sentiment-analysis", model="ProsusAI/finbert")

def get_stock_data(stock):
    stock = stock.upper()
    registry = {
        "TCS": {"slugs": ["tata-consultancy-services", "tcs"], "keywords": ["tcs", "tata consultancy"], "yf_symbol": "TCS.NS", "sector": "IT Services"},
        "SBIN": {"slugs": ["state-bank-of-india", "sbin", "sbi"], "keywords": ["sbin", "state bank", "sbi "], "yf_symbol": "SBIN.NS", "sector": "Banking"},
        "INFY": {"slugs": ["infosys", "infy"], "keywords": ["infy", "infosys"], "yf_symbol": "INFY.NS", "sector": "IT Services"},
        "RELIANCE": {"slugs": ["reliance-industries", "reliance"], "keywords": ["reliance", "ril ", "ambani"], "yf_symbol": "RELIANCE.NS", "sector": "Energy/Conglomerate"},
        "HDFCBANK": {"slugs": ["hdfc-bank", "hdfc"], "keywords": ["hdfc bank", "hdfcbank"], "yf_symbol": "HDFCBANK.NS", "sector": "Banking"},
        "ICICIBANK": {"slugs": ["icici-bank", "icici"], "keywords": ["icici bank", "icicibank"], "yf_symbol": "ICICIBANK.NS", "sector": "Banking"},
        "WIPRO": {"slugs": ["wipro"], "keywords": ["wipro"], "yf_symbol": "WIPRO.NS", "sector": "IT Services"},
        "BHARTIARTL": {"slugs": ["bharti-airtel", "airtel"], "keywords": ["airtel", "bharti"], "yf_symbol": "BHARTIARTL.NS", "sector": "Telecom"},
    }
    # Fallback
    return registry.get(stock, {"slugs": [stock.lower()], "keywords": [stock.lower()], "yf_symbol": f"{stock}.NS", "sector": "General Market"})

def generate_prediction(stock_symbol, current_sentiment):
    try:
        ticker = yf.Ticker(stock_symbol)
        # Fetch 30 days of data
        hist = ticker.history(period="1mo")
        if hist.empty:
            raise ValueError("No data found")
        
        # Scale prices to -1 to 1 range for the terminal chart (normalization)
        prices = hist['Close'].tolist()
        min_p, max_p = min(prices), max(prices)
        range_p = max_p - min_p if max_p != min_p else 1
        normalized_past = [round(((p - min_p) / range_p * 2) - 1, 2) for p in prices]
        
        # Simple forecast based on sentiment + trend (10 days)
        last_price = normalized_past[-1]
        trend = (normalized_past[-1] - normalized_past[-5]) / 5 if len(normalized_past) >= 5 else 0
        
        future = []
        curr = last_price
        for i in range(1, 11):
            # Combine trend with sentiment (0.3 weightage)
            noise = random.uniform(-0.05, 0.05)
            curr = round(curr + (trend * 0.7) + (current_sentiment * 0.3) + noise, 2)
            curr = max(-1.0, min(1.0, curr))
            future.append(curr)
            
        upper = [round(v + (0.05 + 0.02 * i), 2) for i, v in enumerate(future)]
        lower = [round(v - (0.05 + 0.02 * i), 2) for i, v in enumerate(future)]
        
        return {
            "past": normalized_past,
            "future": future,
            "upper_bound": upper,
            "lower_bound": lower,
            "real_price": round(prices[-1], 2),
            "change": round(prices[-1] - prices[-2], 2) if len(prices) > 1 else 0
        }
    except Exception as e:
        print(f"Prediction Error: {e}")
        # Fallback to simulated if yf fails
        past = [round(current_sentiment + random.uniform(-0.2, 0.2), 2) for _ in range(20)]
        future = [round(past[-1] + (i * 0.02) + random.uniform(-0.1, 0.1), 2) for i in range(1, 11)]
        return {"past": past, "future": future, "upper_bound": [v+0.1 for v in future], "lower_bound": [v-0.1 for v in future], "real_price": 0, "change": 0}

def is_generic_noise(headline):
    h_lower = headline.lower()
    # Only block extremely generic noise if it doesn't contain a hint of the stock
    noise = [r"global cues", r"opening bell", r"stock market live", r"track live"]
    for p in noise:
        if re.search(p, h_lower):
            return True
    return False

def fetch_moneycontrol(stock_info, headlines_set, headers):
    results = []
    keywords = stock_info["keywords"]
    for slug in stock_info["slugs"]:
        urls = [
            f"https://www.moneycontrol.com/news/tags/{slug}.html",
            f"https://www.moneycontrol.com/news/tags/{slug.upper()}.html",
            f"https://www.moneycontrol.com/news/tags/{slug.lower()}.html"
        ]
        for url in urls:
            try:
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    # Scrape everything that looks like a title
                    for tag in soup.find_all(["h2", "h3", "a"]):
                        text = tag.get_text(strip=True)
                        if len(text) < 15 or len(text) > 250: continue
                        
                        t_lower = text.lower()
                        if t_lower not in headlines_set:
                            if any(kw in t_lower for kw in keywords):
                                # Logic: Minimal noise filtering to ensure data flow
                                headlines_set.add(t_lower)
                                results.append({"headline": text, "source": "Moneycontrol"})
            except Exception: continue
    return results

def fetch_et(stock_info, headlines_set, headers):
    results = []
    keywords = stock_info["keywords"]
    stock_term = stock_info["slugs"][0].replace("-", " ")
    url = f"https://economictimes.indiatimes.com/topic/{stock_term}/news"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup.find_all(["h2", "h3", "b", "a"]):
                text = tag.get_text(strip=True)
                if len(text) < 20: continue
                t_lower = text.lower()
                if t_lower not in headlines_set:
                    if any(kw in t_lower for kw in keywords):
                        headlines_set.add(t_lower)
                        results.append({"headline": text, "source": "Economic Times"})
    except Exception: pass
    return results

def fetch_livemint(stock_info, headlines_set, headers):
    results = []
    keywords = stock_info["keywords"]
    slug = stock_info["slugs"][0].replace("-", "+")
    url = f"https://www.livemint.com/search?q={slug}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            for tag in soup.find_all(["h2", "h3", "a"]):
                text = tag.get_text(strip=True)
                if len(text) < 20: continue
                t_lower = text.lower()
                if t_lower not in headlines_set:
                    if any(kw in t_lower for kw in keywords):
                        headlines_set.add(t_lower)
                        results.append({"headline": text, "source": "Livemint"})
    except Exception: pass
    return results

def analyze(request, stock):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    stock_info = get_stock_data(stock)
    unique_headlines = set()
    
    # 🔹 Data Pipeline
    mc = fetch_moneycontrol(stock_info, unique_headlines, headers)
    et = fetch_et(stock_info, unique_headlines, headers)
    lm = fetch_livemint(stock_info, unique_headlines, headers)

    all_news = mc + et + lm
    
    if len(all_news) < 1:
        return JsonResponse({"status": "error", "message": f"No recent headlines found for {stock.upper()}. Try again later."}, status=200)

    # 🔹 Source Distribution (60% Moneycontrol Priority)
    final_pool = mc[:30] + (et + lm)[:20]

    # 🔹 AI Sentiment core
    texts = [n["headline"] for n in final_pool]
    sentiments = finbert(texts)

    detailed = []
    scores = []
    for i, res in enumerate(sentiments):
        label, score = res["label"], res["score"]
        source = final_pool[i]["source"]
        
        # Source Weighting logic
        weight = 1.2 if source == "Moneycontrol" else (1.1 if source == "Economic Times" else 1.0)
        val = score if label == "positive" else (-score if label == "negative" else 0.0)
        weighted_val = round(val * weight, 2)
        
        detailed.append({
            "headline": final_pool[i]["headline"],
            "source": source,
            "score": weighted_val,
            "label": label,
            "emoji": "😊" if label == "positive" else ("😟" if label == "negative" else "😐")
        })
        scores.append(weighted_val)

    final_score = sum(scores) / len(scores) if scores else 0
    total = len(scores)
    pos = sum(1 for s in scores if s > 0.1)
    neg = sum(1 for s in scores if s < -0.1)
    neu = total - pos - neg

    confidence = round(abs(final_score) * 100, 1)
    
    if final_score > 0.05: verdict, risk = "Bullish 📈", ("Low Risk 🟢" if confidence > 30 else "Medium Risk 🟡")
    elif final_score < -0.05: verdict, risk = "Bearish 📉", ("High Risk 🔴" if confidence > 30 else "Medium Risk 🟡")
    else: verdict, risk = "Neutral 😐", "Medium Risk 🟡"

    # Fetch Real Price Prediction
    prediction_data = generate_prediction(stock_info["yf_symbol"], final_score)
    sector = stock_info["sector"]

    return JsonResponse({
        "stock": stock.upper(),
        "sector": sector,
        "yf_symbol": stock_info["yf_symbol"],
        "sentiment_score": round(final_score, 2),
        "positive_news": pos, "negative_news": neg, "neutral_news": neu,
        "confidence": confidence, "risk": risk, "verdict": verdict,
        "report": f"Intelligence report for {stock.upper()} ({sector}): Overall sentiment is {verdict.split()[0]} based on {total} unique sources. AI analysis of {sector} trends suggests {verdict.lower()} momentum.",
        "detailed_news": detailed,
        "top_headlines": [n["headline"] for n in detailed[:5]],
        "prediction": prediction_data,
        "real_price": prediction_data["real_price"],
        "price_change": prediction_data["change"],
        "metadata": {"total_found": len(all_news), "source_split": {"MC": len(mc), "ET": len(et), "LM": len(lm)}}
    })
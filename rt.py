#!pip install requests beautifulsoup4 pandas tqdm telethon newspaper3k lxml

import requests
import random
import pandas as pd
from time import sleep
from datetime import datetime
from math import ceil
from typing import Optional
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor


QUERIES = [
    "курс рубля",
    "usd/rub",
    "usdrub",
    "доллар/рубль",
    "евро/рубль",
    "eur/rub",
    "eurrub"
]

BASE_URL = 'https://russian.rt.com'

DATE_FROM = "2012-01-01"
DATE_TO = "2025-12-31"

MAX_PAGES = 100
MIN_TEXT_LEN = 10


with open("user-agents.txt", "w") as f:
    f.write("""Mozilla/5.0 (Windows NT 10.0; Win64; x64)
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
Mozilla/5.0 (X11; Linux x86_64)
""")

with open('user-agents.txt') as file:
    USER_AGENTS = file.read().splitlines()

def random_headers():
    return {'User-Agent': random.choice(USER_AGENTS)}

def generate_date_ranges(start, end):
    dates = pd.date_range(start=start, end=end, freq='M')
    ranges = []

    prev = start
    for d in dates:
        ranges.append((prev, d.strftime("%Y-%m-%d")))
        prev = d.strftime("%Y-%m-%d")

    return ranges

def is_relevant(text):
    if not text:
        return False

    text = text.lower()

    keywords = QUERIES

    return any(k in text for k in keywords)

class RussiaTodayParser:
    def __init__(self, query, date_from, date_to):
        self.api = f'{BASE_URL}/search'
        self.headers = random_headers()

        self.params = {
            'q': query,
            'df': date_from,
            'dt': date_to,
            'pageSize': 100,
            'format': 'json'
        }

        self.articles_data = []

    def get_response(self, page: int) -> Optional[dict]:
        payload = {**self.params, 'page': page}

        for _ in range(3):
            try:
                return requests.get(
                    self.api,
                    headers=self.headers,
                    params=payload,
                    timeout=10
                ).json()
            except Exception as e:
                print(f'Error: {e}')
                sleep(1)

        return None

    def get_article_text(self, link: str) -> Optional[str]:
        try:
            html = requests.get(link, headers=random_headers(), timeout=10).text
            soup = BeautifulSoup(html, 'html.parser')

            content = soup.find('div', class_='article__text')

            if not content:
                return None

            return content.text.strip()

        except:
            return None

    def get_metadata(self, article: dict) -> Optional[dict]:
        link = f"{BASE_URL}{article['href']}"
        text = self.get_article_text(link)

        if not text or len(text) < MIN_TEXT_LEN:
            return None

        if not is_relevant(text):
            return None

        try:
            date = str(datetime.fromtimestamp(int(article['date'])).date())
        except:
            date = None

        return {
            'id': article.get('id'),
            'link': link,
            'date': date,
            'source': 'rt',
            'title': article.get('title'),
            'summary': article.get('summary'),
            'text': text,
            'type': article.get('type')
        }

    def iterate_pages(self) -> pd.DataFrame:
        self.articles_data = []
    
        first_page = self.get_response(1)
        if not first_page:
            return pd.DataFrame()
    
        articles_num = first_page.get('totalCount', 0)
        print(f'Found: {articles_num}')
    
        total_pages = min(ceil(articles_num / 100), MAX_PAGES)
    
        for page in range(1, total_pages + 1):
    
            response = self.get_response(page)
            if not response:
                continue
    
            articles = response.get('docs', [])
    
            links = [f"{BASE_URL}{a['href']}" for a in articles]
    
            with ThreadPoolExecutor(max_workers=5) as executor:
                texts = list(executor.map(self.get_article_text, links))
    
            for article, text in zip(articles, texts):
    
                if not text or len(text) < MIN_TEXT_LEN:
                    continue
        
                try:
                    date = str(datetime.fromtimestamp(int(article['date'])).date())
                except:
                    date = None
    
                self.articles_data.append({
                    'id': article.get('id'),
                    'link': f"{BASE_URL}{article['href']}",
                    'date': date,
                    'source': 'rt',
                    'title': article.get('title'),
                    'summary': article.get('summary'),
                    'text': text,
                    'type': article.get('type')
                })
    
            sleep(random.uniform(0.2, 0.5))
    
        print(f"Saved: {len(self.articles_data)}")
    
        return pd.DataFrame(self.articles_data)


date_ranges = generate_date_ranges(DATE_FROM, DATE_TO)

all_data = []

for query in QUERIES:
    for date_from, date_to in date_ranges:
        print(f"{date_from} → {date_to}")

        parser = RussiaTodayParser(query, date_from, date_to)
        df = parser.iterate_pages()

        if not df.empty:
            all_data.append(df)

        sleep(random.uniform(1, 3))


final_df = pd.concat(all_data, ignore_index=True)
final_df = final_df.dropna()
final_df = final_df.drop_duplicates(subset=["text"])
final_df.to_csv("rt_dataset.csv", index=False)
#!pip install requests beautifulsoup4 pandas tqdm
#!pip install selenium pandas webdriver-manager

import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import logging
from tqdm import tqdm

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import random

options = Options()
options.add_argument("--headless")  # убери если хочешь видеть браузер
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUERIES = [
    "курс рубля",
    "usd/rub",
    "usdrub",
    "доллар/рубль",
    "евро/рубль",
    "eur/rub",
    "eurrub"
]

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "ru-RU,ru;q=0.9"
}

MAX_PAGES = 300
SLEEP = 0.5


def get_page(query, page):
    url = "https://www.gazeta.ru/search.shtml"
    params = {"p": "main", "page": page, "text": query}

    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning(f"Ошибка загрузки страницы {page}: {e}")
        return None

def parse_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.select(".b_ear-title a"):
        href = a.get("href")
        if href:
            links.append("https://www.gazeta.ru" + href)

    return links


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")

    selectors = [
        ".b_article-text",
        ".article_text",
        ".js-article__text",
        ".b-topic__content"
    ]

    for sel in selectors:
        block = soup.select_one(sel)
        if block:
            paragraphs = block.find_all("p")
            text = " ".join(p.get_text(strip=True) for p in paragraphs)
            if len(text) > 200:
                return text

    paragraphs = soup.find_all("p")
    text = " ".join(p.get_text(strip=True) for p in paragraphs)

    if len(text) > 200:
        return text

    og = soup.select_one('meta[property="og:description"]')
    if og:
        return og.get("content", "")

    return ""

def parse_article(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        html = r.text

        soup = BeautifulSoup(html, "html.parser")

        title = soup.find("h1")
        title = title.get_text(strip=True) if title else ""

        date_tag = soup.find("time")
        date = date_tag.get("datetime")[:10] if date_tag else None

        text = extract_text(html)

        return {
            "link": url,
            "title": title,
            "date": date,
            "text": text
        }

    except Exception as e:
        logger.warning(f"Ошибка статьи: {url} | {e}")
        return None


def run(queries):
    all_links = []

    for q in queries:
        logger.info(f"query: {q}")

        for page in range(1, MAX_PAGES + 1):
            html = get_page(q, page)

            if not html:
                break

            links = parse_links(html)

            if not links:
                break

            all_links.extend(links)

            logger.info(f"page {page}: +{len(links)}")

            time.sleep(1)

    all_links = list(set(all_links))
    logger.info(f"Всего ссылок: {len(all_links)}")

    data = []

    for i, link in enumerate(tqdm(all_links)):
        article = parse_article(link)

        if article:
            data.append(article)

        if i % 50 == 0:
            logger.info(f"processed {i}, collected {len(data)}")

        time.sleep(SLEEP)

    df = pd.DataFrame(data)
    df.to_csv("gazeta_final.csv", index=False)

    return df

def article(url):
    try:
        driver.get(url)
        time.sleep(3 + random.random()*3)  

        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
        except:
            title = None

        try:
            date = driver.find_element(By.TAG_NAME, "time").text
        except:
            date = None

        paragraphs = driver.find_elements(By.TAG_NAME, "p")
        text = " ".join([p.text for p in paragraphs if p.text.strip() != ""])

        return title, date, text

    except Exception as e:
        print("Ошибка:", url)
        return None, None, None

df = run(QUERIES)

for i, row in df.iterrows():
    if pd.isna(row.get("text")):
        print(f"Обрабатываю {i+1}/{len(df)}")
        title, date, text = article(row["link"])
        df.at[i, "title"] = title
        df.at[i, "date"] = date
        df.at[i, "text"] = text
        time.sleep(2 + random.random()*3) 

df.to_csv("gazeta_completed.csv", index=False)
driver.quit()
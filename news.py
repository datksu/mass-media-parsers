import pandas as pd
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

options = Options()

# ВАЖНО: для news.ru лучше НЕ headless
# options.add_argument("--headless")
options.add_argument("--disable-blink-features=AutomationControlled")
options.add_argument("--start-maximized")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()),
    options=options
)


def parse_article(url):
    try:
        driver.get(url)
        time.sleep(4 + random.random()*2)

        try:
            title = driver.find_element(By.TAG_NAME, "h1").text
        except:
            title = None
        try:
            date = driver.find_element(By.TAG_NAME, "time").text
        except:
            date = None

        try:
            article = driver.find_element(By.CSS_SELECTOR, "div[data-qa='article-body']")
            paragraphs = article.find_elements(By.TAG_NAME, "p")
        except:
            # fallback — если структура изменилась
            paragraphs = driver.find_elements(By.TAG_NAME, "p")

        text = " ".join([p.text for p in paragraphs if p.text.strip() != ""])

        if len(text) < 200:
            text = None
        return title, date, text

    except Exception as e:
        print("Ошибка:", url, e)
        return None, None, None

for i, row in df.iterrows():
    if pd.isna(row.get("text")):
        print(f"Обрабатываю {i+1}/{len(df)}")

        title, date, text = parse_article(row["URL статьи"])

        df.at[i, "title"] = title
        df.at[i, "date"] = date
        df.at[i, "text"] = text

        time.sleep(2 + random.random()*3)


df.to_csv("news_ru_completed.csv", index=False)
driver.quit()
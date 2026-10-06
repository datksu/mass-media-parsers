import requests as rq
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup as bs
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from IPython import display


QUERIES = [
    "курс рубля",
    "usd/rub",
    "usdrub",
    "доллар/рубль",
    "евро/рубль",
    "eur/rub",
    "eurrub"
]

class rbc_parser:
    def __init__(self, max_workers: int = 10):
        self.session = rq.Session()
        self.max_workers = max_workers

    def _get_url(self, param_dict: dict) -> str:
        return (
            'https://www.rbc.ru/search/ajax/?'
            f"project={param_dict['project']}&"
            f"category={param_dict['category']}&"
            f"dateFrom={param_dict['dateFrom']}&"
            f"dateTo={param_dict['dateTo']}&"
            f"page={param_dict['page']}&"
            f"query={param_dict['query']}&"
            f"material={param_dict['material']}"
        )

    def _get_article_data(self, url: str):
        try:
            r = self.session.get(url, timeout=10)
            soup = bs(r.text, "lxml")

            div_overview = soup.find('div', class_='article__text__overview')
            overview = div_overview.get_text(strip=True) if div_overview else None

            article = soup.find('div', class_='article__text')
            if article:
                paragraphs = article.find_all('p')
                text = ' '.join([p.get_text(strip=True) for p in paragraphs])
            else:
                text = None

            return overview, text

        except Exception:
            return None, None

    def _get_search_table(self, param_dict: dict, include_text: bool = True) -> pd.DataFrame:
        url = self._get_url(param_dict)

        try:
            r = self.session.get(url, timeout=10)
            items = r.json().get('items', [])
        except Exception:
            items = []

        search_table = pd.DataFrame(items)

        if include_text and not search_table.empty:
            urls = search_table['fronturl'].tolist()

            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                results = list(executor.map(self._get_article_data, urls))

            search_table[['overview', 'text']] = results

        if 'publish_date_t' in search_table.columns:
            search_table = search_table.sort_values('publish_date_t', ignore_index=True)

        return search_table

    def _iterable_load_by_page(self, param_dict):
        param_copy = param_dict.copy()
        results = []

        result = self._get_search_table(param_copy)

        while not result.empty:
            results.append(result)
            param_copy['page'] = str(int(param_copy['page']) + 1)
            result = self._get_search_table(param_copy)

        if results:
            return pd.concat(results, ignore_index=True)
        else:
            return pd.DataFrame()

    def get_articles(
        self,
        param_dict,
        time_step=1,
        save_every=5,
        save_excel=True
    ) -> pd.DataFrame:

        param_copy = param_dict.copy()

        time_step = timedelta(days=time_step)
        dateFrom = datetime.strptime(param_copy['dateFrom'], '%d.%m.%Y')
        dateTo = datetime.strptime(param_copy['dateTo'], '%d.%m.%Y')

        if dateFrom > dateTo:
            raise ValueError('dateFrom should be less than dateTo')

        results = []
        save_counter = 0

        while dateFrom <= dateTo:
            current_to = min(dateFrom + time_step, dateTo)

            param_copy['dateFrom'] = dateFrom.strftime("%d.%m.%Y")
            param_copy['dateTo'] = current_to.strftime("%d.%m.%Y")

            print(f"Parsing {param_copy['dateFrom']} → {param_copy['dateTo']}")

            df = self._iterable_load_by_page(param_copy)
            if not df.empty:
                results.append(df)

            dateFrom = current_to + timedelta(days=1)
            save_counter += 1

            if save_counter == save_every:
                display.clear_output(wait=True)
                temp = pd.concat(results, ignore_index=True)
                temp.to_excel("checkpoint.xlsx", index=False)
                print("Checkpoint saved")
                save_counter = 0

        if results:
            out = pd.concat(results, ignore_index=True)
        else:
            out = pd.DataFrame()

        if save_excel and not out.empty:
            out.to_excel(
                f"rbc_{param_dict['dateFrom']}_{param_dict['dateTo']}.xlsx",
                index=False
            )

        print("Finish")
        return out

use_parser = "РБК"

query = 'курс рубля'
project = ""
category = ""
material = ""
dateFrom = '2014-01-30'
dateTo = "2025-12-31"
page = 0

if use_parser == "РБК":
    param_dict = {'query'   : query, 
                  'project' : project,
                  'category': category,
                  'dateFrom': datetime.
                  strptime(dateFrom, '%Y-%m-%d').
                  strftime('%d.%m.%Y'),
                  'dateTo'  : datetime.
                  strptime(dateTo, '%Y-%m-%d').
                  strftime('%d.%m.%Y'),
                  'page'   : str(page),
                  'material': material}

print(use_parser, "- param_dict:", param_dict)

parser = rbc_parser(max_workers=12)
table = parser.get_articles(param_dict=param_dict,
                             time_step = 37, # Шаг - 7 дней, можно больше,
                                            # но есть риск отсечения статей в неделях, гдестатей больше 100
                             save_every = 5, # Сохранять чекпойнт каждые 5 шагов
                             save_excel = True) 
print(len(table))
table.head()
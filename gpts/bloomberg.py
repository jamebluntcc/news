"""
get bloomberg'news 
"""

import time
import loguru
import requests
import argparse
from typing import List
from datetime import datetime
from pydantic import BaseModel
from bs4 import BeautifulSoup


OK, ERR = 1, 0

logger = loguru.logger
parser = argparse.ArgumentParser(
                    prog='get latest news',
                    description=f'get latest news from bloomberg.')
parser.add_argument('-t', '--topic', help="your interest topic", default="")
parser.add_argument('-l', "--url", help="article url, to get whole content", default="")

class NewsSource(BaseModel):
    id: str
    name: str


class NewsArticle(BaseModel):
    source: NewsSource
    title: str
    description: str
    publishedAt: datetime
    symbols: List[str]
    url: str
    id: str

    @classmethod
    def serialize(cls, **kwargs):
        _source = kwargs.pop("source")
        new_source = NewsSource(id=_source["id"], name=_source["name"])
        return cls(source=new_source, **kwargs)


def retry_on_error(retry_times=3):
    """
    被装饰的函数必须同时返回结果、和状态码
    状态码 OK, ERR = 1, 0
    """
    def wrapper(func):
        def inner(self, *args, **kwargs):
            for n in range(retry_times):
                result, status = func(self, *args, **kwargs)
                if status == OK:
                    return result
                else:
                    logger.warning(f"retry {1+n} times")
                    time.sleep(1+n)
            return result
        return inner
    return wrapper


class News:

    source = ""
    __url = "https://static.newsfilter.io/landing-page/articles-{source}.json"

    @retry_on_error()
    def get_articles(self, topic: str = "") -> (List[NewsArticle], int):
        try:
            response = requests.get(self.__url.format(source=self.source))
        except requests.exceptions.RequestException as e:
            logger.error("Error: Unable to connect to NewsFilter API, detail: {}".format(e))
            return [], ERR
        else:
            if response.status_code == 200:
                if topic:
                    return [NewsArticle.serialize(**article) for article in response.json() if topic in article["description"]], OK
                return [NewsArticle.serialize(**article) for article in response.json()], OK
            else:
                logger.warning("Error: Unable to fetch news from {}, detail: {}".format(self.source, response.text))
                return [], ERR


class Bloomberg(News):

    source = "bloomberg"

    @retry_on_error()
    def get_article_content(self, article_url: str) -> (str, int):
        try:
            response = requests.get(article_url)
        except requests.exceptions.RequestException as e:
            logger.error("Error: Unable to connect to Bloomberg API, detail: {}".format(e))
            return "", ERR
        else:
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                article_class = soup.find_all(class_="article-text")
                if article_class:
                    # 一般只有一篇文章
                    element = article_class[0].get_text()
                    return element, OK
                return "", OK
            else:
                logger.warning("Error: Unable to fetch news from {}, detail: {}".format(self.source, response.text))
                return "", ERR

    def get_articles(self, topic: str):
        return super().get_articles(topic)
    
    def get_brief(self, topic: str):
        articles = self.get_articles(topic)
        for article in articles:
            print("-"*30)
            print(f"title: {article.title}")
            print(f"url: {article.url}")
            print(f"brief: ")
            brief = article.description
            print(brief)


if __name__ == "__main__":
    args = parser.parse_args()
    client = Bloomberg()
    if args.url:
        article_content = client.get_article_content(args.url)
        print(article_content)
    else:
        client.get_brief(args.topic)
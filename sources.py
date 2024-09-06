import re
import requests
from typing import List, Tuple
from datetime import datetime
from pydantic import BaseModel
from common import OK, ERR
from bs4 import BeautifulSoup
from models import llm
from tools import retry_on_error, logger, text_output

sources = []


def register_sources(cls):
    if cls.source not in sources:
        sources.append(cls.source)
    return cls



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
    

class News:

    source = ""
    __url = "https://static.newsfilter.io/landing-page/articles-{source}.json"

    @retry_on_error()
    def get_articles(self, topic: str = "") -> Tuple[List[NewsArticle], int]:
        try:
            response = requests.get(self.__url.format(source=self.source))
        except requests.exceptions.RequestException as e:
            logger.error("Error: Unable to connect to NewsFilter API, detail: {}".format(e))
            return [], ERR
        else:
            if response.status_code == 200:
                if topic:
                    _topic = topic.lower()
                    pattern = re.compile(f"\\b{_topic}\\b", re.IGNORECASE)
                    return [NewsArticle.serialize(**article) for article in response.json() if re.search(pattern, article["description"])], OK
                return [NewsArticle.serialize(**article) for article in response.json()], OK
            else:
                logger.warning("Error: Unable to fetch news from {}, detail: {}".format(self.source, response.text))
                return [], ERR

    def get_summary(self, topic: str, top_k: int):
        pass


@register_sources
class Bloomberg(News):

    source = "bloomberg"

    @retry_on_error()
    def get_article_content(self, article_url: str) -> Tuple[str, int]:
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
    
    def get_summary(self, topic: str, top_k: int = 3):
        _summary = []
        articles = self.get_articles(topic)
        if articles:
            if top_k >= len(articles):
                top_k_articles = articles
            else:
                top_k_articles = articles[:top_k]
            for article in top_k_articles:
                logger.info(f"Generating summary for {article.title}...")
                text_output(llm.generate_summary(self.get_article_content(article.url)))
        return _summary
    
    def get_brief(self, topic: str):
        articles = self.get_articles(topic)
        for article in articles:
            print(f"title: {article.title}")
            print(f"url: {article.url}")
            print(f"brief: ")
            brief = article.description
            text_output(brief)
            print("-"*30)


@register_sources
class Reuters(News):

    source = "reuters"

    @retry_on_error()
    def get_article_content(self, article_url: str) -> Tuple[str, int]:
        try:
            article_url = article_url.replace("www.reuters.com", "neuters.de")
            response = requests.get(article_url)
        except requests.exceptions.RequestException as e:
            logger.error("Error: Unable to connect to Reuters API, detail: {}".format(e))
            return "", ERR
        else:
            if response.status_code == 200:
                article_content = []
                soup = BeautifulSoup(response.text, 'html.parser')
                p_elements = soup.find_all('p')
                if p_elements:
                    for element in p_elements:
                        article_content.append(element.text)
                return "\n".join(article_content), OK
            else:
                logger.warning("Error: Unable to fetch news from {}, detail: {}".format(self.source, response.text))
                return "", ERR

    def get_brief(self, topic: str):
        articles = self.get_articles(topic)
        for article in articles:
            print(f"title: {article.title}")
            print(f"url: {article.url}")
            print(f"brief: ")
            brief = article.description
            text_output(brief)
            print("-"*30)



if __name__ == "__main__":
    news = Reuters()
    articles = news.get_articles()
    print(news.get_article_content(articles[0].url))



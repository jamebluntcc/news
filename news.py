"""
news api for newsfilter
https://newsfilter.io/
"""
import time
import requests
import loguru
import argparse
from typing import List
from datetime import datetime
from pydantic import BaseModel
from bs4 import BeautifulSoup
from langchain_community.llms import Ollama
from langchain_openai import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

new_sources = ["bloomberg", "reuters"]
OK, ERR = 1, 0


logger = loguru.logger
parser = argparse.ArgumentParser(
                    prog='get latest news.',
                    description=f'get latest news from {", ".join(new_sources)}')
parser.add_argument('-t', '--topic', help="your interest topic", default="")
parser.add_argument('-s', '--source', help="news's source", default="bloomberg")
parser.add_argument('-l', "--url", help="article url, to get whole content", default="")
parser.add_argument('--summary', help="summary article by llm", default=False, action="store_true")
parser.add_argument('--translate', help=" translate the title and brief", default=False, action="store_true")

def text_output(text: str, max_line_num=100):
    start = 0
    total_len = len(text)
    while total_len > max_line_num:
        print(text[start:start+max_line_num])
        start += max_line_num
        total_len -= max_line_num

def translate_text(text):
    data = [text, "en", "zh"]
    url = "https://hf.space/embed/mikeee/gradio-deepl/+/api/predict"
    resp = requests.post(url,json={"data": data})
    if resp.status_code == 200:
        print(resp.json())
        return resp.json()["data"][0]
    return text


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


class LLM:

    summary_prompt_template = PromptTemplate(template=
    """
    I want you to act as a News Article summarizer. 
    I will provide you with a article on a specific topic: 
    {article}
    and you will create a summary of the main points and findings of the article. 
    Your summary should be concise and should accurately and objectively communicate the key points of the paper. 
    You should not include any personal opinions or interpretations in your summary but rather focus on objectively presenting the information from the paper. 
    Your summary should be written in your own words and should not include any direct quotes from the paper. Please ensure that your summary is clear, concise,
      and accurately reflects the content of the original paper.
      finally, I need u translating it to chinese.
    """, input_variables=["article"])
    translate_prompt_template = PromptTemplate(template=
        """
        You are an expert in Chinese-English translation and you need to translate the English content:
        {content}
        I give you into meaningful Chinese. 
        """, input_variables=["content"]
    )

    def __init__(self, model_type: str, model_id: str) -> None:
        if model_type == "Ollama":
            llm = Ollama(model=model_id)
        elif model_type == "OpenAI":
            llm = OpenAI(model_name=model_id)
        else:
            raise ValueError("Unsupported model type")
        self.summary_chain = LLMChain(prompt=self.summary_prompt_template, llm=llm)
        self.translate_chain = LLMChain(prompt=self.translate_prompt_template, llm=llm)

    def generate_summary(self, content: str) -> str:
        logger.info("Generating summary...")
        summary_content = self.summary_chain.run(content)
        logger.info("Summary generated. and translate...")
        return self.translate(summary_content)
    
    def translate(self, content: str) -> str:
        return self.translate_chain.run(content)

# openai
# llm = LLM(model_type="OpenAI", model_id="gpt-3.5-turbo-instruct")
# ollama
llm = LLM(model_type="Ollama", model_id="mistral-7B-Instruct-v0.2:latest")


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
    def get_articles(self, topic: str = "") -> (List[NewsArticle], int): # type: ignore
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

    def get_summary(self, topic: str, top_k: int):
        pass


class Bloomberg(News):

    source = "bloomberg"

    @retry_on_error()
    def get_article_content(self, article_url: str) -> (str, int): # type: ignore
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
    
    def get_brief(self, topic: str, translate: bool):
        articles = self.get_articles(topic)
        for article in articles:
            print("-"*30)
            print(f"title: {article.title}")
            if translate:
                print(f"translated title: {translate_text(article.title)}")
            print(f"url: {article.url}")
            print(f"brief: ")
            brief = article.description
            text_output(brief)
            if translate:
                print(f"translated brief: ")
                text_output(translate_text(brief))
            print("-"*30)

if __name__ == "__main__":
    args = parser.parse_args()
    if args.source == "bloomberg":
        client = Bloomberg()
        if args.url:
            article_content = client.get_article_content(args.url)
            print("-"* 100)
            text_output(article_content)
            print("-"* 100)
            if args.summary:
                text_output(llm.generate_summary(article_content))
                print("-"* 100)
        else:
            client.get_brief(args.topic, translate=args.translate)
    else:
        raise NotImplemented(f"{args.source} is not implemented.")
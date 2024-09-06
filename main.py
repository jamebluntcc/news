import argparse
from models import llm
from tools import text_output
from sources import Bloomberg, Reuters, sources


parser = argparse.ArgumentParser(
                    prog='get latest news.',
                    description=f'get latest news from {",".join(sources)}')
parser.add_argument('-t', '--topic', help="your interest topic", default="")
parser.add_argument('-s', '--source', help="news's source", default="bloomberg")
parser.add_argument('-l', "--url", help="article url, to get whole content", default="")
parser.add_argument('--summary', help="summary article by llm", default=False, action="store_true")



if __name__ == '__main__':
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
            client.get_brief(args.topic)
    elif args.source == "reuters":
        client = Reuters()
        if args.url:
            article_content = client.get_article_content(args.url)
            print("-"* 100)
            text_output(article_content)
            print("-"* 100)
            if args.summary:
                text_output(llm.generate_summary(article_content))
                print("-"* 100)
        else:
            client.get_brief(args.topic)
    else:
        raise NotImplemented(f"{args.source} is not implemented.")
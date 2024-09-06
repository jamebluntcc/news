import time
import loguru
import requests
from common import OK


logger = loguru.logger


def text_output(text: str, max_line_num=100):
    start = 0
    total_len = len(text)
    while total_len > max_line_num:
        print(text[start : start + max_line_num])
        start += max_line_num
        total_len -= max_line_num
    print(text[start:])


def translate_text(text):
    data = [text, "en", "zh"]
    url = "https://hf.space/embed/mikeee/gradio-deepl/+/api/predict"
    resp = requests.post(url, json={"data": data})
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
                    time.sleep(1 + n)
            return result

        return inner

    return wrapper

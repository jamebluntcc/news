from langchain_community.llms import Ollama
from langchain_openai import OpenAI
from langchain.schema.runnable import RunnableSequence
from langchain.prompts import PromptTemplate
from tools import logger


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
        self.summary_chain = self.summary_prompt_template | llm
        self.translate_chain = self.translate_prompt_template | llm

    def generate_summary(self, content: str) -> str:
        logger.info("Generating summary...")
        summary_content = self.summary_chain.run(content)
        logger.info("Summary generated. and translate...")
        return self.translate(summary_content)
    
    def translate(self, content: str) -> str:
        return self.translate_chain.run(content)
    
llm = LLM(model_type="Ollama", model_id="qwen-chat-14B-Q4_0:latest")

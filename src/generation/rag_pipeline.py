import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from ai_prompter import Prompter
from src.retrieval.vector_store import get_retriever

# 集中式提示存储库初始化
prompter = Prompter(prompt_dir="src/prompts")


def format_docs(docs):
    """
    将检索召回的 Document 列表格式化为纯文本字符串组合。
    """
    return "\n\n".join(doc.page_content for doc in docs)

def build_rag_chain():
    """
    使用 LCEL (LangChain Expression Language) 构建多模态 RAG 核心流水线
    """
    retriever = get_retriever()
    
    # 初始化作为大脑的 LLM/VLM (如需多模态推荐使用 gpt-4o 或 gpt-4-vision-preview)
    llm = ChatOpenAI(
        model="gpt-4o",
        api_key=os.getenv("OPENAI_API_KEY", "dummy-key-for-dev"),
        temperature=0.3,
        streaming=True # 开启流式输出
    )
    
    # 从集中式提示库加载 Jinja2 模板内容
    rag_prompt_template = prompter.get_prompt("rag_prompt.jinja2")

    # 使用从集中式存储库中获取的内容初始化 Prompt Template
    prompt = ChatPromptTemplate.from_template(rag_prompt_template, template_format="jinja2")

    # 核心 LCEL 链：
    # 1. 接受 question
    # 2. retriever 根据 question 召回 context，并组装进字典
    # 3. 将字典传入 prompt 模板
    # 4. 传入 LLM
    # 5. StrOutputParser 解析为纯文本流
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    
    return rag_chain

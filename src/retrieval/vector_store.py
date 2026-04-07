import os
from langchain_community.vectorstores import Qdrant
from langchain_openai import OpenAIEmbeddings

def get_vector_store():
    """
    初始化并返回 Qdrant 向量数据库实例。
    """
    api_key = os.getenv("OPENAI_API_KEY", "dummy-key-for-dev")
    embeddings = OpenAIEmbeddings(api_key=api_key)
    
    qdrant_host = os.getenv("QDRANT_HOST", "localhost")
    qdrant_port = os.getenv("QDRANT_PORT", "6333")
    
    # 骨架示例：目前使用内存模式进行开发占位
    # 生产环境中应替换为 url=f"http://{qdrant_host}:{qdrant_port}"
    vector_store = Qdrant.from_documents(
        documents=[],
        embedding=embeddings,
        location=":memory:", 
        collection_name="github_repo_multi_modal"
    )
    return vector_store

def get_retriever():
    """
    返回用于检索的 Retriever 接口。
    可以配置 MMR（最大边际相关性）或普通相似度检索。
    """
    vs = get_vector_store()
    # k为单次检索召回的 Document 数量
    return vs.as_retriever(search_type="similarity", search_kwargs={"k": 5})

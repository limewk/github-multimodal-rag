from langchain_text_splitters import RecursiveCharacterTextSplitter, Language

def split_markdown(text: str) -> list:
    """
    对 Markdown 文本文档进行切分
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    return splitter.split_text(text)

def split_code(code: str, language: Language) -> list:
    """
    基于特定编程语言（如 Python, JS）的语法树特征切分代码。
    这样可以尽量保持函数或类作为一个完整的块。
    """
    splitter = RecursiveCharacterTextSplitter.from_language(
        language=language, 
        chunk_size=500, 
        chunk_overlap=50
    )
    return splitter.split_text(code)

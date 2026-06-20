import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


_embeddings = None



def get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
    return _embeddings


def get_user_vectorstore(user_id: str):

    persist_dir = f"chroma_db/{user_id}"

    os.makedirs(persist_dir, exist_ok=True)

    return Chroma(
        persist_directory=persist_dir,
        embedding_function=get_embeddings()
    )


def get_retriever(user_id: str):

    vectorstore = get_user_vectorstore(user_id)

    return vectorstore.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 5,
            "fetch_k": 20
        }
    )
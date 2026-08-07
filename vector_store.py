import os
import logging

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

logger = logging.getLogger(__name__)


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


def clear_user_vectorstore(user_id: str):
    """
    Wipes all indexed website content for this user - called when their
    last website is deleted (see api/website.py's DELETE /website), so old
    page embeddings don't linger in Chroma and keep surfacing in AI
    answers after the site itself is gone from Settings.

    Safe to call even if nothing was ever indexed for this user - Chroma
    raises if there's no collection to delete, which we just log and
    swallow rather than fail the whole delete-website request over.
    """

    try:

        vectorstore = get_user_vectorstore(user_id)
        vectorstore.delete_collection()

    except Exception as e:

        logger.info(
            f"clear_user_vectorstore: nothing to clear for {user_id}: {e}"
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
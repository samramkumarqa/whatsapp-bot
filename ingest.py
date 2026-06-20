from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from website_ingest import load_website_chunks
from dedupe import remove_duplicate_chunks

import os


def ingest_docs():

    web_chunks = load_website_chunks()

    if not web_chunks:
        print("⚠️ No website data found")
        return

    # optional dedupe
    web_chunks = remove_duplicate_chunks(web_chunks)

    print(f"🌐 Web chunks: {len(web_chunks)}")

    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vectorstore = Chroma(
        persist_directory="chroma_db",
        embedding_function=embeddings
    )

    vectorstore.add_documents(web_chunks)

    print("✅ Incremental indexing completed")
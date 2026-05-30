from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from dotenv import load_dotenv
load_dotenv()

def ingest_docs():
    loader   = PyPDFDirectoryLoader("docs/")
    docs     = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks   = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    Chroma.from_documents(chunks, embeddings, persist_directory="chroma_db")
    print(f"✅ Indexed {len(chunks)} chunks from {len(docs)} pages.")

if __name__ == "__main__":
    ingest_docs()
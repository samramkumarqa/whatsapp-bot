from groq import AsyncGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
import os
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory="chroma_db", embedding_function=embeddings)
retriever   = vectorstore.as_retriever(search_kwargs={"k": 3})

client = AsyncGroq(api_key=GROQ_API_KEY)

async def handle_rag(user_message: str) -> str:
    docs    = retriever.invoke(user_message)
    context = "\n\n".join([d.page_content for d in docs])

    response = await client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant. Answer using only the context below. "
                    "If the answer is not in the context, say: "
                    "'I could not find that in our documents.'\n\n"
                    f"Context:\n{context}"
                )
            },
            {"role": "user", "content": user_message}
        ]
    )
    return response.choices[0].message.content
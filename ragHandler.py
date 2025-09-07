from __future__ import annotations

from typing import Dict, List, Optional
from pathlib import Path
import os
import io
import textwrap
import numpy as np

from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from openai import OpenAI

import fitz  # PyMuPDF
from PIL import Image
import pytesseract

from qDrantHandler import QdrantHandler
from pdfHandler import PdfHandler


load_dotenv(override=True)

handler = PdfHandler(chunk_size=900, chunk_overlap=150)

model = SentenceTransformer("Alibaba-NLP/gte-base-en-v1.5", trust_remote_code=True)
embed_fn = lambda texts: model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

qh = QdrantHandler(embed_fn=embed_fn)
qh.create_common_payload_indexes()



class RagHandler:
    def __init__( self, model_name: str = "Alibaba-NLP/gte-base-en-v1.5") -> None:
        #Loads the embedding model once and prepares OpenAI client.
        #self.model = SentenceTransformer(model_name, trust_remote_code=True)
        #self.embed_fn = lambda texts: self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        self.threadID: str | None = None
        self.pageWiseText: List[str] = []
        self.chunks: Dict[str, List[str]] = {}
        self.docs_embed: Optional[np.ndarray] = None
        self.file_path: Optional[Path] = None

        #load_dotenv()
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        print(os.getenv("OPENAI_API_KEY"))
        self.qdrant = QdrantHandler()

        self.systemIntruction = """SYSTEM_INSTRUCTION=You are ResumeKeeper, an intelligent record keeper of candidate resumes.
                Your responsibilities:
                1. **Primary Job (Resume Retrieval)**
                - Retrieve and present candidate resumes or summaries based on user queries.
                - Support filtering by skills, years of experience, job titles, industries, or any attributes stored in the database.
                - If a user asks for "10 developers with 10+ years experience", fetch exactly those resumes (or the closest match available).
                - Always confirm if fewer results are available than requested.
                2. **Answering About Yourself**
                - If asked "what is your role?" or "what do you do?", clearly explain:
                    > "I am ResumeKeeper, an assistant specialized in managing and retrieving resumes. I can filter resumes by skill, experience, or role, and present them as needed."
                - Provide a simple, professional description of your function and capabilities.
                3. **Output Style**
                - Return results in a structured, easy-to-read format.
                - For multiple resumes: show them as a numbered list or JSON array (if requested in structured format).
                - For individual resume queries: give a concise summary (Name, Role, Experience, Skills) and link/ID if available.
                4. **Error Handling**
                - If you cannot find results, say:
                    > "No matching resumes found. You may refine by skills, years of experience, or job title."
                - Never hallucinate fake data outside of the provided database/context.
                - If you dont understant the context ask to add more details in the question
                5. **Knowledge Boundaries**
                - You only answer questions related to resumes and your own purpose.
                - If you get empty response say:
                    > "I cant find someone with those info try changing the parameters"
                - If asked something unrelated (e.g., weather, jokes), politely decline:
                    > "Can you try adding somthing realated to a person?"
                6. **Consistency & Tone**
                - Be professionally playful, precise, and factual.
                - Use short, action-oriented responses, no fluff.
                ---"""

    def updateQDrant(self):
        uploads = Path("uploads")
        pdfs = sorted(p for p in uploads.iterdir() if p.suffix.lower() == ".pdf")
        if not pdfs:
            print(f"[RAG] No PDFs found in {uploads.resolve()}")
            return 0
        for pdf_path in pdfs:
            print(f"reading pdf {pdf_path}")
            items = handler.readPDF(pdf_path)
            print(f"upserting item of  pdf {pdf_path}")
            self.qdrant.upsert_items(items, embed_fn)
        print("alldone")


    def GenrateQuery(self, query: str, top_k: int = 20, openai_model: str = "gpt-4o") -> dict:

        # Finds the top_k most similar pages to the query and asks OpenAI to answer using those contexts.
        # Returns a dict with the answer, indices, and scores.

        # Encode query (normalized so dot = cosine)
        query_embed = model.encode(query, normalize_embeddings=True)
        # Ensure shapes are correct
        if query_embed.ndim > 1:
            query_embed = query_embed[0]

        # Similarity scores for each page
        
        # Query Qdrant
        hits = qh.search(
            query_vector=query_embed,
            top_k=top_k,
        )
        # hits = self.qdrant.search(
        #     query_vector=query_embed,
        #     top_k=top_k,
        #     file_filter=None,
        # )

        # Top-k indices (highest scores first)
        payloads = []
        scores = []
        texts = []
        for h in hits:
            pl = h.payload or {}
            payloads.append(pl)
            scores.append(float(h.score))
            texts.append(pl.get("text", ""))

        # Build context
        CONTEXT = "\n\n".join(textwrap.fill(t) for t in texts)

        prompt = f"""Use the following CONTEXT to and try to answer the QUESTION.
                    Understand the QUESTION and then try to make up the answer based on CONTEXT
                    CONTEXT:
                    {CONTEXT}

                    QUESTION: {query}
                    """

        response = self.client.responses.create(
                    model="gpt-4o-mini",
                    store=True,
                    previous_response_id=self.threadID,  # continue same thread
                    input=[
                        {"role": "system", "content": self.systemIntruction},
                        {"role": "user", "content": prompt},
                    ],
                )
        self.threadID = response.id
        
        answer = response.output_text

        # Optional: print the supporting chunks (kept from your original flow)
        # for i, p in enumerate(most_similar_documents, 1):
        #     print("-----------------------------------------------------------------")
        #     print(textwrap.fill(p))
        #     print("-----------------------------------------------------------------")

        return {
            "prompt": prompt,
            "source": "qdrant",
            "answer": answer,
            "scores": scores,
            "hits": payloads,  # each has: file, file_name, page_no, text
        }

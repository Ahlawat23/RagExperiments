import os
import textwrap
import PyPDF2
import numpy as np
from sentence_transformers import SentenceTransformer
from typing import List


class RAGHandler:
    def __init__(self, embedding_model="Alibaba-NLP/gte-base-en-v1.5"):
        # Load embedding model
        self.model = SentenceTransformer(embedding_model, trust_remote_code=True)
        self.docs = []
        self.embeddings = None

    def load_pdf(self, file_path: str) -> List[str]:
        """Extracts text page by page from a PDF"""
        page_texts = []
        with open(file_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    page_texts.append(text)
        self.docs = page_texts
        print(f"Extracted {len(page_texts)} pages from {file_path}")
        return page_texts

    def save_to_txt(self, file_path: str, width: int = 100) -> str:
        """Save extracted text into a .txt file (pretty formatted)"""
        if not self.docs:
            raise ValueError("No documents loaded. Call load_pdf first.")
        
        output_path = os.path.splitext(file_path)[0] + ".txt"
        all_text = ""
        for p in self.docs:
            wrapped_text = textwrap.fill(p, width=width)
            all_text += "\n" + ("-"*65) + "\n"
            all_text += wrapped_text
            all_text += "\n" + ("-"*65) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(all_text)

        print(f"Saved extracted text to {output_path}")
        return output_path

    def embed_documents(self):
        """Embed all loaded documents"""
        if not self.docs:
            raise ValueError("No documents loaded. Call load_pdf first.")
        self.embeddings = self.model.encode(self.docs, normalize_embeddings=True)
        print(f"Created embeddings with shape {self.embeddings.shape}")
        return self.embeddings

    def query(self, text: str, top_k: int = 3) -> List[str]:
        """Retrieve most relevant pages using cosine similarity"""
        if self.embeddings is None:
            raise ValueError("No embeddings found. Call embed_documents first.")
        
        query_vec = self.model.encode([text], normalize_embeddings=True)[0]
        sims = np.dot(self.embeddings, query_vec)  # cosine sim (since normalized)
        top_idx = np.argsort(sims)[::-1][:top_k]
        return [self.docs[i] for i in top_idx]




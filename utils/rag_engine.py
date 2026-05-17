"""
RAG Engine
Retrieval-Augmented Generation over detection logs
Uses sentence-transformers for embedding + FAISS for retrieval
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime


class RAGEngine:
    """
    Simple RAG system:
    1. Convert each log row → text passage
    2. Embed passages with sentence-transformers
    3. At query time: embed query, find top-k passages via FAISS
    4. Synthesize answer from retrieved context
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", top_k: int = 10):
        self.top_k = top_k
        self.model = None
        self.index = None
        self.passages = []
        self._load_model(model_name)

    def _load_model(self, model_name: str):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            self.model = None  # Fallback to keyword search

    def build_index(self, logs_df: pd.DataFrame):
        """Convert logs to text passages and build FAISS index."""
        self.passages = []
        for _, row in logs_df.iterrows():
            text = (
                f"On {row['timestamp']}, a person named {row['name']} was detected. "
                f"Status: {row['status']}. Confidence: {row.get('confidence', 'N/A')}."
            )
            self.passages.append({"text": text, "row": row.to_dict()})

        if not self.passages:
            return

        if self.model is not None:
            try:
                import faiss
                texts = [p["text"] for p in self.passages]
                embeddings = self.model.encode(texts, convert_to_numpy=True)
                embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)
                dim = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dim)
                self.index.add(embeddings.astype(np.float32))
            except ImportError:
                self.index = None

    def _retrieve(self, query: str, k: int = None) -> list:
        """Retrieve top-k relevant passages."""
        k = k or self.top_k

        if self.model is not None and self.index is not None:
            try:
                import faiss
                q_emb = self.model.encode([query], convert_to_numpy=True)
                q_emb = q_emb / np.linalg.norm(q_emb, axis=1, keepdims=True)
                _, idxs = self.index.search(q_emb.astype(np.float32), min(k, len(self.passages)))
                return [self.passages[i] for i in idxs[0] if i < len(self.passages)]
            except Exception:
                pass

        # Keyword fallback
        query_lower = query.lower()
        keywords = set(re.findall(r'\w+', query_lower))
        scored = []
        for p in self.passages:
            score = sum(1 for kw in keywords if kw in p["text"].lower())
            scored.append((score, p))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [p for _, p in scored[:k]]

    def query(self, question: str, logs_df: pd.DataFrame) -> str:
        """
        Answer a natural language question using retrieved log context.
        Uses rule-based synthesis over retrieved passages.
        """
        if not self.passages:
            return "No log data available. Please run Live Detection first."

        question_lower = question.lower()
        retrieved = self._retrieve(question)

        # ---- Analytical answers from full DataFrame ----
        if any(kw in question_lower for kw in ["how many", "count", "total", "number of"]):
            return self._answer_count(question_lower, logs_df)

        if any(kw in question_lower for kw in ["who", "which person", "list"]):
            return self._answer_who(question_lower, logs_df, retrieved)

        if any(kw in question_lower for kw in ["when", "last seen", "time", "latest"]):
            return self._answer_when(question_lower, logs_df)

        if any(kw in question_lower for kw in ["most frequent", "most often", "most detected"]):
            return self._answer_most_frequent(logs_df)

        # Generic: summarize retrieved passages
        if not retrieved:
            return "I couldn't find relevant information in the surveillance logs for that query."

        summary_lines = [f"• {p['text']}" for p in retrieved[:5]]
        return (
            f"Based on the surveillance logs, here are the most relevant records:\n\n"
            + "\n".join(summary_lines)
            + f"\n\n_(Showing {len(summary_lines)} of {len(self.passages)} total log entries)_"
        )

    def _answer_count(self, q: str, df: pd.DataFrame) -> str:
        if "unknown" in q:
            n = len(df[df["status"] == "UNKNOWN"])
            return f"There are **{n} unknown person detections** in the surveillance logs."
        if "known" in q:
            n = len(df[df["status"] == "KNOWN"])
            return f"There are **{n} known person detections** in the logs."
        if "today" in q:
            today = datetime.now().strftime("%Y-%m-%d")
            n = len(df[df["timestamp"].str.startswith(today)])
            return f"**{n} detections** were recorded today ({today})."
        return f"The surveillance system has logged a total of **{len(df)} detection events**."

    def _answer_who(self, q: str, df: pd.DataFrame, retrieved: list) -> str:
        if "today" in q:
            today = datetime.now().strftime("%Y-%m-%d")
            today_df = df[df["timestamp"].str.startswith(today)]
            names = today_df["name"].unique().tolist()
            if not names:
                return "No persons were detected today."
            return f"**Persons detected today:** {', '.join(names)}"
        if "unknown" in q:
            unknowns = df[df["status"] == "UNKNOWN"]["timestamp"].tolist()
            if not unknowns:
                return "No unknown persons have been detected."
            return f"**{len(unknowns)} unknown person events** have been recorded. Timestamps: " + "; ".join(unknowns[:5]) + ("..." if len(unknowns) > 5 else "")
        # List all unique persons
        names = df["name"].unique().tolist()
        return f"**All detected persons:** {', '.join(names)}"

    def _answer_when(self, q: str, df: pd.DataFrame) -> str:
        # Try to find a name in question
        words = q.split()
        for i, word in enumerate(words):
            if word in ["was", "last", "seen", "detected", "when"]:
                continue
            # Try matching to known name
            for name in df["name"].unique():
                if word.lower() in name.lower():
                    person_df = df[df["name"] == name].sort_values("timestamp", ascending=False)
                    if not person_df.empty:
                        last = person_df.iloc[0]["timestamp"]
                        return f"**{name}** was last detected at **{last}**."
        # Most recent event
        latest = df.sort_values("timestamp", ascending=False).iloc[0]
        return f"The most recent detection was **{latest['name']}** ({latest['status']}) at **{latest['timestamp']}**."

    def _answer_most_frequent(self, df: pd.DataFrame) -> str:
        counts = df["name"].value_counts()
        if counts.empty:
            return "No detection data available."
        top_name = counts.index[0]
        top_count = counts.iloc[0]
        return f"**{top_name}** is the most frequently detected person with **{top_count} detections**."

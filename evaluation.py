import json, os, time
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from dotenv import load_dotenv

with open("cleaned_faq.json", encoding="utf-8") as f:
    faq = json.load(f)

QUESTIONS = [item["question"] for item in faq]
ANSWERS   = [item["answer"]   for item in faq]
QUESTIONS = QUESTIONS[0:100]
ANSWERS   = ANSWERS[0:100] 

EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
GEMINI = genai.GenerativeModel("gemini-pro")

QUESTION_EMB = EMBED_MODEL.encode(QUESTIONS, normalize_embeddings=True)   # (N, d)
ANSWER_EMB   = EMBED_MODEL.encode(ANSWERS,   normalize_embeddings=True)   # (N, d)  # for later scoring

# If you already have a Chroma DB with the questions embedded, plug it in here.
# Otherwise we’ll fall back to plain cosine similarity search.
CHROMA_DB = None               # ← inject your vector store instance if available
TOP_K     = 1                  # always take the best hit


def retrieve_with_chroma(query: str, top_k: int = 1):
    """Return [(question, answer, similarity)] using Chroma or in-memory search."""
    if CHROMA_DB is not None:
        results = CHROMA_DB.similarity_search_with_score(query, k=top_k)
        hits = []
        for doc, chroma_score in results:
            if doc.page_content.strip().lower() == query.strip().lower():
                continue
            sim = evaluate_similarity(query, doc.page_content)
            hits.append((doc.page_content, doc.metadata["answer"], sim))
        return hits[:top_k]

    # ─ fallback: cosine sim against QUESTION_EMB ─
    q_vec = EMBED_MODEL.encode([query], normalize_embeddings=True)
    sims  = cosine_similarity(q_vec, QUESTION_EMB)[0]          # (N,)
    best = sims.argsort()[::-1][:top_k]
    return [(QUESTIONS[i], ANSWERS[i], sims[i]) for i in best]


def evaluate_similarity(text_a: str, text_b: str) -> float:
    """Semantic similarity in [-1, 1]."""
    emb = EMBED_MODEL.encode([text_a, text_b], normalize_embeddings=True)
    return cosine_similarity(emb[0:1], emb[1:2])[0, 0]


def call_gemini(prompt: str) -> str:
    """Robust Gemini wrapper → plain text string."""
    try:
        resp = GEMINI.generate_content(prompt)
        return resp.text.strip() if hasattr(resp, "text") and resp.text else ""
    except Exception as exc:
        print("Gemini error:", exc)
        return ""

records = []

for q, gt in zip(QUESTIONS, ANSWERS):
    # ---------- Retrieval ----------
    t0 = time.time()
    hits = retrieve_with_chroma(q, top_k=TOP_K)
    t1 = time.time()

    if hits:
        _, retrieved_answer, _ = hits[0]
        retr_acc = evaluate_similarity(retrieved_answer, gt)
    else:
        retrieved_answer, retr_acc = "", 0.0

    # ---------- LLM ----------
    t2 = time.time()
    llm_answer = call_gemini(
        f"A user asked: “{q}”. "
        "Answer in a concise, friendly tone suited for banking FAQs."
    )
    t3 = time.time()

    llm_acc = evaluate_similarity(llm_answer, gt)

    records.append(
        {
            "question": q,
            "ground_truth": gt,
            "retrieved_answer": retrieved_answer,
            "retrieval_similarity": retr_acc,
            "retrieval_latency_sec": t1 - t0,
            "llm_answer": llm_answer,
            "llm_similarity": llm_acc,
            "llm_latency_sec": t3 - t2,
        }
    )

df = pd.DataFrame(records)

# ──────────────────────────────────────────────────────────────────────────────
# 4. Aggregate metrics
# ──────────────────────────────────────────────────────────────────────────────
print("\n📊 Retrieval-based:")
print(f"  • Avg semantic similarity: {df['retrieval_similarity'].mean():.4f}")
print(f"  • Avg latency:             {df['retrieval_latency_sec'].mean():.2f}s")

print("\n🤖 Gemini LLM:")
print(f"  • Avg semantic similarity: {df['llm_similarity'].mean():.4f}")
print(f"  • Avg latency:             {df['llm_latency_sec'].mean():.2f}s")

df.to_csv("faq_comparison_report.csv", index=False)
print("\n✅ Saved faq_comparison_report.csv")

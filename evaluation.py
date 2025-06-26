import json
import os
import time
import google.generativeai as genai
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd

# 1. Load FAQ data
with open("cleaned_faq.json", "r", encoding="utf-8") as f:
    faq_data = json.load(f)

# 2. Init Gemini LLM
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
llm = genai.GenerativeModel("gemini-pro")

# 3. Init Embedding Model
model = SentenceTransformer("all-MiniLM-L6-v2")

# 4. Prepare corpus and embeddings
questions = [item["question"] for item in faq_data]
answers = [item["answer"] for item in faq_data]
answer_embeddings = model.encode(answers, normalize_embeddings=True)

# 5. Loop through all questions and evaluate
retrieval_similarities = []
llm_similarities = []
retrieval_latencies = []
llm_latencies = []

results = []

for i, item in enumerate(faq_data):
    question = item["question"]
    ground_truth = item["answer"]

    # Encode question
    question_vec = model.encode([question], normalize_embeddings=True)

    # --- Retrieval-based ---
    start_r = time.time()
    sims = cosine_similarity(question_vec, answer_embeddings)[0]
    best_idx = np.argmax(sims)
    best_answer = answers[best_idx]
    retrieval_score = sims[best_idx]
    end_r = time.time()

    # --- LLM-based ---
    start_l = time.time()
    prompt = f"A user asked: '{question}'. Based on typical banking FAQs, respond in a simple, friendly tone."
    llm_response = llm.generate_content(prompt)
    llm_answer = llm_response.text.strip() if llm_response.text else ""
    end_l = time.time()

    # Semantic similarity between LLM answer and GT
    llm_score = cosine_similarity(
        model.encode([llm_answer], normalize_embeddings=True),
        model.encode([ground_truth], normalize_embeddings=True)
    )[0][0]

    results.append({
        "question": question,
        "retrieved_answer": best_answer,
        "retrieval_similarity": retrieval_score,
        "retrieval_latency": end_r - start_r,
        "llm_answer": llm_answer,
        "llm_similarity": llm_score,
        "llm_latency": end_l - start_l
    })

    retrieval_similarities.append(retrieval_score)
    retrieval_latencies.append(end_r - start_r)
    llm_similarities.append(llm_score)
    llm_latencies.append(end_l - start_l)

# 6. Final average scores
print(f"\n📊 Retrieval:")
print(f" - Avg Cosine Similarity (Accuracy Proxy): {np.mean(retrieval_similarities):.4f}")
print(f" - Avg Latency: {np.mean(retrieval_latencies):.2f} seconds")

print(f"\n🤖 LLM (Gemini):")
print(f" - Avg Semantic Similarity: {np.mean(llm_similarities):.4f}")
print(f" - Avg Latency: {np.mean(llm_latencies):.2f} seconds")

# Optional: save results
pd.DataFrame(results).to_csv("faq_comparison_report.csv", index=False)

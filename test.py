import sys, json, pprint, pathlib, time
from faq_logic import FAQBot   # <-- adjust if your class lives in another module
if __name__ == "__main__":
    # ──────────────────────────────────────────────────────────────────────────────
    # 1.  Define test questions (override via CLI)
    # ──────────────────────────────────────────────────────────────────────────────
    SAMPLE_QUERIES = [
        "How can I block my debit card?",
        "What is the daily UPI transfer limit?",
        "Is there a fee for ATM withdrawal?",
    ]

    queries = sys.argv[1:] if len(sys.argv) > 1 else SAMPLE_QUERIES
    print(f"\nRunning FAQBot test on {len(queries)} question(s)…\n")

    # ──────────────────────────────────────────────────────────────────────────────
    # 2.  Instantiate the bot
    # ──────────────────────────────────────────────────────────────────────────────
    start = time.time()
    bot = FAQBot(faq_file_path="cleaned_faq.json", similarity_threshold=0.7)
    print(f"Bot ready in {time.time() - start:,.1f}s – {bot.get_stats()['total_faqs']} FAQs loaded\n")

    # ──────────────────────────────────────────────────────────────────────────────
    # 3.  Evaluate each query
    # ──────────────────────────────────────────────────────────────────────────────
    all_pass = True
    for q in queries:
        try:
            res = bot.answer_question(q)
            print("Q:", q)
            print("A:", res["response"])
            print(f"Similarity: {res['similarity_score']:.3f}  Source: {res['source']}")
            if res["related_questions"]:
                print("Related:", [r["question"] for r in res["related_questions"]])
            print("-" * 70)

            if res["similarity_score"] < bot.similarity_threshold:
                all_pass = False
        except Exception as e:
            print(f"❌ Error processing query '{q}': {e}")
            import traceback
            traceback.print_exc()
            all_pass = False

    # ──────────────────────────────────────────────────────────────────────────────
    # 4.  CI‑friendly exit status
    # ──────────────────────────────────────────────────────────────────────────────
    if all_pass:
        print("✅  All queries met the similarity threshold.")
    else:
        print("❌  At least one query fell below the similarity threshold.")

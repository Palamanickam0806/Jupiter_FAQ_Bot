# Jupiter FAQ Bot

The **Jupiter FAQ Bot** is a Flask-based web application designed to provide instant, conversational answers to user queries about Jupiter's financial services, such as payments, cards, KYC, and rewards. It leverages natural language processing (NLP), semantic search with ChromaDB, and Google's Gemini 1.5 Flash LLM to deliver accurate and user-friendly responses. The system includes a web crawler to extract FAQs, a preprocessing pipeline to clean and categorize data, and a web interface for user interaction.

## Features

- **Web Crawler**: Extracts FAQs from Jupiter's website using a breadth-first search (BFS) with multiple extraction strategies.
- **Data Preprocessing**: Cleans HTML, normalizes text, categorizes FAQs (e.g., KYC, Rewards), and deduplicates similar questions.
- **Semantic Search**: Uses `sentence-transformers/all-MiniLM-L6-v2` for embedding-based search in ChromaDB.
- **Conversational Responses**: Rephrases FAQ answers using Gemini 1.5 Flash for a friendly tone.
- **Fallback Logic**: Gracefully handles irrelevant or unanswerable queries with suggestions to contact support.
- **Web Interface**: A responsive Flask-based UI for user queries, with related question suggestions.
- **Evaluation**: Compares retrieval-based and LLM-based approaches for accuracy and latency.
- **Bonus**: Suggests related queries based on semantic similarity.

## Architecture

1. **Web Crawler** (`crawler.py`):

   - Uses BFS to crawl up to 150 pages, avoiding non-HTML content (e.g., PDFs).
   - Employs extraction strategies for FAQ-specific divs, accordions, and text patterns.
   - Saves FAQs incrementally to `faqs_2.json`.

2. **Data Preprocessing** (`data.py`):

   - Cleans HTML and noise using BeautifulSoup and regex.
   - Normalizes text (lowercase, stopword removal, lemmatization) with NLTK.
   - Categorizes FAQs into topics (e.g., KYC, Payments) using fuzzy matching.
   - Deduplicates questions with `fuzzywuzzy` (threshold: 90).
   - Outputs cleaned data to `cleaned_faq.json`.

3. **Embedding Model**:

   - Uses `sentence-transformers/all-MiniLM-L6-v2` for semantic embeddings.
   - Supports ONNX-based `ONNXMiniLM_L6_V2` for optimized CPU inference (configurable via `USE_ONNX`).

4. **Vector Database**:

   - ChromaDB stores FAQ embeddings with metadata (answers, categories, URLs).
   - Enables cosine similarity-based search for relevant FAQs.

5. **LLM Integration**:

   - Google Gemini 1.5 Flash (`gemini-1.5-flash`) rephrases answers conversationally.
   - Configurable via `GOOGLE_API_KEY`, with a prompt template for friendly responses.

6. **Flask Application** (`main_bot.py`):

   - Endpoints:
     - `/`: Web interface for user queries.
     - `/ask`: Handles POST requests for questions (form or JSON).
     - `/api/ask`: JSON API for programmatic access.
     - `/evaluate`: Tests predefined queries for accuracy and latency.
     - `/health`: Checks service status and FAQ count.
   - Features a chat-like UI with loading animations and related question suggestions.

## Prerequisites

- Python 3.8+

- Google API key for Gemini (`GOOGLE_API_KEY`)

- Required packages:

  ```bash
  pip install flask langchain langchain-community langchain-google-genai chromadb sentence-transformers onnx nltk fuzzywuzzy pandas beautifulsoup4 requests
  ```

## Setup Instructions

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/Palamanickam0806/Jupiter_FAQ_Bot.git
   cd Jupiter_FAQ_Bot
   ```

2. **Set Up Environment**:

   - Create a `.env` file in the project root:

     ```plaintext
     GOOGLE_API_KEY=<your-google-api-key>
     FAQ_FILE_PATH=cleaned_faq.json
     USE_ONNX=false
     SIMILARITY_THRESHOLD=0.7
     PORT=5000
     ```

   - Install dependencies:

     ```bash
     pip install -r requirements.txt
     ```

3. **Prepare FAQ Data** (if not already available):

   - Run the crawler to generate `faqs_2.json`:

     ```bash
     python crawler.py
     ```

   - Preprocess the data to create `cleaned_faq.json`:

     ```bash
     python data.py
     ```

4. **Run the Application**:

   ```bash
   python main_bot.py
   ```

   - The app will be available at `http://localhost:5000`.

## Usage

- **Web Interface**: Open `http://localhost:5000` in a browser, enter a question, and view the response with related question suggestions.

- **API Access**: Send POST requests to `http://localhost:5000/api/ask`:

  ```bash
  curl -X POST -H "Content-Type: application/json" -d '{"question":"What are the fees for the Edge card?"}' http://localhost:5000/api/ask
  ```

- **Health Check**: Verify service status:

  ```bash
  curl http://localhost:5000/health
  ```

- **Evaluation**: Test retrieval vs. LLM-based responses:

  ```bash
  curl http://localhost:5000/evaluate
  ```

## Example Output

**User Query**: "What are the fees for the Edge+ card?" **Response**:

```json
{
  "response": "The Edge+ card has a one-time joining fee of ₹499 plus GST, which includes a Fraud Protection Plan with an Amazon Prime Membership worth ₹1499. There’s no annual fee—it’s free for life!",
  "related_questions": [
    {"question": "What benefits does the Edge+ card offer?", "score": 0.85},
    {"question": "How do I apply for the Edge+ card?", "score": 0.78}
  ],
  "similarity_score": 0.92
}
```

## Limitations

- The `all-MiniLM-L6-v2` model may struggle with highly nuanced questions.
- ChromaDB is suited for small to medium datasets; larger datasets may require Pinecone or Weaviate.
- Persistence relies on local storage, which may not scale for distributed deployments.
- Gemini API latency may affect response times for LLM-based answers.

## Evaluation

- **Semantic Similarity**: Measured using cosine similarity of embeddings, logged in the `/evaluate` endpoint.
- **Retrieval vs. LLM**: Retrieval-based responses are faster and more accurate for known FAQs, while LLM-based responses handle novel queries but risk hallucination.
- **Suggestions**: Related questions are generated based on embedding similarity, enhancing user experience.

## Contributing

Contributions are welcome! Please submit issues or pull requests to the repository at `https://github.com/Palamanickam0806/Jupiter_FAQ_Bot`.


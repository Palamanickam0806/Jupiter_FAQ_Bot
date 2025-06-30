import json
import os
import logging
from typing import List, Dict, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableSequence
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.output_parsers import StrOutputParser
from sklearn.metrics.pairwise import cosine_similarity
from dotenv import load_dotenv


load_dotenv()
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
USE_ONNX = os.getenv("USE_ONNX", "false").lower() == "true"


class FAQBot:
    def __init__(self, faq_file_path: str = 'cleaned_faq.json', similarity_threshold: float = 0.7):
        self.similarity_threshold = similarity_threshold
        logger.info("Loading FAQ data...")
        self.faq_data = self._load_faq_data(faq_file_path)
        logger.info("Initializing embeddings...")
        self.embedding_model = self._initialize_embeddings()
        logger.info("Initializing Chroma DB...")
        self.chroma_db = self._initialize_chroma_db()
        logger.info("Chroma DB initialized.")
        logger.info("Initializing LLM...")
        self.llm = self._initialize_llm()
        logger.info("LLM initialized.")
        logger.info("Creating chain...")
        self.chain = self._create_chain()
        logger.info("FAQBot initialized successfully.")

    def _load_faq_data(self, file_path: str) -> List[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded {len(data)} FAQ items from {file_path}")
            return data
        except FileNotFoundError:
            logger.error(f"FAQ file not found: {file_path}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in FAQ file: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error loading FAQ data: {e}")
            return []

    def _initialize_embeddings(self):
        try:
            if USE_ONNX:
                from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
                logger.info("Using ONNX embedding model.")
                return ONNXMiniLM_L6_V2()
            else:
                logger.info("Using HuggingFace embedding model.")
                return HuggingFaceEmbeddings(
                    model_name="sentence-transformers/all-MiniLM-L6-v2",
                    model_kwargs={'device': 'cpu'},
                    encode_kwargs={'normalize_embeddings': True}
                )
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise

    def _initialize_chroma_db(self) -> Optional[Chroma]:
        persist_dir = "chroma_db"
        if not self.faq_data:
            logger.warning("No FAQ data available to create Chroma DB")
            return None

        try:
            # Explicitly pass the embedding_function when loading existing DB
            if os.path.exists(persist_dir) and os.listdir(persist_dir):
                logger.info("Existing Chroma DB found, loading from disk...")
                return Chroma(
                    collection_name="faq_collection",
                    embedding_function=self.embedding_model,  # <-- important
                    persist_directory=persist_dir
                )

            texts = [item.get('question', '') for item in self.faq_data if item.get('question')]
            metadatas = [
                {
                    "answer": item.get('answer', ''),
                    "source_url": item.get('source_url', ''),
                    "category": item.get('category', 'General')
                }
                for item in self.faq_data if item.get('question')
            ]

            if not texts:
                logger.error("No valid questions found in FAQ data")
                return None

            db = Chroma.from_texts(
                texts=texts,
                embedding=self.embedding_model,
                metadatas=metadatas,
                collection_name="faq_collection",
                persist_directory=persist_dir
            )
            db.persist()
            logger.info(f"Chroma DB initialized successfully with {len(texts)} documents")
            return db
        except Exception as e:
            logger.error(f"Failed to initialize Chroma DB: {e}", exc_info=True)
            raise


    def _initialize_llm(self) -> GoogleGenerativeAI:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")

        try:
            return GoogleGenerativeAI(
                model="gemini-1.5-flash",
                temperature=0.7,
                google_api_key=api_key,
                max_tokens=500
            )
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            raise

    def _create_chain(self) -> RunnableSequence:
        prompt_template = PromptTemplate(
            input_variables=["question", "answer", "category"],
            template="""
You are a helpful FAQ assistant for Jupiter's financial app.

User Question: "{question}"
Retrieved Answer: "{answer}"
Category: {category}

Instructions:
1. Rephrase the answer in a conversational, friendly tone ,
2. Keep the response concise but informative
3. If the answer doesn't fully match the question, acknowledge this and provide what information you can
4. If you're unsure, suggest contacting Jupiter support
5. Don't make up information not provided in the retrieved answer
6.  If the question is not related to finance, politely redirect to the appropriate support channel

Response:  For general convo like 'hi' or 'how are you', respond with a friendly greeting
"""
        )
        return RunnableSequence(prompt_template | self.llm | StrOutputParser())

    def evaluate_similarity(self, query: str, retrieved_question: str) -> float:
        try:
            q_emb = self.embedding_model.embed_query(query)
            r_emb = self.embedding_model.embed_query(retrieved_question)
            return float(cosine_similarity([q_emb], [r_emb])[0][0])
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0

    def get_related_questions(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.chroma_db:
            return []

        try:
            results = self.chroma_db.similarity_search_with_score(query, k=top_k + 3)
            related = []

            for doc, score in results:
                if doc.page_content.strip().lower() == query.strip().lower():
                    continue
                similarity = self.evaluate_similarity(query, doc.page_content)
                if similarity >= 0.4:
                    related.append({
                        "question": doc.page_content,
                        "score": similarity,
                        "category": doc.metadata.get('category', 'General')
                    })
                if len(related) >= top_k:
                    break

            return related
        except Exception as e:
            logger.error(f"Error getting related questions: {e}")
            return []

    def answer_question(self, user_question: str) -> Dict[str, Any]:
        if not user_question or not user_question.strip():
            return {
                "response": "Please enter a question.",
                "related_questions": [],
                "similarity_score": 0.0,
                "source": "validation"
            }

        if not self.chroma_db:
            return {
                "response": "FAQ service is currently unavailable. Please contact support.",
                "related_questions": [],
                "similarity_score": 0.0,
                "source": "error"
            }

        try:
            user_question = user_question.strip()
            results = self.chroma_db.similarity_search_with_score(user_question, k=1)

            if results:
                retrieved_doc, _ = results[0]
                similarity_score = self.evaluate_similarity(user_question, retrieved_doc.page_content)

                if similarity_score >= self.similarity_threshold:
                    try:
                        response = self.chain.invoke({
                            "question": user_question,
                            "answer": retrieved_doc.metadata['answer'],
                            "category": retrieved_doc.metadata.get('category', 'General')
                        }).strip()
                    except Exception as e:
                        logger.error(f"Error generating LLM response: {e}")
                        response = retrieved_doc.metadata['answer']

                    related = self.get_related_questions(user_question)

                    return {
                        "response": response,
                        "related_questions": related,
                        "similarity_score": similarity_score,
                        "source": "knowledge_base",
                        "category": retrieved_doc.metadata.get('category', 'General')
                    }

            fallback = (
                "I don't have a specific answer for that question. "
                "Please check the Jupiter Help Centre or contact our support team for assistance."
            )
            return {
                "response": fallback,
                "related_questions": self.get_related_questions(user_question),
                "similarity_score": 0.0,
                "source": "fallback"
            }

        except Exception as e:
            logger.error(f"Error answering question '{user_question}': {e}")
            return {
                "response": "I'm experiencing technical difficulties. Please try again or contact support.",
                "related_questions": [],
                "similarity_score": 0.0,
                "source": "error"
            }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_faqs": len(self.faq_data),
            "similarity_threshold": self.similarity_threshold,
            "status": "ready" if self.chroma_db else "not_ready"
        }

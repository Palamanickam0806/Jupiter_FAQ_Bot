from flask import Flask, request, jsonify, render_template
from faq_logic import FAQBot
import logging
import os
from dotenv import load_dotenv
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
os.environ["CHROMA_TELEMETRY_ENABLED"] = "FALSE"
os.environ['ANONYMIZED_TELEMETRY'] = 'False'
import chromadb.config
chromadb.config.Settings.anonymized_telemetry = False
app = Flask(__name__)
faq_bot = FAQBot()
test_queries = []

@app.route('/')
def index():
    """Render the main FAQ interface"""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    if not faq_bot:
        return jsonify({
            "error": "FAQ bot not initialized. Please check server logs.",
            "response": "Service temporarily unavailable.",
            "related_questions": []
        }), 500
    
    try:
        if request.is_json:
            data = request.get_json()
            user_question = data.get('question', '').strip()
        else:
            user_question = request.form.get('question', '').strip()
        test_queries.append(user_question)
        result = faq_bot.answer_question(user_question)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in /ask endpoint: {e}")
        return jsonify({
            "error": "An error occurred processing your request.",
            "response": "Sorry, I encountered an error. Please try again.",
            "related_questions": []
        }), 500

@app.route('/api/ask', methods=['POST'])
def api_ask():
    if not faq_bot:
        return jsonify({"error": "Service unavailable"}), 503
    
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({"error": "Question is required"}), 400
        
        user_question = data['question'].strip()
        test_queries.append(user_question)
        result = faq_bot.answer_question(user_question)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error in API endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/evaluate', methods=['GET'])
def evaluate():
    if not faq_bot:
        return jsonify({"error": "FAQ bot not initialized"}), 500
    
    # test_queries = [
    #     "What are the fees for the Edge+ card?",
    #     "How do I complete KYC?",
    #     "What rewards can I get?",
    #     "Random unrelated question"
    # ]
    
    results = []
    for query in test_queries:
        try:
            result = faq_bot.answer_question(query)
            results.append({
                "query": query,
                "response": result["response"],
                "similarity_score": result["similarity_score"],
                "related_questions": result["related_questions"]
            })
        except Exception as e:
            logger.error(f"Error evaluating query '{query}': {e}")
            results.append({
                "query": query,
                "response": "Error occurred",
                "similarity_score": 0.0,
                "related_questions": []
            })
    
    return jsonify(results)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy" if faq_bot else "unhealthy",
        "faq_count": len(faq_bot.faq_data) if faq_bot else 0,
        "service": "Jupiter FAQ Bot"
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(host="0.0.0.0", port=port) # debug=True,






























# # ================================
# # File: config.py (Optional Configuration File)
# # ================================

# import os
# from typing import Dict, Any

# class Config:
#     """Configuration class for the FAQ Bot application"""
    
#     # Flask Configuration
#     SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
#     DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
#     # Google API Configuration
#     GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    
#     # FAQ Bot Configuration
#     FAQ_FILE_PATH = os.environ.get('FAQ_FILE_PATH') or 'cleaned_faq.json'
#     SIMILARITY_THRESHOLD = float(os.environ.get('SIMILARITY_THRESHOLD') or '0.7')
    
#     # Model Configuration
#     EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL') or 'sentence-transformers/all-MiniLM-L6-v2'
#     LLM_MODEL = os.environ.get('LLM_MODEL') or 'gemini-1.5-flash'
#     LLM_TEMPERATURE = float(os.environ.get('LLM_TEMPERATURE') or '0.7')
#     LLM_MAX_TOKENS = int(os.environ.get('LLM_MAX_TOKENS') or '500')
    
#     # Chroma Configuration
#     CHROMA_COLLECTION_NAME = os.environ.get('CHROMA_COLLECTION_NAME') or 'faq_collection'
    
#     # Application Configuration
#     MAX_RELATED_QUESTIONS = int(os.environ.get('MAX_RELATED_QUESTIONS') or '3')
    
#     @classmethod
#     def validate_config(cls) -> Dict[str, Any]:
#         """Validate configuration and return status"""
#         issues = []
        
#         if not cls.GOOGLE_API_KEY:
#             issues.append("GOOGLE_API_KEY environment variable not set")
        
#         if not os.path.exists(cls.FAQ_FILE_PATH):
#             issues.append(f"FAQ file not found: {cls.FAQ_FILE_PATH}")
        
#         if cls.SIMILARITY_THRESHOLD < 0 or cls.SIMILARITY_THRESHOLD > 1:
#             issues.append("SIMILARITY_THRESHOLD must be between 0 and 1")
        
#         return {
#             "valid": len(issues) == 0,
#             "issues": issues,
#             "config": {
#                 "faq_file": cls.FAQ_FILE_PATH,
#                 "similarity_threshold": cls.SIMILARITY_THRESHOLD,
#                 "embedding_model": cls.EMBEDDING_MODEL,
#                 "llm_model": cls.LLM_MODEL,
#                 "debug": cls.DEBUG
#             }
#         }


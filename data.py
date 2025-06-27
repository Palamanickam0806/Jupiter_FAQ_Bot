import pandas as pd
import re
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
import json

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('wordnet')

# Initialize lemmatizer and stopwords
lemmatizer = WordNetLemmatizer()
stop_words = set(stopwords.words('english'))

# Define topic keywords for categorization
TOPIC_KEYWORDS = {
    'KYC': ['kyc', 'know your customer', 'verification', 'identity', 'document', 'address proof'],
    'Rewards': ['reward', 'cashback', 'points', 'benefit', 'offer', 'discount'],
    'Payments': ['payment', 'transaction', 'pay', 'upi', 'transfer', 'bill'],
    'Limits': ['limit', 'maximum', 'minimum', 'cap', 'threshold', 'restriction'],
    'Card': ['card', 'credit card', 'debit card', 'edge+', 'rupay', 'visa', 'mastercard'],
    'Fees': ['fee', 'charge', 'cost', 'pricing', 'annual fee', 'joining fee'],
    'Account': ['account', 'balance', 'deposit', 'withdrawal', 'savings', 'current'],
    'Security': ['security', 'fraud', 'protection', 'safe', 'authentication', 'otp'],
    'General': ['general', 'other', 'miscellaneous', 'support', 'help', 'faq']
}

def clean_text(text):
    """Clean HTML and formatting noise from text."""
    # Remove HTML tags
    text = BeautifulSoup(text, 'html.parser').get_text()
    # Remove extra whitespace and newlines
    text = re.sub(r'\s+', ' ', text).strip()
    # Remove special characters but keep alphanumeric and basic punctuation
    text = re.sub(r'[^\w\s.,!?]', '', text)
    return text

def normalize_text(text):
    """Normalize text by lowercasing, removing stopwords, and lemmatizing."""
    tokens = word_tokenize(text.lower())
    tokens = [lemmatizer.lemmatize(token) for token in tokens if token not in stop_words]
    return ' '.join(tokens)

def categorize_question(question):
    """Categorize a question based on predefined topic keywords."""
    normalized_question = normalize_text(question)
    max_score = 0
    assigned_category = 'General'
    
    for category, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            score = fuzz.partial_ratio(keyword, normalized_question)
            if score > max_score and score > 80:  # Threshold for keyword matching
                max_score = score
                assigned_category = category
    
    return assigned_category

def deduplicate_questions(data, threshold=90):
    """Deduplicate similar questions based on fuzzy matching."""
    df = pd.DataFrame(data)
    unique_data = []
    seen_questions = set()
    
    for i, row in df.iterrows():
        question = row['question']
        normalized_q = normalize_text(question)
        is_duplicate = False
        
        for seen_q in seen_questions:
            if fuzz.ratio(normalized_q, seen_q) > threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            seen_questions.add(normalized_q)
            unique_data.append(row.to_dict())
    
    return unique_data

def preprocess_data(input_file, output_file):
    """Main function to preprocess and clean FAQ data."""
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    for item in data:
        item.pop('extracted_at', None)
        item.pop('extraction_method', None)
        
    # Clean and normalize data
    for item in data:
        item['question'] = clean_text(item['question'])
        item['answer'] = clean_text(item['answer'])
        item['normalized_question'] = normalize_text(item['question'])
        item['category'] = categorize_question(item['question'])
    
    # Deduplicate questions
    cleaned_data = deduplicate_questions(data)
    
    # Save processed data
    with open(output_file, 'w') as f:
        json.dump(cleaned_data, f, indent=2)
    
    return cleaned_data

# Example usage
if __name__ == "__main__":
    input_file = 'faqs_2.json'  # Input JSON file with scraped data
    output_file = 'cleaned_faq.json'  # Output JSON file for cleaned data
    processed_data = preprocess_data(input_file, output_file)
    print(f"Processed {len(processed_data)} unique FAQs and saved to {output_file}")


# import json

# def clean_json_fields(input_file, output_file):
#     # Load JSON data
#     with open(input_file, 'r') as f:
#         data = json.load(f)
    
#     # Remove specified fields
#     for item in data:
#         item.pop('extracted_at', None)
#         item.pop('extraction_method', None)
    
#     # Save cleaned data
#     with open(output_file, 'w') as f:
#         json.dump(data, f, indent=2)

# # Example usage
# if __name__ == "__main__":
#     input_file = 'processed_faq.json'  # Input JSON file
#     output_file = 'cleaned_faq.json'   # Output JSON file
#     clean_json_fields(input_file, output_file)
#     print(f"Cleaned JSON saved to {output_file}")
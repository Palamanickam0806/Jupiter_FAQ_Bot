import requests
from bs4 import BeautifulSoup
import json
import time
import os
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser
from typing import List, Dict, Set
import logging
from collections import deque
import re

class FAQCrawler:
    def __init__(self, base_url: str, output_file: str = "faqs_2.json", max_pages: int = 50):
        """
        Initialize the FAQ crawler
        
        Args:
            base_url: The base URL of the website to crawl
            output_file: JSON file to save FAQs
            max_pages: Maximum number of pages to crawl
        """
        self.base_url = base_url.rstrip('/')
        self.domain = urlparse(base_url).netloc
        self.output_file = output_file
        self.max_pages = max_pages
        self.visited_urls: Set[str] = set()
        self.faqs: List[Dict] = []
        self.session = requests.Session()
        
        # Set up headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Set up logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Load existing FAQs if file exists
        self.load_existing_faqs()
        
        # URL patterns to avoid
        self.skip_patterns = [
            r'\.pdf$', r'\.jpg$', r'\.jpeg$', r'\.png$', r'\.gif$', r'\.css$', r'\.js$',
            r'\.zip$', r'\.exe$', r'\.doc$', r'\.docx$', r'\.xml$', r'\.rss$',
            r'/wp-admin/', r'/admin/', r'/login', r'/register', r'/logout',
            r'#', r'javascript:', r'mailto:', r'tel:', r'ftp:'
        ]
    
    def load_existing_faqs(self):
        """Load existing FAQs from JSON file if it exists"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    self.faqs = json.load(f)
                self.logger.info(f"Loaded {len(self.faqs)} existing FAQs from {self.output_file}")
            except Exception as e:
                self.logger.error(f"Error loading existing FAQs: {e}")
                self.faqs = []
    
    def save_faqs(self):
        """Save FAQs to JSON file in real-time"""
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(self.faqs, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved {len(self.faqs)} FAQs to {self.output_file}")
        except Exception as e:
            self.logger.error(f"Error saving FAQs: {e}")
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        try:
            parsed = urlparse(url)
            
            # Must be same domain
            if parsed.netloc != self.domain:
                return False
            
            # Check skip patterns
            for pattern in self.skip_patterns:
                if re.search(pattern, url, re.IGNORECASE):
                    return False
            
            # Must be HTTP/HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
                
            return True
        except:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL to avoid duplicates"""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/') if parsed.path != '/' else '/',
            parsed.params,
            parsed.query,
            ''  # Remove fragment
        ))
        return normalized
    
    def get_page_content(self, url: str) -> BeautifulSoup:
        """
        Fetch and parse page content
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            self.logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                self.logger.warning(f"Skipping non-HTML content: {url}")
                return None
                
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_faqs_from_page(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """
        Extract FAQ question-answer pairs from a page using multiple strategies
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
            
        Returns:
            List of FAQ dictionaries
        """
        faqs = []
        
        # Strategy 1: Look for the exact format from your example
        faq_items = soup.find_all('div', class_='faq-item')
        
        if faq_items:
            self.logger.info(f"Found {len(faq_items)} FAQ items using Strategy 1")
            for item in faq_items:
                faq = self.extract_faq_from_item_strategy1(item, url)
                if faq:
                    faqs.append(faq)
        
        # Strategy 2: Look for FAQ containers with toggle functionality
        if not faqs:
            faq_containers = soup.find_all('div', attrs={'data-controller': 'faq-toggle'})
            for container in faq_containers:
                items = container.find_all('div', class_='faq-item')
                self.logger.info(f"Found {len(items)} FAQ items using Strategy 2")
                for item in items:
                    faq = self.extract_faq_from_item_strategy1(item, url)
                    if faq:
                        faqs.append(faq)
        
        # Strategy 3: Look for accordion-style FAQs
        if not faqs:
            accordion_items = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['accordion', 'collapse', 'toggle', 'expandable']
            ))
            
            if accordion_items:
                self.logger.info(f"Found {len(accordion_items)} accordion items using Strategy 3")
                for item in accordion_items:
                    faq = self.extract_faq_generic(item, url)
                    if faq:
                        faqs.append(faq)
        
        # Strategy 4: Look for question-answer patterns in text
        if not faqs:
            faqs.extend(self.extract_faqs_by_text_pattern(soup, url))
        
        # Strategy 5: Look for FAQ sections by headings
        if not faqs:
            faqs.extend(self.extract_faqs_by_headings(soup, url))
        
        return faqs
    
    def extract_faq_from_item_strategy1(self, item: BeautifulSoup, url: str) -> Dict:
        """Extract FAQ using the format from your example"""
        try:
            # Look for question in faq-header
            question_elem = item.find('div', class_='faq-header')
            if question_elem:
                question_span = question_elem.find('span')
                if question_span:
                    question = question_span.get_text(strip=True)
                else:
                    question = question_elem.get_text(strip=True)
            else:
                # Fallback: look for any clickable element
                question_elem = item.find(['span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5'], 
                                        attrs={'data-action': lambda x: x and 'toggle' in str(x)})
                if question_elem:
                    question = question_elem.get_text(strip=True)
                else:
                    return None
            
            # Look for answer in faq-answer
            answer_elem = item.find('div', class_='faq-answer') or \
                         item.find('div', attrs={'data-faq-toggle-target': 'answer'})
            
            if answer_elem:
                answer_p = answer_elem.find('p')
                if answer_p:
                    answer = answer_p.get_text(strip=True)
                else:
                    answer = answer_elem.get_text(strip=True)
            else:
                return None
            
            if question and answer and len(question) > 5 and len(answer) > 10:
                return {
                    'question': question,
                    'answer': answer,
                    'source_url': url,
                }
                
        except Exception as e:
            self.logger.error(f"Error in strategy1 extraction: {e}")
        
        return None
    
    def extract_faq_generic(self, item: BeautifulSoup, url: str) -> Dict:
        """Generic FAQ extraction for various formats"""
        try:
            # Look for question - usually the first prominent text
            question_selectors = [
                'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                '.question', '.title', '.header',
                '[data-toggle]', '.accordion-header',
                'summary', '.faq-question'
            ]
            
            question = None
            for selector in question_selectors:
                elem = item.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if len(text) > 5 and '?' in text:
                        question = text
                        break
            
            # Look for answer - usually in a separate div or paragraph
            answer_selectors = [
                '.answer', '.content', '.body', '.description',
                '.accordion-body', '.collapse', '.faq-answer',
                'p', '.text'
            ]
            
            answer = None
            for selector in answer_selectors:
                elem = item.select_one(selector)
                if elem:
                    text = elem.get_text(strip=True)
                    if len(text) > 10 and text != question:
                        answer = text
                        break
            
            if question and answer:
                return {
                    'question': question,
                    'answer': answer,
                    'source_url': url,
                    'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'extraction_method': 'generic'
                }
                
        except Exception as e:
            self.logger.error(f"Error in generic extraction: {e}")
        
        return None
    
    def extract_faqs_by_text_pattern(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract FAQs by looking for Q&A text patterns"""
        faqs = []
        
        try:
            # Look for text that starts with Q: or Question:
            text_elements = soup.find_all(['p', 'div', 'li'])
            
            i = 0
            while i < len(text_elements) - 1:
                elem = text_elements[i]
                text = elem.get_text(strip=True)
                
                # Check if this looks like a question
                if (text.lower().startswith(('q:', 'question:', 'q.')) or 
                    text.endswith('?') and len(text) > 10):
                    
                    # Look for answer in next element(s)
                    for j in range(i + 1, min(i + 3, len(text_elements))):
                        next_elem = text_elements[j]
                        next_text = next_elem.get_text(strip=True)
                        
                        if (next_text.lower().startswith(('a:', 'answer:', 'a.')) or 
                            (len(next_text) > 20 and not next_text.endswith('?'))):
                            
                            question = text.replace('Q:', '').replace('Question:', '').replace('Q.', '').strip()
                            answer = next_text.replace('A:', '').replace('Answer:', '').replace('A.', '').strip()
                            
                            if len(question) > 5 and len(answer) > 10:
                                faqs.append({
                                    'question': question,
                                    'answer': answer,
                                    'source_url': url,
                                    'extracted_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                                    'extraction_method': 'text_pattern'
                                })
                            break
                
                i += 1
                
        except Exception as e:
            self.logger.error(f"Error in text pattern extraction: {e}")
        
        return faqs
    
    def extract_faqs_by_headings(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract FAQs by looking for question headings followed by content"""
        faqs = []
        
        try:
            headings = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            
            for heading in headings:
                question = heading.get_text(strip=True)
                
                # Check if heading looks like a question
                if '?' in question and len(question) > 10:
                    # Look for answer in next siblings
                    answer_elem = heading.find_next_sibling(['p', 'div', 'ul', 'ol'])
                    
                    if answer_elem:
                        answer = answer_elem.get_text(strip=True)
                        
                        if len(answer) > 20:
                            faqs.append({
                                'question': question,
                                'answer': answer,
                                'source_url': url
                            })
                            
        except Exception as e:
            self.logger.error(f"Error in headings extraction: {e}")
        
        return faqs
    
    def get_all_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract all valid internal links from a page"""
        links = []
        
        try:
            for link in soup.find_all('a', href=True):
                href = link['href'].strip()
                if not href:
                    continue
                
                # Convert relative URLs to absolute
                full_url = urljoin(current_url, href)
                full_url = self.normalize_url(full_url)
                
                if self.is_valid_url(full_url) and full_url not in self.visited_urls:
                    links.append(full_url)
                    
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
        
        return links
    
    def crawl_all_pages(self):
        """
        Crawl all pages on the website and extract FAQs
        """
        self.logger.info(f"Starting comprehensive crawl of: {self.base_url}")
        
        # Use BFS to crawl all pages
        to_visit = deque([self.base_url])
        pages_crawled = 0
        total_new_faqs = 0
        
        while to_visit and pages_crawled < self.max_pages:
            current_url = to_visit.popleft()
            
            if current_url in self.visited_urls:
                continue
            
            self.visited_urls.add(current_url)
            pages_crawled += 1
            
            self.logger.info(f"Crawling page {pages_crawled}/{self.max_pages}: {current_url}")
            
            # Get page content
            soup = self.get_page_content(current_url)
            if not soup:
                continue
            
            # Extract FAQs from this page
            page_faqs = self.extract_faqs_from_page(soup, current_url)
            
            if page_faqs:
                self.logger.info(f"Found {len(page_faqs)} FAQs on {current_url}")
                
                # Add new FAQs (avoid duplicates)
                for faq in page_faqs:
                    if not any(existing['question'].lower().strip() == faq['question'].lower().strip() 
                             for existing in self.faqs):
                        self.faqs.append(faq)
                        total_new_faqs += 1
                        self.logger.info(f"New FAQ: {faq['question'][:60]}...")
                
                # Save FAQs in real-time
                self.save_faqs()
            
            # Get all links from this page for further crawling
            new_links = self.get_all_links(soup, current_url)
            
            # Add new links to the queue
            for link in new_links:
                if link not in self.visited_urls:
                    to_visit.append(link)
            
            self.logger.info(f"Found {len(new_links)} new links. Queue size: {len(to_visit)}")
            
            # Be respectful - add delay between requests
            time.sleep(1)
        
        self.logger.info(f"Crawling completed!")
        self.logger.info(f"Pages crawled: {pages_crawled}")
        self.logger.info(f"Total FAQs: {len(self.faqs)}")
        self.logger.info(f"New FAQs found: {total_new_faqs}")
        
        # Final save
        self.save_faqs()

def main():
    # Configuration
    BASE_URL = "https://jupiter.money"  # Replace with your target website
    OUTPUT_FILE = "faqs_2.json"
    MAX_PAGES = 150  # Adjust as needed
    
    print("=== FAQ Website Crawler ===")
    print(f"Target: {BASE_URL}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Max pages: {MAX_PAGES}")
    print()
    
    # Initialize and run crawler
    crawler = FAQCrawler(BASE_URL, OUTPUT_FILE, MAX_PAGES)
    crawler.crawl_all_pages()
    
    print(f"\nCrawling completed! Check '{OUTPUT_FILE}' for results.")
    print(f"Total FAQs extracted: {len(crawler.faqs)}")

if __name__ == "__main__":
    main()
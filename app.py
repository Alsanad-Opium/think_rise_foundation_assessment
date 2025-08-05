# app.py
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import sqlite3
from scraper import NagpurCourtScraper
import logging
import time
import threading

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session management for single browser instance
browser_session = {
    'scraper': None,
    'last_used': 0,
    'lock': threading.Lock()
}

# Session timeout in seconds (5 minutes)
SESSION_TIMEOUT = 300

def get_or_create_browser_session():
    """Get existing browser session or create new one if expired"""
    current_time = time.time()
    
    with browser_session['lock']:
        # Check if session exists and is not expired
        if (browser_session['scraper'] is not None and 
            current_time - browser_session['last_used'] < SESSION_TIMEOUT):
            browser_session['last_used'] = current_time
            logger.info("Using existing browser session")
            return browser_session['scraper']
        
        # Close existing session if it exists
        if browser_session['scraper'] is not None:
            try:
                browser_session['scraper'].close()
                logger.info("Closed expired browser session")
            except Exception as e:
                logger.warning(f"Error closing browser session: {e}")
        
        # Create new session
        try:
            browser_session['scraper'] = NagpurCourtScraper(headless=False)
            browser_session['last_used'] = current_time
            logger.info("Created new browser session")
            return browser_session['scraper']
        except Exception as e:
            logger.error(f"Failed to create browser session: {e}")
            browser_session['scraper'] = None
            raise

# Setup SQLite
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_type TEXT,
                    case_number TEXT,
                    filing_year TEXT,
                    response TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_captcha')
def get_captcha():
    """Fetch the latest captcha image from the court website and save it to static/captcha.png"""
    try:
        scraper = get_or_create_browser_session()
        
        # Navigate to the website if not already there
        if scraper.driver.current_url != scraper.base_url:
            scraper.driver.get(scraper.base_url)
            # Wait for page to load
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            WebDriverWait(scraper.driver, 10).until(
                EC.presence_of_element_located((By.ID, "est_code"))
            )
        
        # Get and save captcha image
        captcha_path = scraper.get_captcha_image("static/captcha.png")
        if captcha_path:
            return send_from_directory('static', 'captcha.png')
        else:
            return "", 500
    except Exception as e:
        logger.error(f"Error fetching captcha: {e}")
        return "", 500

@app.route('/fetch', methods=['POST'])
def fetch():
    case_type = request.form['case_type']
    case_number = request.form['case_number']
    filing_year = request.form['filing_year']
    captcha_text = request.form.get('captcha_text')

    try:
        # Get the existing browser session
        scraper = get_or_create_browser_session()
        
        # Navigate to the website if not already there
        if scraper.driver.current_url != scraper.base_url:
            scraper.driver.get(scraper.base_url)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            WebDriverWait(scraper.driver, 10).until(
                EC.presence_of_element_located((By.ID, "est_code"))
            )
        
        # Fill form fields
        scraper.fill_form_fields(case_type, case_number, filing_year)
        
        # Fill captcha manually
        if not scraper.fill_captcha_manual(captcha_text):
            raise Exception("Failed to fill captcha")
        
        # Submit form
        if not scraper.submit_form():
            raise Exception("Failed to submit form")
        
        # Extract results
        data = scraper.extract_results()

        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO queries (case_type, case_number, filing_year, response) VALUES (?, ?, ?, ?)",
                  (case_type, case_number, filing_year, str(data)))
        conn.commit()
        conn.close()

        return render_template("result.html", data=data)

    except Exception as e:
        logger.error(f"Error in fetch: {e}")
        return f"<h3>Error: {str(e)}</h3><p>Try again later or check your inputs.</p>"

@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint for scraping"""
    try:
        data = request.get_json()
        case_type = data.get('case_type')
        case_number = data.get('case_number')
        filing_year = data.get('filing_year')
        
        if not all([case_type, case_number, filing_year]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get the existing browser session
        scraper = get_or_create_browser_session()
        
        # Navigate to the website if not already there
        if scraper.driver.current_url != scraper.base_url:
            scraper.driver.get(scraper.base_url)
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            WebDriverWait(scraper.driver, 10).until(
                EC.presence_of_element_located((By.ID, "est_code"))
            )
        
        # Use the existing scrape_case_data method
        result = scraper.scrape_case_data(case_type, case_number, filing_year)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"API Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/history')
def history():
    """Show search history"""
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM queries ORDER BY timestamp DESC LIMIT 20")
        queries = c.fetchall()
        conn.close()
        
        return render_template("history.html", queries=queries)
        
    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        return f"<h3>Error: {str(e)}</h3>"

@app.route('/test')
def test_scraper():
    """Test endpoint for scraper"""
    try:
        scraper = get_or_create_browser_session()
        result = scraper.scrape_case_data("Criminal", "123", "2023")
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def status():
    """Check browser session status"""
    try:
        current_time = time.time()
        session_age = current_time - browser_session['last_used']
        session_active = browser_session['scraper'] is not None and session_age < SESSION_TIMEOUT
        
        return jsonify({
            'session_active': session_active,
            'session_age_seconds': session_age,
            'session_timeout_seconds': SESSION_TIMEOUT,
            'browser_exists': browser_session['scraper'] is not None
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def cleanup_browser_session():
    """Cleanup function to close browser session on shutdown"""
    with browser_session['lock']:
        if browser_session['scraper'] is not None:
            try:
                browser_session['scraper'].close()
                logger.info("Browser session closed during cleanup")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")

if __name__ == '__main__':
    init_db()
    try:
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        cleanup_browser_session()

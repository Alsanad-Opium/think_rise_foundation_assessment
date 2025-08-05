 # app.py
from flask import Flask, render_template, request, jsonify, session, send_from_directory
import sqlite3
from scraper import NagpurCourtScraper
import logging
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scraper instance (for session management)
scrapers = {}

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
        scraper = NagpurCourtScraper()
        scraper.driver.get(scraper.base_url)
        # Wait for page to load
        WebDriverWait(scraper.driver, 10).until(
            EC.presence_of_element_located((By.ID, "est_code"))
        )
        # Get and save captcha image
        captcha_path = scraper.get_captcha_image("static/captcha.png")
        scraper.close()
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
        # Create a new scraper instance for this request
        scraper = NagpurCourtScraper()
        # Navigate to the website and fill form fields
        scraper.driver.get(scraper.base_url)
        WebDriverWait(scraper.driver, 10).until(
            EC.presence_of_element_located((By.ID, "est_code"))
        )
        scraper.fill_form_fields(case_type, case_number, filing_year)
        
        # Fill captcha manually
        if not scraper.fill_captcha_manual(captcha_text):
            raise Exception("Failed to fill captcha")
        
        # Submit form
        if not scraper.submit_form():
            raise Exception("Failed to submit form")
        
        # Extract results
        data = scraper.extract_results()
        scraper.close()

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
        
        # Create scraper and scrape
        scraper = NagpurCourtScraper()
        result = scraper.scrape_case_data(case_type, case_number, filing_year)
        scraper.close()
        
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
        scraper = NagpurCourtScraper()
        result = scraper.scrape_case_data("Criminal", "123", "2023")
        scraper.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)

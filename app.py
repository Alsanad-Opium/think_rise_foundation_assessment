# app.py
from flask import Flask, render_template, request, jsonify, session
import sqlite3
from scraper import NagpurCourtScraper
import logging

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

@app.route('/fetch', methods=['POST'])
def fetch():
    case_type = request.form['case_type']
    case_number = request.form['case_number']
    filing_year = request.form['filing_year']

    try:
        # Create a new scraper instance for this request
        scraper = NagpurCourtScraper()
        
        # Scrape data from court
        data = scraper.scrape_case_data(case_type, case_number, filing_year)
        
        # Close the scraper
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

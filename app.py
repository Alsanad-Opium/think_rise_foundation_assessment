# app.py
from flask import Flask, render_template, request
import sqlite3
from scraper import scrape_case_data

app = Flask(__name__)

# Setup SQLite
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    case_type TEXT,
                    case_number TEXT,
                    filing_year TEXT,
                    response TEXT
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
        # Scrape data from court
        data = scrape_case_data(case_type, case_number, filing_year)

        # Save to DB
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO queries (case_type, case_number, filing_year, response) VALUES (?, ?, ?, ?)",
                  (case_type, case_number, filing_year, str(data)))
        conn.commit()
        conn.close()

        return render_template("result.html", data=data)

    except Exception as e:
        return f"<h3>Error: {str(e)}</h3><p>Try again later or check your inputs.</p>"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)

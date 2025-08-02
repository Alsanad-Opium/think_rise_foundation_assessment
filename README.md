# Nagpur District Court Web Scraper

A comprehensive web scraping application for the Nagpur District Court website with automatic captcha handling and case data extraction.

## Features

- **Automatic Captcha Solving**: Uses OCR (Optical Character Recognition) to solve captcha challenges
- **Smart Form Detection**: Automatically identifies and fills form fields based on common naming patterns
- **Web Interface**: User-friendly Flask web application for easy interaction
- **Search History**: Tracks and displays previous search queries
- **API Endpoints**: RESTful API for programmatic access
- **Error Handling**: Comprehensive error handling and logging
- **Database Storage**: SQLite database for storing search history and results

## Technology Stack

- **Backend**: Python Flask
- **Web Scraping**: Selenium WebDriver with Chrome
- **Captcha Solving**: Tesseract OCR with OpenCV preprocessing
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript
- **Image Processing**: Pillow, OpenCV
- **Browser Automation**: Selenium WebDriver Manager

## Installation

### Prerequisites

1. **Python 3.7+**
2. **Chrome Browser** (for Selenium WebDriver)
3. **Tesseract OCR** (for captcha solving)

### Install Tesseract OCR

#### Windows:
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Install and add to PATH
3. Set environment variable: `TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR\tessdata`

#### Linux (Ubuntu/Debian):
```bash
sudo apt-get install tesseract-ocr
```

#### macOS:
```bash
brew install tesseract
```

### Install Python Dependencies

1. **Clone the repository:**
```bash
git clone <repository-url>
cd think_rise_foundation_assessment
```

2. **Create virtual environment:**
```bash
python -m venv .env
source .env/bin/activate  # On Windows: .env\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Usage

### Running the Web Application

1. **Start the Flask server:**
```bash
python app.py
```

2. **Open your browser and navigate to:**
```
http://localhost:5000
```

3. **Enter case details:**
   - Case Type (e.g., Criminal, Civil)
   - Case Number (e.g., 123, 456)
   - Filing Year (e.g., 2023, 2024)

4. **Click "Search Case"** - The system will automatically:
   - Navigate to the Nagpur District Court website
   - Fill in the form fields
   - Solve any captcha challenges
   - Extract case information
   - Display results

### API Usage

#### Search for Case Data
```bash
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "case_type": "Criminal",
    "case_number": "123",
    "filing_year": "2023"
  }'
```

#### Test Scraper
```bash
curl http://localhost:5000/test
```

### Direct Python Usage

```python
from scraper import NagpurCourtScraper

# Create scraper instance
scraper = NagpurCourtScraper()

try:
    # Search for case data
    result = scraper.scrape_case_data("Criminal", "123", "2023")
    print(result)
finally:
    # Always close the scraper
    scraper.close()
```

## Project Structure

```
think_rise_foundation_assessment/
├── app.py                 # Main Flask application
├── scraper.py            # Web scraping logic with captcha handling
├── database.db           # SQLite database
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
├── LICENSE              # License file
└── templates/           # HTML templates
    ├── index.html       # Main search form
    ├── result.html      # Results display
    └── history.html     # Search history
```

## Key Components

### NagpurCourtScraper Class

The main scraper class with the following methods:

- `setup_driver()`: Initialize Chrome WebDriver
- `solve_captcha()`: OCR-based captcha solving
- `find_form_fields()`: Detect form fields on the page
- `fill_form_fields()`: Fill form with case data
- `handle_captcha()`: Process captcha challenges
- `submit_form()`: Submit the search form
- `extract_results()`: Parse and extract case information

### Captcha Solving

The system uses a multi-step approach for captcha solving:

1. **Image Capture**: Extract captcha image from the webpage
2. **Preprocessing**: Apply OpenCV filters for better OCR accuracy
3. **OCR Processing**: Use Tesseract to extract text
4. **Text Cleaning**: Remove noise and format the result

### Form Field Detection

The scraper intelligently identifies form fields using:

- Common naming patterns (case_type, case_number, etc.)
- Field types and attributes
- Context-based field mapping

## Configuration

### Environment Variables

- `TESSDATA_PREFIX`: Path to Tesseract data files
- `CHROME_DRIVER_PATH`: Custom Chrome driver path (optional)

### Browser Options

The scraper can be configured to run in headless mode by uncommenting:
```python
chrome_options.add_argument("--headless")
```

## Error Handling

The application includes comprehensive error handling for:

- Network connectivity issues
- Website structure changes
- Captcha solving failures
- Form submission errors
- Database connection issues

## Logging

The application uses Python's logging module with INFO level by default. Logs include:

- Scraping progress
- Captcha solving attempts
- Form field detection
- Error messages
- Performance metrics

## Database Schema

```sql
CREATE TABLE queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_type TEXT,
    case_number TEXT,
    filing_year TEXT,
    response TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues:**
   - Ensure Chrome browser is installed
   - Update Chrome to latest version
   - Check webdriver-manager installation

2. **Tesseract OCR Issues:**
   - Verify Tesseract installation
   - Check PATH environment variable
   - Ensure language data files are available

3. **Captcha Solving Failures:**
   - Check image quality and preprocessing
   - Verify OCR configuration
   - Consider manual intervention for complex captchas

4. **Website Access Issues:**
   - Check internet connectivity
   - Verify website availability
   - Handle rate limiting if applicable

### Debug Mode

Enable debug logging by modifying the logging level:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for educational and research purposes only. Please ensure compliance with the target website's terms of service and robots.txt file. The developers are not responsible for any misuse of this software.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for error messages
3. Create an issue on the repository
4. Contact the development team
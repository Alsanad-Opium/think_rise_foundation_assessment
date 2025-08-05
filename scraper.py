# scraper.py
import requests
from bs4 import BeautifulSoup
import time
import re
import base64
import io
from PIL import Image
import cv2
import numpy as np
import pytesseract
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set Tesseract path for Windows
if os.name == 'nt':  # Windows
    tesseract_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(tesseract_path):
        pytesseract.pytesseract.tesseract_cmd = tesseract_path

class NagpurCourtScraper:
    def __init__(self, enable_manual_captcha=False, headless=False):
        self.base_url = "https://nagpur.dcourts.gov.in/court-orders-search-by-case-number/"
        self.driver = None
        self.enable_manual_captcha = enable_manual_captcha
        self.headless = headless
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # Run in headless mode based on parameter
        if self.headless:
            chrome_options.add_argument("--headless")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver setup successful (headless: {})".format(self.headless))
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def solve_captcha(self, captcha_element):
        """Solve captcha using OCR with improved preprocessing"""
        try:
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
                logger.info("Tesseract is available")
            except Exception as e:
                logger.warning(f"Tesseract not available: {e}")
                # Return a dummy captcha for testing (you should install Tesseract for production)
                return "TEST123"
            
            # Get captcha image
            captcha_src = captcha_element.get_attribute('src')
            
            if captcha_src.startswith('data:image'):
                # Handle base64 encoded image
                image_data = captcha_src.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            else:
                # Handle URL image
                response = requests.get(captcha_src)
                image = Image.open(io.BytesIO(response.content))
            
            # Convert to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Try multiple preprocessing techniques
            captcha_text = None
            
            # Method 1: Basic preprocessing
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # OCR configuration for captcha
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            
            # Extract text
            captcha_text = pytesseract.image_to_string(opening, config=custom_config)
            captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
            
            # If first attempt failed or is too short, try alternative preprocessing
            if not captcha_text or len(captcha_text) < 3:
                logger.info("First OCR attempt failed, trying alternative preprocessing...")
                
                # Method 2: Adaptive threshold
                adaptive_thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
                captcha_text = pytesseract.image_to_string(adaptive_thresh, config=custom_config)
                captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
                
                # Method 3: Different PSM mode if still no result
                if not captcha_text or len(captcha_text) < 3:
                    logger.info("Trying different PSM mode...")
                    custom_config_alt = r'--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
                    captcha_text = pytesseract.image_to_string(opening, config=custom_config_alt)
                    captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
                
                # Method 4: Invert colors if still no result
                if not captcha_text or len(captcha_text) < 3:
                    logger.info("Trying inverted colors...")
                    inverted = cv2.bitwise_not(opening)
                    captcha_text = pytesseract.image_to_string(inverted, config=custom_config)
                    captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
                
                # Method 5: Gaussian blur to reduce noise
                if not captcha_text or len(captcha_text) < 3:
                    logger.info("Trying Gaussian blur...")
                    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
                    _, blurred_thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                    captcha_text = pytesseract.image_to_string(blurred_thresh, config=custom_config)
                    captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
            
            # If all methods fail, return a dummy value for testing
            if not captcha_text or len(captcha_text) < 3:
                logger.warning("All OCR attempts failed, using dummy captcha")
                return "TEST123"
            
            logger.info(f"Captcha solved: {captcha_text}")
            return captcha_text
            
        except Exception as e:
            logger.error(f"Failed to solve captcha: {e}")
            # Return a dummy captcha for testing
            return "TEST123"
    
    def find_form_fields(self):
        """Find all form fields on the page"""
        try:
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "form"))
            )
            
            # Find all input fields
            inputs = self.driver.find_elements(By.TAG_NAME, "input")
            selects = self.driver.find_elements(By.TAG_NAME, "select")
            textareas = self.driver.find_elements(By.TAG_NAME, "textarea")
            
            form_fields = {
                'inputs': inputs,
                'selects': selects,
                'textareas': textareas
            }
            
            logger.info(f"Found {len(inputs)} inputs, {len(selects)} selects, {len(textareas)} textareas")
            return form_fields
            
        except Exception as e:
            logger.error(f"Failed to find form fields: {e}")
            return None
    
    def fill_form_fields(self, case_type, case_number, filing_year):
        """Fill form fields with provided data"""
        try:
            form_fields = self.find_form_fields()
            if not form_fields:
                return False
            
            # Wait for page to be fully loaded
            time.sleep(3)
            
            # First, select a court complex (required field)
            court_complex_select = self.driver.find_element(By.ID, "est_code")
            if court_complex_select:
                # Wait for the element to be clickable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "est_code"))
                )
                
                # Select the first available option (Nagpur, District Sessions Court III)
                select = Select(court_complex_select)
                # Try to select a specific court, fallback to first option
                try:
                    select.select_by_value("MHNG01,MHNG02,MHNG05,MHNG04,MHNG06")  # Nagpur, District Sessions Court III
                except:
                    # If that fails, select the first available option
                    options = select.options
                    if len(options) > 1:  # Skip the "Select Court Complex" option
                        select.select_by_index(1)
                logger.info("Selected court complex")
                
                # Wait for case type dropdown to be populated (it's dynamic)
                time.sleep(5)
            
            # Now fill the case type (it should be enabled now)
            case_type_select = self.driver.find_element(By.ID, "case_type")
            if case_type_select and not case_type_select.get_attribute("disabled"):
                try:
                    # Wait for the element to be clickable
                    WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "case_type"))
                    )
                    
                    select = Select(case_type_select)
                    # Try to select by visible text first
                    try:
                        select.select_by_visible_text(case_type)
                    except:
                        # If that fails, try to select by partial text match
                        options = select.options
                        for option in options:
                            if case_type.lower() in option.text.lower():
                                select.select_by_visible_text(option.text)
                                break
                        else:
                            # If still no match, try to select the first available option
                            if len(options) > 1:
                                select.select_by_index(1)
                                logger.info("Selected first available case type option")
                    logger.info(f"Selected case type: {case_type}")
                except Exception as e:
                    logger.warning(f"Could not select case type: {e}")
            
            # Fill case number
            case_number_input = self.driver.find_element(By.ID, "reg_no")
            if case_number_input:
                # Wait for the element to be clickable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "reg_no"))
                )
                case_number_input.clear()
                case_number_input.send_keys(case_number)
                logger.info(f"Filled case number: {case_number}")
            
            # Fill year
            year_input = self.driver.find_element(By.ID, "reg_year")
            if year_input:
                # Wait for the element to be clickable
                WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "reg_year"))
                )
                year_input.clear()
                year_input.send_keys(filing_year)
                logger.info(f"Filled year: {filing_year}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fill form fields: {e}")
            return False
    
    def save_captcha_image(self, captcha_element, filename="captcha.png"):
        """Save captcha image for manual review"""
        try:
            captcha_src = captcha_element.get_attribute('src')
            
            if captcha_src.startswith('data:image'):
                # Handle base64 encoded image
                image_data = captcha_src.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
            else:
                # Handle URL image
                response = requests.get(captcha_src)
                image = Image.open(io.BytesIO(response.content))
            
            image.save(filename)
            logger.info(f"Captcha image saved as {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save captcha image: {e}")
            return None

    def get_captcha_image(self, save_path="static/captcha.png"):
        """Get the current captcha image and save it to the specified path"""
        try:
            # Wait for captcha image to be present
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "siwp_captcha_image_0"))
            )
            
            captcha_img = self.driver.find_element(By.ID, "siwp_captcha_image_0")
            return self.save_captcha_image(captcha_img, save_path)
        except Exception as e:
            logger.error(f"Failed to get captcha image: {e}")
            return None

    def fill_captcha_manual(self, captcha_text):
        """Fill captcha with manually provided text"""
        try:
            # Find captcha input field
            captcha_input = self.driver.find_element(By.ID, "siwp_captcha_value_0")
            if captcha_input:
                captcha_input.clear()
                captcha_input.send_keys(captcha_text)
                logger.info(f"Filled captcha manually: {captcha_text}")
                return True
            else:
                logger.warning("Captcha input field not found")
                return False
        except Exception as e:
            logger.error(f"Failed to fill captcha manually: {e}")
            return False

    def handle_captcha(self):
        """Handle captcha if present with retry mechanism"""
        try:
            # Look for the specific captcha image used by this website
            captcha_img = self.driver.find_element(By.ID, "siwp_captcha_image_0")
            if captcha_img:
                logger.info("Captcha found, attempting to solve...")
                
                # Try up to 3 times to solve captcha
                max_attempts = 3
                for attempt in range(max_attempts):
                    logger.info(f"Captcha attempt {attempt + 1}/{max_attempts}")
                    
                    # Check if manual captcha input is enabled
                    if self.enable_manual_captcha:
                        # Save captcha image for manual review
                        captcha_file = self.save_captcha_image(captcha_img, f"captcha_attempt_{attempt + 1}.png")
                        if captcha_file:
                            print(f"\nCaptcha image saved as: {captcha_file}")
                            print("Please check the image and enter the captcha code manually.")
                            captcha_text = input("Enter captcha code: ").strip()
                        else:
                            captcha_text = "TEST123"
                    else:
                        # Use OCR
                        try:
                            pytesseract.get_tesseract_version()
                            # Use OCR to solve captcha
                            captcha_text = self.solve_captcha(captcha_img)
                        except Exception as e:
                            logger.warning(f"Tesseract not available: {e}")
                            # For testing, you can uncomment the line below to manually enter captcha
                            # captcha_text = input("Please enter the captcha code you see: ")
                            # Or use a dummy value for testing
                            captcha_text = "TEST123"
                    
                    if not captcha_text:
                        continue
                    
                    # Find captcha input field
                    captcha_input = self.driver.find_element(By.ID, "siwp_captcha_value_0")
                    if captcha_input:
                        captcha_input.clear()
                        captcha_input.send_keys(captcha_text)
                        logger.info(f"Filled captcha: {captcha_text}")
                        
                        # Submit form to check if captcha is correct
                        if self.submit_form():
                            # Check if we got an error message about incorrect captcha
                            time.sleep(3)
                            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                            
                            # Check for various error messages
                            page_text = soup.get_text().lower()
                            captcha_error = any(phrase in page_text for phrase in [
                                'captcha', 'incorrect', 'wrong', 'invalid', 'error'
                            ])
                            
                            # Also check if form is still visible (indicating validation failure)
                            form_still_visible = soup.find('form', id='ecourt-services-court-order-case-number-order')
                            
                            if captcha_error or form_still_visible:
                                logger.warning(f"Captcha validation failed on attempt {attempt + 1}")
                                logger.info(f"Page contains error: {captcha_error}, Form still visible: {form_still_visible is not None}")
                                
                                if attempt < max_attempts - 1:
                                    # Refresh the page to get a new captcha
                                    self.driver.refresh()
                                    time.sleep(3)
                                    # Wait for page to load and find new captcha
                                    WebDriverWait(self.driver, 10).until(
                                        EC.presence_of_element_located((By.ID, "est_code"))
                                    )
                                    # Re-fill form fields
                                    self.fill_form_fields(self.last_case_type, self.last_case_number, self.last_filing_year)
                                    # Find new captcha image
                                    captcha_img = self.driver.find_element(By.ID, "siwp_captcha_image_0")
                                    continue
                                else:
                                    logger.error("All captcha attempts failed")
                                    return False
                            else:
                                logger.info("Captcha validation successful")
                                return True
                        else:
                            logger.error("Failed to submit form")
                            return False
                    else:
                        logger.warning("Captcha input field not found")
                        return False
                
                return False
            
            logger.info("No captcha found")
            return True
            
        except Exception as e:
            logger.error(f"Failed to handle captcha: {e}")
            return False
    
    def submit_form(self):
        """Submit the form"""
        try:
            # Find the specific submit button for this form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "input[type='submit'][value='Search']")
            if submit_button:
                submit_button.click()
                logger.info("Form submitted")
                return True
            else:
                logger.error("Submit button not found")
                return False
                
        except Exception as e:
            logger.error(f"Failed to submit form: {e}")
            return False
    
    def extract_results(self):
        """Extract results from the page"""
        try:
            # Wait for results to load (AJAX response)
            time.sleep(5)
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for results in the specific containers used by this website
            results = {}
            
            # Look for the data table with case results
            data_tables = soup.find_all('table', class_='data-table-1')
            
            if data_tables:
                logger.info(f"Found {len(data_tables)} data table(s)")
                all_cases = []
                
                for table_index, table in enumerate(data_tables):
                    # Extract caption (court name)
                    caption = table.find('caption')
                    court_name = caption.get_text(strip=True) if caption else f"Court {table_index + 1}"
                    
                    # Extract table rows
                    tbody = table.find('tbody')
                    if tbody:
                        rows = tbody.find_all('tr')
                        logger.info(f"Found {len(rows)} case(s) in table for {court_name}")
                        
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) >= 4:  # Ensure we have all required columns
                                case_info = {}
                                
                                # Extract serial number
                                serial_span = cells[0].find('span', class_='bt-content')
                                case_info['serial_number'] = serial_span.get_text(strip=True) if serial_span else ""
                                
                                # Extract case type/number/year
                                case_span = cells[1].find('span', class_='bt-content')
                                case_info['case_details'] = case_span.get_text(strip=True) if case_span else ""
                                
                                # Extract order date
                                date_span = cells[2].find('span', class_='bt-content')
                                case_info['order_date'] = date_span.get_text(strip=True) if date_span else ""
                                
                                # Extract order details and PDF link
                                order_span = cells[3].find('span', class_='bt-content')
                                if order_span:
                                    # Look for PDF link
                                    pdf_link = order_span.find('a')
                                    if pdf_link:
                                        case_info['pdf_link'] = pdf_link.get('href', '')
                                        case_info['pdf_text'] = pdf_link.get_text(strip=True)
                                    else:
                                        case_info['order_details'] = order_span.get_text(strip=True)
                                
                                case_info['court_name'] = court_name
                                all_cases.append(case_info)
                
                if all_cases:
                    results['cases'] = all_cases
                    results['total_cases'] = len(all_cases)
                    logger.info(f"Successfully extracted {len(all_cases)} case(s) with details")
                else:
                    logger.warning("No cases found in data tables")
            
            # Check for results in the cnrResults container (fallback)
            cnr_results = soup.find('div', id='cnrResults')
            if cnr_results and cnr_results.get_text(strip=True):
                results['case_results'] = cnr_results.get_text(strip=True)
                logger.info("Found case results in cnrResults container")
            
            # Check for detailed results
            cnr_details = soup.find('div', id='cnrResultsDetails')
            if cnr_details and cnr_details.get_text(strip=True):
                results['case_details'] = cnr_details.get_text(strip=True)
                logger.info("Found case details in cnrResultsDetails container")
            
            # Check for business results
            cnr_business = soup.find('div', id='cnrResultsBusiness')
            if cnr_business and cnr_business.get_text(strip=True):
                results['business_results'] = cnr_business.get_text(strip=True)
                logger.info("Found business results in cnrResultsBusiness container")
            
            # If no results found in specific containers, look for any error messages or general content
            if not results:
                # Check for error messages or "no results" messages
                error_messages = soup.find_all(string=re.compile(r'no.*result|error|not.*found', re.I))
                if error_messages:
                    results['message'] = error_messages[0].strip()
                    logger.info(f"Found message: {results['message']}")
                else:
                    # Get the main content area
                    main_content = soup.find('div', class_='resultsHolder')
                    if main_content:
                        results['raw_content'] = main_content.get_text(strip=True)
                        logger.info("Found raw content in resultsHolder")
            
            # If still no results, check if the form is still visible (indicating no submission or error)
            if not results:
                form = soup.find('form', id='ecourt-services-court-order-case-number-order')
                if form:
                    results['status'] = 'Form still visible - possible submission error or validation failure'
                    logger.warning("Form still visible after submission")
            
            logger.info(f"Extracted results: {list(results.keys())}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to extract results: {e}")
            return {'error': str(e)}
    
    def scrape_case_data(self, case_type, case_number, filing_year):
        """Main method to scrape case data"""
        try:
            logger.info(f"Starting scrape for case: {case_type}/{case_number}/{filing_year}")
            
            # Store case data for retry purposes
            self.last_case_type = case_type
            self.last_case_number = case_number
            self.last_filing_year = filing_year
            
            # Navigate to the website
            self.driver.get(self.base_url)
            logger.info("Navigated to website")
            
            # Wait for page to load completely
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "est_code"))
            )
            logger.info("Page loaded successfully")
            
            # Fill form fields
            if not self.fill_form_fields(case_type, case_number, filing_year):
                raise Exception("Failed to fill form fields")
            
            # Handle captcha (now includes retry mechanism)
            if not self.handle_captcha():
                raise Exception("Failed to handle captcha")
            
            # Extract results (form was already submitted in handle_captcha)
            results = self.extract_results()
            
            return results
            
        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return {'error': str(e)}
        
        finally:
            # Don't close driver here as it might be reused
            pass
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

# Legacy function for backward compatibility
def scrape_case_data(case_type, case_number, filing_year):
    """Legacy function that creates a scraper instance and scrapes data"""
    scraper = NagpurCourtScraper(headless=False)
    try:
        return scraper.scrape_case_data(case_type, case_number, filing_year)
    finally:
        scraper.close()

if __name__ == "__main__":
    # Test the scraper
    scraper = NagpurCourtScraper(headless=False)
    try:
        result = scraper.scrape_case_data("Criminal", "123", "2023")
        print("Result:", result)
    finally:
        scraper.close()

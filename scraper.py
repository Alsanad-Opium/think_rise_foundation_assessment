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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NagpurCourtScraper:
    def __init__(self):
        self.base_url = "https://nagpur.dcourts.gov.in/court-orders-search-by-case-number/"
        self.driver = None
        self.setup_driver()
    
    def setup_driver(self):
        """Setup Chrome driver with appropriate options"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        # Uncomment the line below to run in headless mode
        # chrome_options.add_argument("--headless")
        
        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Chrome driver setup successful")
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def solve_captcha(self, captcha_element):
        """Solve captcha using OCR"""
        try:
            # Check if Tesseract is available
            try:
                pytesseract.get_tesseract_version()
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
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply threshold to get black text on white background
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Remove noise
            kernel = np.ones((1, 1), np.uint8)
            opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
            
            # OCR configuration for captcha
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
            
            # Extract text
            captcha_text = pytesseract.image_to_string(opening, config=custom_config)
            
            # Clean the text
            captcha_text = re.sub(r'[^a-zA-Z0-9]', '', captcha_text).strip()
            
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
                from selenium.webdriver.support.ui import Select
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
    
    def handle_captcha(self):
        """Handle captcha if present"""
        try:
            # Look for the specific captcha image used by this website
            captcha_img = self.driver.find_element(By.ID, "siwp_captcha_image_0")
            if captcha_img:
                logger.info("Captcha found, attempting to solve...")
                
                # Check if Tesseract is available
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
                    return False
                
                # Find captcha input field
                captcha_input = self.driver.find_element(By.ID, "siwp_captcha_value_0")
                if captcha_input:
                    captcha_input.clear()
                    captcha_input.send_keys(captcha_text)
                    logger.info(f"Filled captcha: {captcha_text}")
                    return True
                else:
                    logger.warning("Captcha input field not found")
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
            
            # Check for results in the cnrResults container
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
            
            # Handle captcha
            if not self.handle_captcha():
                raise Exception("Failed to handle captcha")
            
            # Submit form
            if not self.submit_form():
                raise Exception("Failed to submit form")
            
            # Extract results
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
    scraper = NagpurCourtScraper()
    try:
        return scraper.scrape_case_data(case_type, case_number, filing_year)
    finally:
        scraper.close()

if __name__ == "__main__":
    # Test the scraper
    scraper = NagpurCourtScraper()
    try:
        result = scraper.scrape_case_data("Criminal", "123", "2023")
        print("Result:", result)
    finally:
        scraper.close()

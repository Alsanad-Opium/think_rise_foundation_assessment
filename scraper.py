# scraper.py
import requests
from bs4 import BeautifulSoup

def scrape_case_data(case_type, case_number, filing_year):
    session = requests.Session()

    # Step 1: Setup your payload (this needs to be adjusted based on real form submission)
    payload = {
        'state_code': 'MH',        # Maharashtra example
        'dist_code': 'NAG',        # Nagpur example
        'court_code': '1',         # May vary
        'case_type': case_type,
        'case_number': case_number,
        'case_year': filing_year,
    }

    headers = {
        'User-Agent': 'Mozilla/5.0',
    }

    try:
        # Step 2: Go to the main case status search page (simulate form submission)
        search_url = "https://services.ecourts.gov.in/ecourtindia_v6/?p=casestatus/index&app_token=site&app_name=ecourts"

        response = session.post(search_url, data=payload, headers=headers)

        if "No record found" in response.text:
            raise ValueError("Invalid case details or no data available.")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Step 3: Parse basic metadata (examples - may need tweaking)
        party_block = soup.find("div", {"class": "PartyName"})
        filing_date = soup.find("span", string="Filing:")
        hearing_date = soup.find("span", string="Next Hearing Date:")
        pdf_tag = soup.find("a", href=True, string="Order/Judgment")

        return {
            'party_names': party_block.text.strip() if party_block else "Not found",
            'filing_date': filing_date.find_next("span").text.strip() if filing_date else "Not available",
            'next_hearing_date': hearing_date.find_next("span").text.strip() if hearing_date else "Not available",
            'latest_order_pdf': "https://services.ecourts.gov.in" + pdf_tag['href'] if pdf_tag else "Not found"
        }

    except Exception as e:
        raise RuntimeError(f"Scraping failed: {e}")

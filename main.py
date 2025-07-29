from IC_web_scraper import scrape_all_acts
import os
# === CONFIGURATION ===
CHROMEDRIVER_PATH = "chromedriver/chromedriver.exe"
BASE_URL = "https://www.indiacode.nic.in"
ACTS_LIST_URL = f"{BASE_URL}/handle/123456789/1362/browse?type=shorttitle"
json_pdf_directory = "acts_json_pdf"



if __name__ == "__main__":
    os.makedirs(json_pdf_directory, exist_ok=True)
    scrape_all_acts(CHROMEDRIVER_PATH,ACTS_LIST_URL,json_pdf_directory)
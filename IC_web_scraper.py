# === INDIA CODE SCRAPER ===
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import json, time, os, re

# === STEP 0: Activate WebDriver ===
def activate_webdriver(CHROMEDRIVER_PATH,json_pdf_directory):
    options = Options()
    prefs = {"download.default_directory": json_pdf_directory}
    options.add_experimental_option("prefs", prefs)
    # options.add_argument("--headless")
    service = Service(CHROMEDRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# === STEP 1: Load Acts List and extract links ===
def extract_act_links(driver,ACTS_LIST_URL):
    driver.get(ACTS_LIST_URL)
    time.sleep(3)
    act_title = driver.find_elements(By.XPATH, "(//table//tr//strong)")
    act_titles_list = [title.text for title in act_title if title.text.strip()]
    del act_title[0] # Remove header row
    act_links_list = driver.find_elements(By.XPATH, "//table//tr//td//a")
    act_url_list = [link.get_attribute("href") for link in act_links_list]
    return act_titles_list,act_url_list, driver

# === STEP 3: Extract Metadata ===
def extract_metadata(soup):
    meta_table = soup.select("table.itemDisplayTable tr")
    metadata = {}
    for row in meta_table:
        key = row.select_one(".metadataFieldLabel")
        val = row.select_one(".metadataFieldValue")
        if key and val:
            metadata[key.text.strip().replace(":", "")] = val.text.strip()
    return metadata

# === STEP 4: Scrape Chapters and Sections ===
def scrape_chapters_and_sections(driver):
    PARTS = {"Chapter": {}}
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#showallchapterindex, .preambletitle")))
    chapter_id_list = driver.find_elements(By.XPATH, "//a[contains(@id, 'showallchapterindex')]/..//li//b")
    chapter_name_list = driver.find_elements(By.XPATH, "//a[contains(@id, 'showallchapterindex')]/..//li//a")

    for idx in range(len(chapter_id_list)):
        try:
            chapter_id = chapter_id_list[idx].text.strip()
            chapter_name = chapter_name_list[idx].text.strip()
            if not chapter_id: continue

            if chapter_name not in PARTS["Chapter"]:
                PARTS["Chapter"][chapter_name] = {}
            if chapter_id not in PARTS["Chapter"][chapter_name]:
                PARTS["Chapter"][chapter_name][chapter_id] = {}

            print(f"Processing Chapter {idx+1}: {chapter_name} (ID: {chapter_id})")
            driver.execute_script("arguments[0].click();", chapter_name_list[idx])
            time.sleep(3)

            section_index_name_list = driver.find_elements(By.XPATH, "//div[contains(@id, 'chapterid')]//tbody//tr")
            section_idx = 0
            section_length = len(section_index_name_list)

            while section_idx < section_length:
                try:
                    section_name = section_index_name_list[section_idx].text.strip()
                    match = re.match(r"(Section\s*\d+[A-Za-z]*)\.\s*(.+)", section_name)
                    if match:
                        section_num, section_title = match.groups()
                        print(f"Processing Section: {section_num} - {section_title}")

                        row = section_index_name_list[section_idx]
                        link_elem = row.find_element(By.XPATH, ".//a")
                        href = link_elem.get_attribute("href")
                        print(f"Opening Section URL: {href}")

                        driver.execute_script(f"window.open('{href}', '_blank');")
                        WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                        original_window = driver.current_window_handle
                        new_window = [h for h in driver.window_handles if h != original_window][0]
                        driver.switch_to.window(new_window)

                        section_content = driver.find_element(By.XPATH,"(//div[contains(@class, 'panel-body')]//p)[1]").text.strip()
                        section_footnotes = driver.find_element(By.XPATH,"(//div[contains(@class, 'panel-body')]//p)[2]").text.strip()

                        driver.close()
                        driver.switch_to.window(original_window)
                        print("✅ Successfully switched back to original tab.")

                        section_para = {str(i): p for i, p in enumerate(section_content.split("\n")) if p.strip()}
                        footnotes = {str(i): p for i, p in enumerate(section_footnotes.split("\n")) if p.strip()}

                        PARTS["Chapter"][chapter_id][chapter_name][section_num + "."] = {
                            "Title": section_title,
                            "Paragraph": section_para,
                            "Footnotes": footnotes
                        }

                        if section_idx == len(section_index_name_list) - 1:
                            section_next_button = driver.find_element(By.XPATH, "(//div[contains(@class, 'panel-group')]//a[contains(@class,'next')])[1]")
                            if "disabled" not in section_next_button.get_attribute("class"):
                                print("Moving to next section page...")
                                section_next_button.click()
                                time.sleep(3)
                                section_index_name_list = driver.find_elements(By.XPATH, "//div[contains(@id, 'chapterid')]//tbody//tr")
                                section_length = len(section_index_name_list)
                                section_idx = 0
                                continue
                            else:
                                print("No more section found, moving to next chapter.")

                    section_idx += 1

                except Exception as e:
                    print(f"❗ Error processing section in chapter {idx}: {str(e)}")
                    continue

        except Exception as e:
            print(f"Error processing chapter {idx}: {str(e)}")
            continue

    return PARTS


def scrape_only_sections(driver):
    PARTS = {"Section": {}}
    section_index_name_list = driver.find_elements(By.XPATH, "//table[contains(@id,'Section')]//tbody//tr")
    section_idx = 0
    section_length = len(section_index_name_list)

    while section_idx < section_length:
        try:
            section_name = section_index_name_list[section_idx].text.strip()
            match = re.match(r"(Section\s*\d+[A-Za-z]*)\.\s*(.+)", section_name)
            if match:
                section_num, section_title = match.groups()
                print(f"Processing Section: {section_num} - {section_title}")

                row = section_index_name_list[section_idx]
                link_elem = row.find_element(By.XPATH, ".//a")
                href = link_elem.get_attribute("href")
                print(f"Opening Section URL: {href}")

                driver.execute_script(f"window.open('{href}', '_blank');")
                WebDriverWait(driver, 10).until(lambda d: len(d.window_handles) > 1)
                original_window = driver.current_window_handle
                new_window = [h for h in driver.window_handles if h != original_window][0]
                driver.switch_to.window(new_window)

                section_content = driver.find_element(By.XPATH,"(//div[contains(@class, 'panel-body')]//p)[1]").text.strip()
                section_footnotes = driver.find_element(By.XPATH,"(//div[contains(@class, 'panel-body')]//p)[2]").text.strip()

                driver.close()
                driver.switch_to.window(original_window)
                print("✅ Successfully switched back to original tab.")

                section_para = {str(i): p for i, p in enumerate(section_content.split("\n")) if p.strip()}
                footnotes = {str(i): p for i, p in enumerate(section_footnotes.split("\n")) if p.strip()}

                PARTS["Section"][section_num + "."] = {
                    "Title": section_title,
                    "Paragraph": section_para,
                    "Footnotes": footnotes
                }
                if section_idx == len(section_index_name_list) - 1:
                    section_next_button = driver.find_element(By.XPATH, "(//div[contains(@class, 'panel-group')]//a[contains(@class,'next')])[1]")
                    if "disabled" not in section_next_button.get_attribute("class"):
                        print("Moving to next section page...")
                        section_next_button.click()
                        time.sleep(3)
                        # Update section_index_name_list
                        section_index_name_list = driver.find_elements(By.XPATH, "//table[contains(@id,'Section')]//tbody//tr")
                        section_length = len(section_index_name_list)
                        section_idx = 0
                        continue
                    else:
                        print("No more sections found.")
                section_idx += 1
        except Exception as e:
            print(f"❗ Error processing section {section_idx}: {str(e)}")
            continue

    return PARTS
# === STEP 5: Main Scraper Execution ===
def scrape_all_acts(CHROMEDRIVER_PATH, ACTS_LIST_URL,json_pdf_directory):
    
    #Activate Selenium WebDriver for Google Chrome
    driver = activate_webdriver(CHROMEDRIVER_PATH,json_pdf_directory)
        
    act_titles_list,act_url_list, driver = extract_act_links(driver, ACTS_LIST_URL)

    act_idx = 0
    act_length = len(act_url_list)

    while act_idx < act_length:
        print(f"\n[{act_idx+1}] Scraping: {act_titles_list[act_idx]}")
        driver.get(act_url_list[act_idx])
        time.sleep(3)

        try:
            driver.find_element(By.LINK_TEXT, "Actdetails").click()
            time.sleep(2)

            # === ACT METADATA ===
            # Parse the full page after tabs are loaded
            soup = BeautifulSoup(driver.page_source, "html.parser")
            meta_table = soup.select("table.itemDisplayTable tr")
            # print(meta_table)
            metadata = {}
            for row in meta_table:
                key = row.select_one(".metadataFieldLabel")
                val = row.select_one(".metadataFieldValue")
                if key and val:
                    metadata[key.text.strip().replace(":", "")] = val.text.strip()

            act_title = metadata.get("Short Title","")
            act_id = f"ACT NO. {metadata.get('Act Number', '')} OF {metadata.get('Act Year', '')}"
            enactment_date = f"{metadata.get('Enactment Date', '')}"
            long_title = metadata.get("Long Title", "")
            act_definition = {str(i): p.strip() for i, p in enumerate(long_title.split(". ")) if p.strip()}
            ministry = metadata.get("Ministry", "")
            department = metadata.get("Department", "")
            enforcement_date = metadata.get("Enforcement Date", "")
            last_updated = metadata.get("Last Updated", "")

        except Exception as e:
            print("❌ Failed to load Act Details tab.", e)
            continue

        try:
            # Check if chapters are present
            if driver.find_elements(By.XPATH, "//a[contains(@id, 'showallchapterindex')]/..//li//b"):
                print("Chapters found, looking for sections...")
                try:
                    driver.find_element(By.LINK_TEXT, "Sections").click()
                    print("Chapters and sections both found, scraping...")
                    time.sleep(2)
                    PARTS = scrape_chapters_and_sections(driver)
                except Exception as e:
                    print("❌ Failed to load Sections tab.", e)
                    continue
                
            else:
                print("No chapters found, looking for sections ")
                try:
                    driver.find_element(By.LINK_TEXT, "Sections").click()
                    print("Sections found, scraping...")
                    time.sleep(2)
                    PARTS = scrape_only_sections(driver)
                except Exception as e:
                    print("❌ No Chapters or sections found....Downloading PDF file", e)
                    pdf_element = driver.find_element(By.XPATH, "(//p[contains(@id, 'short_title')])[1]")
                    pdf_element.click()
                    time.sleep(5)
                    continue
                
        except Exception as e:
            print(f"Chapter extraction failed: {str(e)}")
            PARTS = {}

        try:
            driver.find_element(By.LINK_TEXT, "Sections").click()
            time.sleep(2)
        except Exception as e:
            print("❌ Failed to load Sections tab.", e)
            continue


        act_data = {
            "Act Title": act_title,
            "Act ID": act_id,
            "Enactment Date": enactment_date,
            "Act Definition": act_definition,
            "Ministry": ministry,
            "Department": department,
            "Enforcement Date": enforcement_date,
            "Last Updated": last_updated,
            "PARTS": PARTS
        }

        file_name = re.sub(r"[^\w\s-]", "", act_title).strip().replace(" ", "_") + ".json"
        with open(os.path.join(json_pdf_directory, file_name), "w", encoding="utf-8") as f:
            json.dump(act_data, f, indent=4, ensure_ascii=False)
        print(f"✅ Saved JSON: {file_name}")

        print(f"Finished scraping {act_title}.")
        print("=" * 40)
        print("Moving to next act...")

        # End of Table so move to next page
        if act_idx == len(act_url_list) - 1:
            print("Moving to next page of acts...")
            # Go to Acts Page
            driver.back()
            time.sleep(3)
            next_button = driver.find_element(By.XPATH, "(//a[contains(@class, 'pull-right')])[2]")
            if "disabled" not in next_button.get_attribute("class"):
                print("Moving to next act page...")
                next_button.click()
                act_titles_list,act_url_list, driver = extract_act_links(driver, ACTS_LIST_URL)
                time.sleep(3)
                continue
            else:
                print("No more acts found. 878 Acts done!!!")
                break
        act_idx += 1
        


    driver.quit()



## TO-DO:
# 1. Add nested chapters and sections handling.
##    - Ensure that chapters can have multiple sections and subsections.
##    - Usual path: //a[contains(@id, 'showallchapterindex')]/..//li//ul//ul
# 2. Put chapter Number before chapter name in the JSON file. (Done) 
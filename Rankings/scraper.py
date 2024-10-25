from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from bs4 import BeautifulSoup
from Rankings.models import StudentInfo, Marks
from django.db import IntegrityError
from concurrent.futures import ThreadPoolExecutor
import os
import time

# Set up Chrome options for headless mode and performance
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--ignore-certificate-errors')
chrome_options.add_argument('--log-level=3')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-popup-blocking')
chrome_options.add_argument('--disable-features=NetworkService,NetworkServiceInProcess')
chrome_options.add_argument('--blink-settings=imagesEnabled=false')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Linux; Android 9; Pixel 3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36')

prefs = {
    "profile.managed_default_content_settings.images": 2,  # Disable images
    "profile.default_content_setting_values.notifications": 2,  # Disable notifications
    "profile.managed_default_content_settings.stylesheets": 2, # Disable Stylesheets
}
chrome_options.add_experimental_option("prefs", prefs)

# Reuse driver session across multiple scrapes
def init_driver():
    service = Service(log_path=os.devnull)
    return webdriver.Chrome(options=chrome_options, service=service)

def scrape_roll_number(roll_number, driver):
    try:
        url = 'https://hscresult.bise-ctg.gov.bd/h1624/individual/'
        driver.get(url)

        # Scraping logic
        roll_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, 'roll'))
        )
        roll_input.send_keys(str(roll_number))

        submit_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@type="submit"]'))
        )
        driver.execute_script("document.querySelector('form').submit();")

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.tftable2'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        roll_no = soup.find_all('td')[1].text.strip()
        name = soup.find_all('td')[3].text.strip()
        board = soup.find_all('td')[5].text.strip()
        father_name = soup.find_all('td')[7].text.strip()
        group = soup.find_all('td')[9].text.strip()
        mother_name = soup.find_all('td')[11].text.strip()
        session = soup.find_all('td')[13].text.strip()
        reg_no = soup.find_all('td')[15].text.strip()
        type_of_result = soup.find_all('td')[17].text.strip()
        institute = soup.find_all('td')[19].text.strip()
        result = soup.find_all('td')[21].text.strip()
        gpa = soup.find_all('td')[23].text.strip()

        # Parsing marks logic
        subject_rows = soup.select('.tftable2 tbody tr')
        marks_data = {}
        for row in subject_rows:
            cols = row.find_all('td')
            if len(cols) == 2:
                subject_code = cols[0].text.strip().split('(')[-1].replace(')', '')
                marks_text = cols[1].text.strip().split('(')[-1].replace(')', '').strip()
                marks = int(marks_text) if marks_text.isdigit() else 0
                marks_data[subject_code] = marks

        # Map subject codes to fields in the Marks model
        bangla = marks_data.get('101', 0)
        english = marks_data.get('107', 0)
        ict = marks_data.get('275', 0)
        physics = marks_data.get('174', 0)
        chemistry = marks_data.get('176', 0)
        biology = marks_data.get('178', 0)
        higher_math = marks_data.get('265', 0)
        statistics = marks_data.get('129', 0)
        finance = marks_data.get('292', 0)
        management = marks_data.get('277', 0)
        accounting = marks_data.get('253', 0)
        production = marks_data.get('286', 0)
        economics = marks_data.get('109', 0)
        logic = marks_data.get('121', 0)
        sociology = marks_data.get('117', 0)
        social_work = marks_data.get('271', 0)
        home_science = marks_data.get('273', 0)
        islamic_history = marks_data.get('267', 0)
        civics = marks_data.get('269', 0)

        # Update or create the marks for the existing student
        try:
            student_info, created = StudentInfo.objects.get_or_create(roll_no=roll_no,
            defaults={
                'name': name,
                'board': board,
                'father_name': father_name,
                'group': group,
                'mother_name': mother_name,
                'session': session,
                'reg_no': reg_no,
                'type_of_result': type_of_result,
                'institute': institute,
                'result': result,
                'gpa': gpa
            }
        )

            Marks.objects.create(
                student=student_info,
                bangla=bangla,
                english=english,
                ict=ict,
                physics=physics,
                chemistry=chemistry,
                biology=biology,
                higher_math=higher_math,
                statistics=statistics,
                accounting=accounting,
                management=management,
                finance=finance,
                production=production,
                economics=economics,
                logic=logic,
                sociology=sociology,
                social_work=social_work,
                home_science=home_science,
                islamic_history=islamic_history,
                civics=civics,
                total_marks=sum([
                    bangla, english, ict, physics, chemistry, biology,
                    higher_math, statistics, accounting, management,
                    finance, production, economics, logic, sociology,
                    social_work, home_science, islamic_history, civics
                ])
            )
        except StudentInfo.DoesNotExist:
            print(f"Student with roll number {roll_number} does not exist.")

    except WebDriverException as e:
        print(f"WebDriverException for roll number {roll_number}: {e}")

# List of roll numbers to scrape
roll_numbers = [300001]

driver = init_driver()

for idx, roll in enumerate(roll_numbers):
    scrape_roll_number(roll, driver)
    
    # Restart WebDriver every 500 roll numbers
    if idx > 0 and idx % 500 == 0:
        driver.quit()
        print(f"Restarting driver after {idx} roll numbers...")
        driver = init_driver()

# Quit the driver after all scraping is done
driver.quit()


        
        


# not_created: 500180, 500740
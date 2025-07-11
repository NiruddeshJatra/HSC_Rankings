import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HSC_Rankings.settings')
django.setup()

import requests
from bs4 import BeautifulSoup
from Rankings.models import StudentInfo, Marks
from concurrent.futures import ThreadPoolExecutor, as_completed

# Subject code to Marks model field mapping for SSC
SSC_SUBJECT_CODE_MAP = {
    '101': 'bangla',
    '107': 'english',
    '109': 'math',
    '136': 'physics',
    '137': 'chemistry',
    '138': 'biology',
    '126': 'higher_math',
    '154': 'ict',
    '111': 'islam_moral',
    '112': 'hindu_moral',
    '113': 'buddha_moral',
    '114': 'christian_moral',
    '150': 'bangladesh_world',
    '134': 'agriculture',
    '151': 'home_science',
    '152': 'finance_banking',
    '146': 'accounting',
    '143': 'business_ent',
    '127': 'general_science',
    '149': 'music',
    '110': 'geography',
    '140': 'civics',
    '141': 'economics',
    '153': 'history_bd',
    '147': 'physical_education',  # NEW
    '156': 'career_education',   # NEW
}

RESULT_URL = "https://sresult.bise-ctg.gov.bd/rxto2025/individual/result.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Referer": "https://sresult.bise-ctg.gov.bd/rxto2025/individual/index.php"
}

def fetch_and_save_ssc_result(roll_number, max_retries=5):
    data = {
        "roll": str(roll_number),
        "button2": "Submit"
    }
    for attempt in range(max_retries):
        try:
            response = requests.post(RESULT_URL, data=data, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            tds = soup.find_all('td')
            if len(tds) < 2:
                print(f"No result found for roll: {roll_number}")
                return False  # Not saved
            roll_no = tds[1].text.strip() if len(tds) > 1 else ''
            name = tds[3].text.strip() if len(tds) > 3 else ''
            board = tds[5].text.strip() if len(tds) > 5 else ''
            father_name = tds[7].text.strip() if len(tds) > 7 else ''
            group = tds[9].text.strip() if len(tds) > 9 else ''
            mother_name = tds[11].text.strip() if len(tds) > 11 else ''
            session = tds[13].text.strip() if len(tds) > 13 else ''
            reg_no = tds[15].text.strip() if len(tds) > 15 else ''
            type_of_result = tds[17].text.strip() if len(tds) > 17 else ''
            institute = tds[19].text.strip() if len(tds) > 19 else ''
            result_gpa = tds[21].text.strip() if len(tds) > 21 else ''
            dob = tds[23].text.strip() if len(tds) > 23 else ''

            # Parse GPA and result
            if 'GPA=' in result_gpa:
                result, gpa = result_gpa.split('GPA=')
                result = result.strip()
                gpa = gpa.strip()
            else:
                result = result_gpa
                gpa = ''

            # Extract subject marks from the second table
            subject_rows = soup.select('.tftable2 tbody tr')
            marks_data = {field: 0 for field in SSC_SUBJECT_CODE_MAP.values()}  # Default 0 for all
            for row in subject_rows:
                cols = row.find_all('td')
                if len(cols) == 3:
                    code = cols[0].text.strip()
                    mark_grade = cols[2].text.strip()
                    # Extract numeric mark before '(' if present
                    mark = 0
                    if '(' in mark_grade:
                        try:
                            mark = int(mark_grade.split('(')[0])
                        except ValueError:
                            mark = 0
                    else:
                        try:
                            mark = int(mark_grade)
                        except ValueError:
                            mark = 0
                    field = SSC_SUBJECT_CODE_MAP.get(code)
                    if field:
                        marks_data[field] = mark
            # Calculate total marks after all subjects are processed
            total_marks = sum(marks_data.values())
            # Debug print for problematic student
            if roll_no == '114143':
                print(f"DEBUG: Roll {roll_no}, marks_data: {marks_data}, total_marks: {total_marks}")
            # Save to database
            student_info, created = StudentInfo.objects.get_or_create(
                roll_no=roll_no,
                exam_type='SSC',
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
            Marks.objects.update_or_create(
                student=student_info,
                defaults={
                    **marks_data,
                    'total_marks': total_marks
                }
            )
            print(f"Saved SSC result for roll: {roll_no}")
            return True  # Saved
        except Exception as e:
            if "database is locked" in str(e):
                wait_time = 0.5 + attempt * 0.5
                print(f"Database is locked for roll {roll_number}, retrying in {wait_time:.1f}s (attempt {attempt+1})")
                time.sleep(wait_time)
                continue
            print(f"Error for roll number {roll_number}: {e}")
            return False  # Not saved
        print(f"Failed to save roll {roll_number} after {max_retries} retries due to database lock.")
        return False

# List of roll numbers to scrape (SSC 2025, test with 100 rolls)
# Read roll numbers from failed_rolls.txt
# try:
#     with open("failed_rolls.txt", "r") as f:
#         roll_numbers = [int(line.strip()) for line in f if line.strip()]
#     print(f"Loaded {len(roll_numbers)} roll numbers from failed_rolls.txt")
# except FileNotFoundError:
#     print("failed_rolls.txt not found. Using empty list.")
#     roll_numbers = []
# except Exception as e:
#     print(f"Error reading failed_rolls.txt: {e}")
roll_numbers = [114143]

failed_rolls = []
max_workers = 3
with ThreadPoolExecutor(max_workers=max_workers) as executor:
    future_to_roll = {executor.submit(fetch_and_save_ssc_result, roll): roll for roll in roll_numbers}
    for future in as_completed(future_to_roll):
        roll = future_to_roll[future]
        try:
            result = future.result()
            if not result:
                failed_rolls.append(roll)
        except Exception as exc:
            print(f"Exception for roll {roll}: {exc}")
            failed_rolls.append(roll)

if failed_rolls:
    with open("failed_rolls.txt", "w") as f:
        for roll in failed_rolls:
            f.write(f"{roll}\n")
    print(f"Failed rolls saved to failed_rolls.txt: {failed_rolls}")
else:
    print("All rolls saved successfully!")
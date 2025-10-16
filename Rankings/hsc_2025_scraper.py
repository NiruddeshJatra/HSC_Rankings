import sys
import os
import time
import random
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HSC_Rankings.settings')
django.setup()

from Rankings.models import StudentInfo, Marks

# Subject code to Marks model field mapping for HSC 2025
HSC_SUBJECT_CODE_MAP = {
    '101': 'bangla',
    '107': 'english',
    '275': 'ict',
    '174': 'physics',
    '176': 'chemistry',
    '178': 'biology',
    '265': 'higher_math',
    '129': 'statistics',
    '292': 'finance',
    '277': 'management',
    '253': 'accounting',
    '286': 'production',
    '109': 'economics',
    '121': 'logic',
    '117': 'sociology',
    '271': 'social_work',
    '273': 'home_science',
    '267': 'islamic_history',
    '269': 'civics',
}

BASE_URL = "https://hscresult.bise-ctg.gov.bd/h_x_y_ctg25/individual"
RESULT_URL = f"{BASE_URL}/result_mark_details.php"
INDEX_URL = f"{BASE_URL}/index.php"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": INDEX_URL,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded",
    "Origin": "https://hscresult.bise-ctg.gov.bd",
}

def create_session():
    session = requests.Session()
    
    # First visit the index page to get initial cookies
    try:
        print("Getting initial session cookies...")
        session.get(INDEX_URL, headers=HEADERS, timeout=10)
        time.sleep(0.5)  # Small delay after initial request
    except Exception as e:
        print(f"Warning: Could not get initial session: {e}")
    
    # Set up retry strategy
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def fetch_and_save_hsc_2025_result(roll_number, session, max_retries=3):
    data = {
        "roll": str(roll_number),
        "button2": "Submit"
    }
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            response = session.post(RESULT_URL, data=data, headers=HEADERS, timeout=15)
            elapsed = time.time() - start_time
            
            # Check if response is valid
            if response.status_code != 200:
                print(f"⚠️ HTTP {response.status_code} for roll: {roll_number}")
                if attempt < max_retries - 1:
                    wait_time = 1 + attempt
                    print(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                return False
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Check if result exists by looking for the info table
            info_table = soup.find('table', class_='tftable')
            if not info_table:
                print(f"ℹ️ No result found for roll: {roll_number}")
                return False
            
            # Extract all rows from the info table
            rows = info_table.find_all('tr')
            if len(rows) < 6:
                print(f"Unexpected table structure for roll: {roll_number}")
                return False
            
            # Helper function to safely extract cell values
            def get_cell_value(row, index):
                cells = row.find_all('td')
                return cells[index].text.strip() if len(cells) > index else ''
            
            # Row 0: Roll and Name
            roll_no = get_cell_value(rows[0], 1)
            name = get_cell_value(rows[0], 3)
            
            # Row 1: Board and Father's Name
            board = get_cell_value(rows[1], 1)
            father_name = get_cell_value(rows[1], 3)
            
            # Row 2: Group and Mother's Name
            group = get_cell_value(rows[2], 1)
            mother_name = get_cell_value(rows[2], 3)
            
            # Row 3: Session and Registration Number
            session_year = get_cell_value(rows[3], 1)
            reg_no = get_cell_value(rows[3], 3)
            
            # Row 4: Type and Institute
            type_of_result = get_cell_value(rows[4], 1)
            institute = get_cell_value(rows[4], 3)
            
            # Row 5: Result and GPA
            result = get_cell_value(rows[5], 1)
            gpa_str = get_cell_value(rows[5], 3)
            
            # Parse GPA
            try:
                gpa = float(gpa_str) if gpa_str else 0.0
            except ValueError:
                gpa = 0.0
            
            # Extract subject marks from the second table
            marks_table = soup.find('table', class_='tftable2')
            marks_data = {}
            
            if marks_table:
                for row in marks_table.find_all('tr')[1:]:  # Skip header row
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        subject_text = cols[0].text.strip()
                        marks_text = cols[1].text.strip()
                        
                        # Extract subject code from text like "BANGLA(101)"
                        if '(' in subject_text and ')' in subject_text:
                            code = subject_text.split('(')[-1].replace(')', '').strip()
                            
                            # Extract numeric mark from text like "A-(136)" or "D (078)"
                            mark = 0
                            if '(' in marks_text and ')' in marks_text:
                                try:
                                    # Extract the number inside parentheses
                                    mark_str = marks_text.split('(')[-1].replace(')', '').strip()
                                    mark = int(mark_str)
                                except ValueError:
                                    mark = 0
                            
                            # Map to database field
                            field = HSC_SUBJECT_CODE_MAP.get(code)
                            if field:
                                marks_data[field] = mark

            # Calculate total marks
            total_marks = sum(marks_data.values())
            
            # Save to database
            student_info, created = StudentInfo.objects.get_or_create(
                roll_no=roll_no,
                exam_type='HSC_2025',
                defaults={
                    'name': name,
                    'board': board,
                    'father_name': father_name,
                    'group': group,
                    'mother_name': mother_name,
                    'session': session_year,
                    'reg_no': reg_no,
                    'type_of_result': type_of_result,
                    'institute': institute,
                    'result': result,
                    'gpa': gpa
                }
            )
            
            # Update if already exists
            if not created:
                student_info.name = name
                student_info.board = board
                student_info.father_name = father_name
                student_info.group = group
                student_info.mother_name = mother_name
                student_info.session = session_year
                student_info.reg_no = reg_no
                student_info.type_of_result = type_of_result
                student_info.institute = institute
                student_info.result = result
                student_info.gpa = gpa
                student_info.save()
            
            Marks.objects.update_or_create(
                student=student_info,
                defaults={
                    **marks_data,
                    'total_marks': total_marks
                }
            )
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Request error for roll {roll_number} (attempt {attempt+1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 + attempt)  # Progressive backoff
                continue
            return False
            
        except Exception as e:
            if "database is locked" in str(e):
                wait_time = 1 + attempt * 0.5
                print(f"Database locked for roll {roll_number}, retrying in {wait_time}s")
                time.sleep(wait_time)
                continue
            print(f"Unexpected error for roll {roll_number}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return False

def main():
    # Read roll numbers from file or define range
    try:
        with open("hsc_2025_rolls.txt", "r") as f:
            roll_numbers = [int(line.strip()) for line in f if line.strip()]
        print(f"Loaded {len(roll_numbers)} roll numbers from hsc_2025_rolls.txt")
    except FileNotFoundError:
        # Example: Roll numbers for Chittagong Board HSC 2025
        start_roll = 112781
        end_roll = 121172  # Test with 10 rolls first
        roll_numbers = [101642, 101895, 103433, 105710, 107824, 109638, 110686]
    
    failed_rolls = []
    successful_count = 0
    
    # Use session for connection pooling and reuse
    session = create_session()
    
    # Adjust max_workers based on server capacity
    max_workers = 5  # Conservative to avoid overwhelming the server
    
    print(f"Starting HSC 2025 scraping with {max_workers} workers...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_roll = {
            executor.submit(fetch_and_save_hsc_2025_result, roll, session): roll 
            for roll in roll_numbers
        }
        
        # Process completed tasks
        for future in as_completed(future_to_roll):
            roll = future_to_roll[future]
            try:
                result = future.result()
                if result:
                    successful_count += 1
                else:
                    failed_rolls.append(roll)
            except Exception as exc:
                print(f"❌ Exception for roll {roll}: {exc}")
                failed_rolls.append(roll)
            
            # Progress update
            completed = successful_count + len(failed_rolls)
            if completed % 100 == 0 or completed == len(roll_numbers):
                print(f"\n=== Progress: {completed}/{len(roll_numbers)} ===")
            
            # Small delay between requests
            time.sleep(0.2)
    
    # Close session
    session.close()
    
    # Save failed rolls for retry
    if failed_rolls:
        with open("failed_rolls_hsc_2025.txt", "w") as f:
            for roll in failed_rolls:
                f.write(f"{roll}\n")
        print(f"\n❌ Failed rolls ({len(failed_rolls)}) saved to failed_rolls_hsc_2025.txt")
    
    print(f"\n✅ HSC 2025 scraping completed!")
    print(f"   Successful: {successful_count}")
    print(f"   Failed: {len(failed_rolls)}")
    print(f"   Success rate: {(successful_count/len(roll_numbers))*100:.1f}%")

if __name__ == "__main__":
    main()

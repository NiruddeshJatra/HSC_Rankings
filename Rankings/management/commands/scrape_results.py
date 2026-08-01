import itertools
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand, CommandError

from Rankings.models import ExamSet, StudentInfo, Marks
from Rankings.subject_maps import get_subject_map

RESULT_ENDPOINT = {'hsc': 'result_mark_details.php', 'ssc': 'result.php'}

CONSECUTIVE_FAILURE_LIMIT = 20
UNKNOWN_CODE_LIMIT = 50
MAX_RETRIES = 3
INITIAL_BACKOFF = 2
CHUNK_SIZE_MULTIPLIER = 4


class ParserDrift(Exception):
    def __init__(self, message, html):
        super().__init__(message)
        self.html = html


def parse_hsc(html, roll, subject_map):
    soup = BeautifulSoup(html, 'html.parser')
    info_table = soup.find('table', class_='tftable')
    if not info_table:
        return None  # no result for this roll

    rows = info_table.find_all('tr')
    if len(rows) < 6:
        raise ParserDrift(f"HSC info table has {len(rows)} rows, expected >= 6", html)

    def cell(row_index, col_index):
        cells = rows[row_index].find_all('td')
        return cells[col_index].text.strip() if len(cells) > col_index else ''

    roll_no = cell(0, 1)
    name = cell(0, 3)
    board = cell(1, 1)
    father_name = cell(1, 3)
    group = cell(2, 1)
    mother_name = cell(2, 3)
    session = cell(3, 1)
    reg_no = cell(3, 3)
    type_of_result = cell(4, 1)
    institute = cell(4, 3)
    result = cell(5, 1)
    gpa_str = cell(5, 3)

    marks_data = {}
    matched_codes = []
    unknown_codes = {}
    marks_table = soup.find('table', class_='tftable2')
    if marks_table:
        for row in marks_table.find_all('tr')[1:]:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            subject_text = cols[0].text.strip()
            marks_text = cols[1].text.strip()
            if '(' in subject_text and ')' in subject_text:
                code = subject_text.split('(')[-1].replace(')', '').strip()
                mark = 0
                if '(' in marks_text and ')' in marks_text:
                    try:
                        mark = int(marks_text.split('(')[-1].replace(')', '').strip())
                    except ValueError:
                        mark = 0
                field = subject_map.get(code)
                if field:
                    marks_data[field] = mark
                    matched_codes.append((code, field, mark))
                else:
                    unknown_codes[code] = subject_text

    return {
        'roll_no': roll_no, 'name': name, 'board': board, 'father_name': father_name,
        'group': group, 'mother_name': mother_name, 'session': session, 'reg_no': reg_no,
        'type_of_result': type_of_result, 'institute': institute, 'result': result,
        'gpa_str': gpa_str, 'marks_data': marks_data, 'matched_codes': matched_codes,
        'unknown_codes': unknown_codes,
    }


def parse_ssc(html, roll, subject_map):
    soup = BeautifulSoup(html, 'html.parser')
    tds = soup.find_all('td')
    if len(tds) < 2:
        return None  # no result for this roll

    if len(tds) < 22:
        raise ParserDrift(f"SSC result page has {len(tds)} <td> cells, expected >= 22", html)

    def cell(index):
        return tds[index].text.strip() if len(tds) > index else ''

    roll_no = cell(1)
    name = cell(3)
    board = cell(5)
    father_name = cell(7)
    group = cell(9)
    mother_name = cell(11)
    session = cell(13)
    reg_no = cell(15)
    type_of_result = cell(17)
    institute = cell(19)
    result_gpa = cell(21)

    if 'GPA=' in result_gpa:
        result, gpa_str = result_gpa.split('GPA=')
        result = result.strip()
        gpa_str = gpa_str.strip()
    else:
        result = result_gpa
        gpa_str = ''

    if not result and gpa_str:
        # The board portal prints no status text for passing students -
        # it shows "GPA=X.XX" alone. Store that inferred status explicitly
        # rather than leaving result blank.
        result = 'PASS'

    marks_data = {field: 0 for field in subject_map.values()}
    matched_codes = []
    unknown_codes = {}
    for row in soup.select('.tftable2 tbody tr'):
        cols = row.find_all('td')
        if len(cols) != 3:
            continue
        code = cols[0].text.strip()
        subject_text = cols[1].text.strip()
        mark_grade = cols[2].text.strip()
        mark = 0
        try:
            mark = int(mark_grade.split('(')[0]) if '(' in mark_grade else int(mark_grade)
        except ValueError:
            mark = 0
        field = subject_map.get(code)
        if field:
            marks_data[field] = mark
            matched_codes.append((code, field, mark))
        else:
            unknown_codes[code] = subject_text

    return {
        'roll_no': roll_no, 'name': name, 'board': board, 'father_name': father_name,
        'group': group, 'mother_name': mother_name, 'session': session, 'reg_no': reg_no,
        'type_of_result': type_of_result, 'institute': institute, 'result': result,
        'gpa_str': gpa_str, 'marks_data': marks_data, 'matched_codes': matched_codes,
        'unknown_codes': unknown_codes,
    }


PARSERS = {'hsc': parse_hsc, 'ssc': parse_ssc}


def print_record(stdout, roll, parsed, total_marks):
    stdout.write("=" * 70)
    stdout.write(f"Roll: {parsed['roll_no']}   Name: {parsed['name']}")
    stdout.write(f"Group: {parsed['group']}   Institute: {parsed['institute']}")
    stdout.write(f"GPA: {parsed['gpa_str']}   Result: {parsed['result']}")
    stdout.write("Subjects:")
    for code, field, mark in parsed['matched_codes']:
        stdout.write(f"  {code} ({field}): {mark}")
    if parsed['unknown_codes']:
        stdout.write("Unknown codes in this record:")
        for code, sample_text in parsed['unknown_codes'].items():
            stdout.write(f"  {code} - sample text: {sample_text!r}")
    stdout.write(f"Total marks (mapped only): {total_marks}")


class Command(BaseCommand):
    help = 'Scrape SSC/HSC individual results from the BISE-CTG result portal and save them.'

    def add_arguments(self, parser):
        parser.add_argument('--exam', required=True, choices=['hsc', 'ssc'], help='Exam type')
        parser.add_argument('--year', required=True, help='4-digit exam year, e.g. 2026')
        parser.add_argument('--base-url', required=True,
                             help="Base individual-result URL for this year's board site, "
                                  "e.g. https://hscresult.bise-ctg.gov.bd/h_x_y_ctg26/individual "
                                  "(no default - the board changes this path every year)")
        parser.add_argument('--roll-start', type=int, required=True)
        parser.add_argument('--roll-end', type=int, default=None,
                             help='Optional. If omitted, requires --limit and stops once --limit rolls are parsed.')
        parser.add_argument('--workers', type=int, default=5, help='Concurrent workers (default 5, hard cap 10)')
        parser.add_argument('--resume', action='store_true', help='Skip roll numbers already saved for this exam_type')
        parser.add_argument('--misses-file', type=str, default=None, help='Path to write failed/missing roll numbers (default misses_<exam>_<year>.txt)')
        parser.add_argument('--limit', type=int, default=None, help='Stop after N successfully parsed rolls')
        parser.add_argument('--print-only', action='store_true', help='Parse and print each record; write nothing to the DB')
        parser.add_argument('--force', action='store_true',
                             help='Allow scraping into an exam set whose rankings are already published '
                                  '(refused by default, so a mistyped --year cannot overwrite a live set)')

    def handle(self, *args, **options):
        exam = options['exam'].lower()
        year = options['year']
        if not year.isdigit() or len(year) != 4:
            raise CommandError(f"--year must be a 4-digit year, got {year!r}")

        try:
            subject_map = get_subject_map(exam)
        except ValueError as exc:
            raise CommandError(str(exc))

        roll_end = options['roll_end']
        limit = options['limit']
        if roll_end is None and limit is None:
            raise CommandError("Either --roll-end or --limit must be provided.")

        print_only = options['print_only']
        base_url = options['base_url'].rstrip('/')
        workers = min(max(options['workers'], 1), 10)
        exam_type = f"{exam.upper()}_{year}"
        misses_file = options['misses_file'] or f"misses_{exam}_{year}.txt"

        # Guard against a mistyped --year writing over a live exam set. --print-only
        # is exempt: it never touches the DB, so it stays usable as a pre-flight
        # check against an already-published set.
        if not print_only and not options['force']:
            if ExamSet.objects.filter(exam_type=exam_type, rankings_published=True).exists():
                raise CommandError(
                    f"Refusing to scrape into {exam_type}: its rankings are already published. "
                    f"Check --exam/--year. Pass --force only if you really mean to overwrite a live exam set."
                )

        result_url = f"{base_url}/{RESULT_ENDPOINT[exam]}"
        parse = PARSERS[exam]
        roll_start = options['roll_start']

        if roll_end is not None:
            roll_iter = iter(range(roll_start, roll_end + 1))
            total_rolls = roll_end - roll_start + 1
        else:
            roll_iter = itertools.count(roll_start)
            total_rolls = None

        existing = set()
        if options['resume']:
            existing = set(StudentInfo.objects.filter(exam_type=exam_type).values_list('roll_no', flat=True))
            self.stdout.write(f"Resume: {len(existing)} rolls already saved for {exam_type}")

        session = requests.Session()
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{base_url}/index.php",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            session.get(f"{base_url}/index.php", headers=headers, timeout=10)
        except requests.exceptions.RequestException:
            pass  # cookie warm-up is best-effort

        lock = threading.Lock()
        stats = {'processed': 0, 'saved': 0, 'missing': 0, 'failed': 0}
        misses = []
        consecutive_failures = 0
        abort = threading.Event()
        limit_reached = threading.Event()
        first_failure_html = {}
        unknown_code_counts = {}  # code -> [count, sample_text]
        first_unknown_html = {}   # code -> raw HTML of the first record it appeared in
        start_time = time.monotonic()

        def fetch_one(roll):
            if abort.is_set() or limit_reached.is_set():
                return 'skipped', roll, None

            data = {"roll": str(roll), "button2": "Submit"}
            backoff = INITIAL_BACKOFF
            response_text = None
            for attempt in range(MAX_RETRIES + 1):
                try:
                    resp = session.post(result_url, data=data, headers=headers, timeout=15)
                except requests.exceptions.RequestException:
                    if attempt >= MAX_RETRIES:
                        return 'failed', roll, None
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                if resp.status_code == 429 or resp.status_code >= 500:
                    if attempt >= MAX_RETRIES:
                        return 'failed', roll, None
                    time.sleep(backoff)
                    backoff *= 2
                    continue

                response_text = resp.text
                break

            if response_text is None:
                return 'failed', roll, None

            try:
                parsed = parse(response_text, roll, subject_map)
            except ParserDrift as exc:
                first_failure_html.setdefault(roll, str(exc) + "\n\n" + exc.html)
                return 'drift', roll, None

            if parsed is None:
                return 'missing', roll, None

            if parsed['roll_no'] != str(roll):
                first_failure_html.setdefault(roll, f"Roll mismatch: requested {roll}, got {parsed['roll_no']!r}\n\n{response_text}")
                return 'drift', roll, None

            try:
                gpa = float(parsed['gpa_str']) if parsed['gpa_str'] else 0.0
            except ValueError:
                gpa = None
            if gpa is None or not (0.0 <= gpa <= 5.0):
                first_failure_html.setdefault(roll, f"Invalid GPA {parsed['gpa_str']!r} for roll {roll}\n\n{response_text}")
                return 'drift', roll, None

            total_marks = sum(parsed['marks_data'].values())
            # Only carry the page body back when it contains an unmapped subject
            # code - that is the one case the abort path needs to show raw HTML for.
            unknown_html = response_text if parsed['unknown_codes'] else None

            if print_only:
                return 'printed', roll, (parsed, total_marks, unknown_html)

            student_info, _ = StudentInfo.objects.get_or_create(
                roll_no=parsed['roll_no'],
                exam_type=exam_type,
                defaults={
                    'name': parsed['name'], 'board': parsed['board'], 'father_name': parsed['father_name'],
                    'group': parsed['group'], 'mother_name': parsed['mother_name'], 'session': parsed['session'],
                    'reg_no': parsed['reg_no'], 'type_of_result': parsed['type_of_result'],
                    'institute': parsed['institute'], 'result': parsed['result'], 'gpa': gpa,
                },
            )
            student_info.name = parsed['name']
            student_info.board = parsed['board']
            student_info.father_name = parsed['father_name']
            student_info.group = parsed['group']
            student_info.mother_name = parsed['mother_name']
            student_info.session = parsed['session']
            student_info.reg_no = parsed['reg_no']
            student_info.type_of_result = parsed['type_of_result']
            student_info.institute = parsed['institute']
            student_info.result = parsed['result']
            student_info.gpa = gpa
            student_info.save()

            Marks.objects.update_or_create(
                student=student_info,
                defaults={**parsed['marks_data'], 'total_marks': total_marks},
            )
            return 'saved', roll, (parsed, total_marks, unknown_html)

        def next_chunk(chunk_size):
            chunk = []
            for roll in roll_iter:
                if options['resume'] and str(roll) in existing:
                    continue
                chunk.append(roll)
                if len(chunk) >= chunk_size:
                    break
            return chunk

        default_chunk_size = workers * CHUNK_SIZE_MULTIPLIER
        successes = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            while not abort.is_set() and not limit_reached.is_set():
                # Cap the chunk to what's still needed so a --limit run doesn't
                # fire a full chunk_size worth of requests past the target count.
                chunk_size = default_chunk_size
                if limit is not None:
                    chunk_size = min(chunk_size, max(limit - successes, 1))
                chunk = next_chunk(chunk_size)
                if not chunk:
                    break

                futures = {executor.submit(fetch_one, roll): roll for roll in chunk}
                for future in as_completed(futures):
                    roll = futures[future]
                    try:
                        status, _, payload = future.result()
                    except Exception as exc:
                        status, payload = 'failed', None
                        self.stderr.write(f"Unexpected error for roll {roll}: {exc}")

                    with lock:
                        if status == 'skipped':
                            continue
                        stats['processed'] += 1

                        if status in ('saved', 'printed'):
                            stats['saved'] += 1
                            consecutive_failures = 0
                            successes += 1
                            parsed, total_marks, unknown_html = payload

                            for code, sample_text in parsed['unknown_codes'].items():
                                entry = unknown_code_counts.setdefault(code, [0, sample_text])
                                entry[0] += 1
                                if unknown_html is not None:
                                    first_unknown_html.setdefault(code, unknown_html)

                            if print_only:
                                print_record(self.stdout, roll, parsed, total_marks)

                            offending = {c: v for c, v in unknown_code_counts.items() if v[0] > UNKNOWN_CODE_LIMIT}
                            if offending and not abort.is_set():
                                abort.set()
                                self.stderr.write(self.style.ERROR(
                                    "\nAborting: the following subject code(s) appeared more than "
                                    f"{UNKNOWN_CODE_LIMIT} times and are not in the subject map:\n"
                                ))
                                for code, (count, sample_text) in offending.items():
                                    self.stderr.write(f"  code {code}: seen {count} times, sample text {sample_text!r}")
                                self.stderr.write("Update Rankings/subject_maps.py with these codes before continuing.")
                                for code in offending:
                                    html = first_unknown_html.get(code)
                                    if html:
                                        self.stderr.write(f"\nRaw HTML of the first record containing code {code}:\n")
                                        self.stderr.write(html)

                            if limit is not None and successes >= limit:
                                limit_reached.set()

                        elif status == 'missing':
                            stats['missing'] += 1
                            misses.append(roll)
                            consecutive_failures = 0
                        elif status in ('failed', 'drift'):
                            stats['failed'] += 1
                            misses.append(roll)
                            consecutive_failures += 1
                            if consecutive_failures > CONSECUTIVE_FAILURE_LIMIT and not abort.is_set():
                                abort.set()
                                self.stderr.write(self.style.ERROR(
                                    f"\nAborting: {consecutive_failures} consecutive failures. "
                                    f"The board likely changed its page format.\n"
                                    f"Raw HTML of the first failure:\n"
                                ))
                                first_roll = next(iter(first_failure_html))
                                self.stderr.write(first_failure_html[first_roll])

                        if not print_only and stats['processed'] % 500 == 0:
                            elapsed = time.monotonic() - start_time
                            rate = stats['processed'] / elapsed if elapsed > 0 else 0
                            remaining = (total_rolls - stats['processed']) if total_rolls else None
                            eta = (remaining / rate) if (rate > 0 and remaining is not None) else float('inf')
                            self.stdout.write(
                                f"processed={stats['processed']} saved={stats['saved']} "
                                f"missing={stats['missing']} failed={stats['failed']} "
                                f"elapsed={elapsed:.0f}s eta={eta:.0f}s"
                            )

                    if abort.is_set() or limit_reached.is_set():
                        break

        if unknown_code_counts:
            self.stdout.write("\nUnknown subject codes seen this run:")
            for code, (count, sample_text) in sorted(unknown_code_counts.items(), key=lambda kv: -kv[1][0]):
                self.stdout.write(f"  {code}: {count} occurrence(s), sample text {sample_text!r}")

        if misses and not print_only:
            with open(misses_file, 'w') as f:
                for roll in misses:
                    f.write(f"{roll}\n")
            self.stdout.write(f"Wrote {len(misses)} missing/failed rolls to {misses_file}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. processed={stats['processed']} saved={stats['saved']} "
            f"missing={stats['missing']} failed={stats['failed']}"
        ))

        if abort.is_set():
            raise CommandError("Aborted - see output above (either too many consecutive parser failures, or an unmapped subject code appeared too often).")

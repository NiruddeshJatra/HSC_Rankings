"""Condense `scrape_results --print-only` output into a phone-readable digest.

The raw print-only log is ~12 lines per record; on a phone that is 240 lines to
scroll through. This prints one line per record plus an explicit warning list,
so the pre-flight check can actually be read on the device it is run from.

Usage: python .github/scripts/sample_digest.py <log-path>
"""

import re
import sys

FIELD_SPLIT = re.compile(r'\s{2,}')
SUBJECT_LINE = re.compile(r'^\s{2}\S+ \(\w+\): -?\d+$')


def fields(line):
    """`Roll: 1   Name: X` -> {'Roll': '1', 'Name': 'X'}"""
    out = {}
    for part in FIELD_SPLIT.split(line):
        key, sep, value = part.partition(': ')
        if sep:
            out[key.strip()] = value.strip()
    return out


def parse(lines):
    records = []
    current = None
    in_unknown = False
    for line in lines:
        line = line.rstrip('\n')
        if line.startswith('Roll: '):
            in_unknown = False
            current = {'subjects': 0, 'unknown': [], 'roll': '', 'name': '',
                       'gpa': '', 'result': '', 'total': '', 'group': ''}
            records.append(current)
            got = fields(line)
            current['roll'] = got.get('Roll', '')
            current['name'] = got.get('Name', '')
            continue
        if current is None:
            continue
        if line.startswith('Unknown codes in this record:'):
            in_unknown = True
        elif in_unknown and line.startswith('  '):
            current['unknown'].append(line.strip())
        elif line.startswith('Group: '):
            current['group'] = fields(line).get('Group', '')
        elif line.startswith('GPA: '):
            got = fields(line)
            current['gpa'] = got.get('GPA', '')
            current['result'] = got.get('Result', '')
        elif line.startswith('Total marks'):
            in_unknown = False
            current['total'] = line.split(':')[-1].strip()
        elif SUBJECT_LINE.match(line):
            current['subjects'] += 1
    return records


def main():
    with open(sys.argv[1], encoding='utf-8', errors='replace') as f:
        records = parse(f)

    if not records:
        print('No records parsed — see the raw log below.')
        return

    warnings = []
    for r in records:
        try:
            gpa = float(r['gpa'])
        except ValueError:
            gpa = None
        if gpa is None or not (0.0 <= gpa <= 5.0):
            warnings.append(f"roll {r['roll']}: GPA {r['gpa']!r} is not a number in 0–5")
        if not r['name']:
            warnings.append(f"roll {r['roll']}: name is blank")
        if not r['result']:
            warnings.append(f"roll {r['roll']}: result status is blank")
        if r['subjects'] == 0:
            warnings.append(f"roll {r['roll']}: no subject marks parsed")
        for u in r['unknown']:
            warnings.append(f"roll {r['roll']}: unknown subject code — {u}")

    groups = sorted({r['group'] for r in records if r['group']})
    print(f"{len(records)} records parsed · group(s): {', '.join(groups) or 'unknown'}")
    print()
    for r in records:
        print(f"- `{r['roll']}` GPA {r['gpa'] or '?'} · {r['result'] or 'NO RESULT'} · "
              f"total {r['total'] or '?'} · {r['subjects']} subj — {r['name'] or 'NO NAME'}")
    print()
    if warnings:
        print(f"**{len(warnings)} warning(s) — do not run mode = full:**")
        print()
        for w in warnings:
            print(f"- {w}")
    else:
        print("No blank names, no out-of-range GPAs, no unknown subject codes, "
              "no empty result statuses. Still eyeball the rolls and marks above.")


if __name__ == '__main__':
    main()

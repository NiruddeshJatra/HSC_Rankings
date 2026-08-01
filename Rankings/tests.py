from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from Rankings.management.commands.rank_students import compute_competition_ranks
from Rankings.management.commands.verify_examset import SUBJECT_FIELDS, nonzero_subject_marks_q
from Rankings.models import ExamSet, Marks, StudentInfo
from Rankings.subject_maxes import subject_max


class CompetitionRankingTests(TestCase):
    def test_ties_share_rank_and_skip_correctly(self):
        scores = [500, 480, 480, 470]
        self.assertEqual(compute_competition_ranks(scores), [1, 2, 2, 4])

    def test_no_ties(self):
        scores = [100, 90, 80]
        self.assertEqual(compute_competition_ranks(scores), [1, 2, 3])

    def test_all_tied(self):
        scores = [50, 50, 50]
        self.assertEqual(compute_competition_ranks(scores), [1, 1, 1])


def make_student(roll, total, exam_type='SSC_2026', group='SCIENCE', **marks):
    student = StudentInfo.objects.create(
        roll_no=str(roll), name=f'Student {roll}', group=group,
        exam_type=exam_type, result='PASS', gpa='5.00',
    )
    Marks.objects.create(student=student, total_marks=total, **marks)
    return student


class RankStudentsIdempotenceTests(TestCase):
    """WS11.4: re-running rank_students mid-scrape must not corrupt partial data."""

    def test_rerunning_produces_identical_ranks(self):
        for roll, total in ((1001, 1200), (1002, 1100), (1003, 1100), (1004, 900)):
            make_student(roll, total)

        call_command('rank_students', exam_type='SSC_2026', group='all')
        first = dict(StudentInfo.objects.values_list('roll_no', 'rank'))

        call_command('rank_students', exam_type='SSC_2026', group='all')
        second = dict(StudentInfo.objects.values_list('roll_no', 'rank'))

        self.assertEqual(first, {'1001': 1, '1002': 2, '1003': 2, '1004': 4})
        self.assertEqual(first, second)

    def test_ranking_partial_then_full_set_is_correct(self):
        make_student(1001, 1100)
        make_student(1002, 900)
        call_command('rank_students', exam_type='SSC_2026', group='all')

        # A higher scorer arrives later in the scrape; re-ranking must reorder,
        # not append.
        make_student(1003, 1250)
        call_command('rank_students', exam_type='SSC_2026', group='all')

        self.assertEqual(
            dict(StudentInfo.objects.values_list('roll_no', 'rank')),
            {'1003': 1, '1001': 2, '1002': 3},
        )


class VerifyExamsetTests(TestCase):
    def test_fails_on_zero_total_with_nonzero_subject_marks(self):
        make_student(1001, 1200, bangla=180)
        make_student(1002, 0, bangla=170)  # the HSC_2024 defect
        call_command('rank_students', exam_type='SSC_2026', group='all')

        with self.assertRaises(CommandError):
            call_command('verify_examset', exam_type='SSC_2026')

    def test_fails_on_blank_result(self):
        student = make_student(1001, 1200, bangla=180)
        StudentInfo.objects.filter(pk=student.pk).update(result='')
        call_command('rank_students', exam_type='SSC_2026', group='all')

        with self.assertRaises(CommandError):
            call_command('verify_examset', exam_type='SSC_2026')

    def test_genuine_zero_total_rows_pass(self):
        # A candidate who scored nothing has total_marks == 0 AND no subject
        # marks. That is not the defect and must not fail verification — the
        # published sets have hundreds of these rows.
        make_student(1001, 1200, bangla=180)
        make_student(1002, 0)
        call_command('rank_students', exam_type='SSC_2026', group='all')

        call_command('verify_examset', exam_type='SSC_2026')  # must not raise

    def test_passes_on_clean_data(self):
        make_student(1001, 1200, bangla=180)
        make_student(1002, 1100, bangla=170)
        call_command('rank_students', exam_type='SSC_2026', group='all')

        call_command('verify_examset', exam_type='SSC_2026')  # must not raise


class SubjectFieldsTests(TestCase):
    """Pin the integer columns verify_examset treats as subject marks.

    This is a tripwire, not a second source of truth: adding a subject to Marks
    fails this test, and the fix is to add the name here. Adding an integer
    column that is NOT a subject mark also fails it, and the fix is to add the
    name to NON_SUBJECT_INT_FIELDS instead — which is the case that would
    otherwise silently corrupt the zero-total check.
    """

    EXPECTED = {
        'bangla', 'english', 'math', 'physics', 'chemistry', 'biology',
        'higher_math', 'ict', 'islam_moral', 'hindu_moral', 'buddha_moral',
        'christian_moral', 'bangladesh_world', 'agriculture', 'home_science',
        'finance_banking', 'accounting', 'business_ent', 'general_science',
        'music', 'geography', 'civics', 'economics', 'history_bd', 'statistics',
        'management', 'finance', 'production', 'logic', 'history',
        'islamic_history', 'social_work', 'sociology', 'physical_education',
        'career_education',
    }

    def test_subject_fields_match_expected(self):
        self.assertEqual(set(SUBJECT_FIELDS), self.EXPECTED)

    def test_total_marks_is_not_treated_as_a_subject(self):
        self.assertNotIn('total_marks', SUBJECT_FIELDS)

    def test_nonzero_subject_marks_q_is_not_a_tautology(self):
        # Q() is falsy, so `Q() | Q(cond)` collapses to `Q(cond)` rather than
        # matching everything. Locking that in: a row with no subject marks
        # must not match.
        zero = make_student(1001, 0)
        scored = make_student(1002, 180, bangla=180)

        matched = set(
            StudentInfo.objects.filter(nonzero_subject_marks_q())
            .values_list('roll_no', flat=True)
        )
        self.assertEqual(matched, {scored.roll_no})
        self.assertNotIn(zero.roll_no, matched)


class ScrapeGuardTests(TestCase):
    def test_refuses_to_scrape_into_a_published_exam_set(self):
        ExamSet.objects.create(exam_type='SSC_2025', label='SSC 2025', rankings_published=True)

        with self.assertRaises(CommandError):
            call_command(
                'scrape_results', exam='ssc', year='2025',
                base_url='https://example.invalid/x', roll_start=1, limit=1,
            )


class FixtureModeTests(TestCase):
    """`--fixture-dir` must drive the same pipeline the HTTP path does.

    Also pins what the fixtures contain: the rehearsal is only worth running if
    the deliberately broken pages are still broken.
    """

    FIXTURES = Path(settings.BASE_DIR) / '.github' / 'fixtures'

    def scrape(self, **kwargs):
        out = StringIO()
        call_command(
            'scrape_results', exam='ssc', year='2025',
            fixture_dir=str(self.FIXTURES),
            roll_start=300001, roll_end=300020,
            print_only=True, workers=1, stdout=out, stderr=out, **kwargs,
        )
        return out.getvalue()

    def test_parses_every_fixture_without_http(self):
        output = self.scrape()
        self.assertIn('Done. processed=20 saved=20 missing=0 failed=0', output)

    def test_unknown_subject_code_is_reported(self):
        output = self.scrape()
        self.assertIn('Unknown subject codes seen this run:', output)
        self.assertIn('999', output)

    def test_blank_result_fixture_still_parses(self):
        # It must reach the digest as a record with an empty result, not be
        # silently dropped — that is what makes it a useful warning case.
        output = self.scrape()
        self.assertIn('Roll: 300018', output)

    def test_missing_fixture_counts_as_missing(self):
        out = StringIO()
        call_command(
            'scrape_results', exam='ssc', year='2025',
            fixture_dir=str(self.FIXTURES),
            roll_start=399001, roll_end=399005,
            print_only=True, workers=1, stdout=out, stderr=out,
        )
        self.assertIn('missing=5', out.getvalue())

    def test_base_url_not_required_with_fixture_dir(self):
        self.scrape()  # no base_url passed anywhere above

    def test_base_url_still_required_without_fixture_dir(self):
        with self.assertRaises(CommandError):
            call_command('scrape_results', exam='ssc', year='2025',
                         roll_start=1, limit=1, print_only=True)

    def test_bad_fixture_dir_is_rejected(self):
        with self.assertRaises(CommandError):
            call_command('scrape_results', exam='ssc', year='2025',
                         fixture_dir=str(self.FIXTURES / 'nope'),
                         roll_start=1, limit=1, print_only=True)


class SubjectMaxTests(TestCase):
    """WS11.5: SSC_2026 must resolve by exam-level prefix, with no per-year code."""

    SSC_SCIENCE_SUBJECTS = [
        'bangla', 'english', 'math', 'physics', 'chemistry', 'biology',
        'higher_math', 'ict', 'islam_moral', 'bangladesh_world',
        'career_education', 'physical_education',
    ]

    def test_ssc_2026_totals_1300(self):
        total = sum(subject_max('SSC_2026', f) for f in self.SSC_SCIENCE_SUBJECTS)
        self.assertEqual(total, 1300)

    def test_ssc_2026_individual_maxes(self):
        self.assertEqual(subject_max('SSC_2026', 'bangla'), 200)
        self.assertEqual(subject_max('SSC_2026', 'english'), 200)
        self.assertEqual(subject_max('SSC_2026', 'ict'), 50)
        self.assertEqual(subject_max('SSC_2026', 'career_education'), 50)
        self.assertEqual(subject_max('SSC_2026', 'physics'), 100)

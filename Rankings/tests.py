from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from Rankings.management.commands.rank_students import compute_competition_ranks
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

    def test_passes_on_clean_data(self):
        make_student(1001, 1200, bangla=180)
        make_student(1002, 1100, bangla=170)
        call_command('rank_students', exam_type='SSC_2026', group='all')

        call_command('verify_examset', exam_type='SSC_2026')  # must not raise


class ScrapeGuardTests(TestCase):
    def test_refuses_to_scrape_into_a_published_exam_set(self):
        ExamSet.objects.create(exam_type='SSC_2025', label='SSC 2025', rankings_published=True)

        with self.assertRaises(CommandError):
            call_command(
                'scrape_results', exam='ssc', year='2025',
                base_url='https://example.invalid/x', roll_start=1, limit=1,
            )


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

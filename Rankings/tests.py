from django.test import TestCase

from Rankings.management.commands.rank_students import compute_competition_ranks


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

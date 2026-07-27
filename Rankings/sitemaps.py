from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import StudentInfo, ExamSet

GROUPS = ['science', 'business_studies', 'humanities']


class StaticSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 1.0

    def items(self):
        return ['rankings:home', 'rankings:methodology']

    def location(self, item):
        return reverse(item)


class GroupSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.9

    def items(self):
        published_exam_types = set(
            ExamSet.objects.filter(rankings_published=True).values_list('exam_type', flat=True)
        )
        combos = []
        for exam_type in StudentInfo.objects.values_list('exam_type', flat=True).distinct():
            if exam_type not in published_exam_types:
                continue
            exam, _, year = exam_type.partition('_')
            if not year:
                continue
            for group in GROUPS:
                combos.append((exam.lower(), year, group))
        return combos

    def location(self, item):
        exam, year, group = item
        return reverse('rankings:results', kwargs={'exam': exam, 'year': year, 'group': group})

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from Rankings.models import StudentInfo, Marks

BATCH_SIZE = 2000


class Command(BaseCommand):
    help = 'Transfer StudentInfo/Marks data from the legacy SQLite database to the configured Postgres database'

    def add_arguments(self, parser):
        parser.add_argument('--exam-type', type=str, default=None, help='Only transfer this exam_type (e.g. SSC_2026). Default: all.')
        parser.add_argument('--dry-run', action='store_true', help='Print source/destination row counts and exit without writing.')

    def _counts(self, exam_type):
        src_students = StudentInfo.objects.using('LEGACY_SQLITE')
        dst_students = StudentInfo.objects.using('default')
        src_marks = Marks.objects.using('LEGACY_SQLITE')
        dst_marks = Marks.objects.using('default')
        if exam_type:
            src_students = src_students.filter(exam_type=exam_type)
            dst_students = dst_students.filter(exam_type=exam_type)
            src_marks = src_marks.filter(student__exam_type=exam_type)
            dst_marks = dst_marks.filter(student__exam_type=exam_type)
        return src_students.count(), dst_students.count(), src_marks.count(), dst_marks.count()

    def handle(self, *args, **options):
        exam_type = options['exam_type']
        dry_run = options['dry_run']

        src_student_count, dst_student_count, src_marks_count, dst_marks_count = self._counts(exam_type)
        self.stdout.write(f"Source StudentInfo: {src_student_count}, Destination StudentInfo: {dst_student_count}")
        self.stdout.write(f"Source Marks: {src_marks_count}, Destination Marks: {dst_marks_count}")

        if dry_run:
            return

        students_qs = StudentInfo.objects.using('LEGACY_SQLITE')
        if exam_type:
            students_qs = students_qs.filter(exam_type=exam_type)

        transferred_students = 0
        transferred_marks = 0
        batch = []
        for student in students_qs.iterator(chunk_size=BATCH_SIZE):
            batch.append(StudentInfo(
                roll_no=student.roll_no,
                name=student.name,
                board=student.board,
                father_name=student.father_name,
                group=student.group,
                mother_name=student.mother_name,
                session=student.session,
                reg_no=student.reg_no,
                type_of_result=student.type_of_result,
                institute=student.institute,
                result=student.result,
                gpa=student.gpa,
                rank=student.rank,
                exam_type=student.exam_type,
            ))
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic(using='default'):
                    StudentInfo.objects.using('default').bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=False)
                transferred_students += len(batch)
                self.stdout.write(f"  ...{transferred_students} StudentInfo rows transferred")
                batch = []
        if batch:
            with transaction.atomic(using='default'):
                StudentInfo.objects.using('default').bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=False)
            transferred_students += len(batch)

        # Map (roll_no, exam_type) -> new student id, needed to attach Marks to the newly created rows.
        dst_lookup = {}
        dst_qs = StudentInfo.objects.using('default').all()
        if exam_type:
            dst_qs = dst_qs.filter(exam_type=exam_type)
        for sid, roll_no, et in dst_qs.values_list('id', 'roll_no', 'exam_type'):
            dst_lookup[(roll_no, et)] = sid

        marks_qs = Marks.objects.using('LEGACY_SQLITE').select_related('student')
        if exam_type:
            marks_qs = marks_qs.filter(student__exam_type=exam_type)

        marks_fields = [f.name for f in Marks._meta.get_fields() if f.name not in ('id', 'student')]

        batch = []
        for mark in marks_qs.iterator(chunk_size=BATCH_SIZE):
            dst_id = dst_lookup.get((mark.student.roll_no, mark.student.exam_type))
            if dst_id is None:
                continue
            kwargs = {field: getattr(mark, field) for field in marks_fields}
            kwargs['student_id'] = dst_id
            batch.append(Marks(**kwargs))
            if len(batch) >= BATCH_SIZE:
                with transaction.atomic(using='default'):
                    Marks.objects.using('default').bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=False)
                transferred_marks += len(batch)
                self.stdout.write(f"  ...{transferred_marks} Marks rows transferred")
                batch = []
        if batch:
            with transaction.atomic(using='default'):
                Marks.objects.using('default').bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=False)
            transferred_marks += len(batch)

        final_src_student, final_dst_student, final_src_marks, final_dst_marks = self._counts(exam_type)
        self.stdout.write(self.style.SUCCESS(
            f"StudentInfo -> source: {final_src_student}, destination: {final_dst_student}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"Marks -> source: {final_src_marks}, destination: {final_dst_marks}"
        ))

        if final_src_student != final_dst_student or final_src_marks != final_dst_marks:
            raise CommandError(
                f"Row count mismatch after transfer: "
                f"StudentInfo src={final_src_student} dst={final_dst_student}, "
                f"Marks src={final_src_marks} dst={final_dst_marks}"
            )

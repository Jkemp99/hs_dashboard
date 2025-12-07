from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Student(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='students', default=1)
    GRADE_CHOICES = [
        ('Kindergarten', 'Kindergarten'),
        ('1st Grade', '1st Grade'),
        ('2nd Grade', '2nd Grade'),
        ('3rd Grade', '3rd Grade'),
        ('4th Grade', '4th Grade'),
        ('5th Grade', '5th Grade'),
        ('6th Grade', '6th Grade'),
        ('7th Grade', '7th Grade'),
        ('8th Grade', '8th Grade'),
        ('9th Grade', '9th Grade'),
        ('10th Grade', '10th Grade'),
        ('11th Grade', '11th Grade'),
        ('12th Grade', '12th Grade'),
        ('Other', 'Custom'),
    ]

    name = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=50, choices=GRADE_CHOICES, default='1st Grade')
    custom_grade_level = models.CharField(max_length=50, blank=True, null=True, help_text="Enter grade if 'Other' is selected")
    
    TRACKING_MODES = [
        ('attendance', 'Attendance Only'),
        ('subjects', 'Subjects'),
    ]
    tracking_mode = models.CharField(max_length=20, choices=TRACKING_MODES, default='attendance')

    academic_year_start_month = models.PositiveSmallIntegerField(default=8, help_text="Start month (1-12)")
    academic_year_end_month = models.PositiveSmallIntegerField(default=7, help_text="End month (1-12)")

    def __str__(self):
        if self.grade_level == 'Other' and self.custom_grade_level:
            return f"{self.name} ({self.custom_grade_level})"
        return f"{self.name} ({self.grade_level})"

    @property
    def is_other_grade(self):
        return self.grade_level == 'Other'

    @property
    def is_subject_tracking(self):
        return self.tracking_mode == 'subjects'

class Subject(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return f"{self.name} ({self.student.name})"

class SchoolDay(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='school_days')
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    subjects = models.ManyToManyField(Subject, blank=True, related_name='school_days')
    subjects_completed = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.name} - {self.date}"

    class Meta:
        unique_together = ['student', 'date']

class WorkSample(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='work_samples')
    subject = models.CharField(max_length=100)
    date_uploaded = models.DateField(default=timezone.now)
    file = models.FileField(upload_to='samples/')
    
    def __str__(self):
        return f"{self.subject} - {self.student.name} ({self.date_uploaded})"

    @property
    def is_pdf(self):
        return self.file.name.lower().endswith('.pdf')

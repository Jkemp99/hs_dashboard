from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Association(models.Model):
    name = models.CharField(max_length=200)
    director_name = models.CharField(max_length=100)
    required_days = models.PositiveIntegerField(default=180)
    logo = models.ImageField(upload_to='association_logos/', blank=True, null=True)

    def __str__(self):
        return self.name

class FamilyProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    association = models.ForeignKey(Association, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        FamilyProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

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
    
    academic_year_start_month = models.PositiveSmallIntegerField(default=8, help_text="Start month (1-12)")
    academic_year_end_month = models.PositiveSmallIntegerField(default=7, help_text="End month (1-12)")
    
    GRADING_SYSTEM_CHOICES = [
        ('quarters', 'Quarters'),
        ('semesters', 'Semesters'),
    ]
    grading_system = models.CharField(max_length=20, choices=GRADING_SYSTEM_CHOICES, default='quarters')

    def __str__(self):
        if self.grade_level == 'Other' and self.custom_grade_level:
            return f"{self.name} ({self.custom_grade_level})"
        return f"{self.name} ({self.grade_level})"

    @property
    def is_other_grade(self):
        return self.grade_level == 'Other'

    @property
    def is_subject_tracking(self):
        """All students now track subjects by default."""
        return True

    @property
    def display_grade(self):
        if self.grade_level == 'Other' and self.custom_grade_level:
            return self.custom_grade_level
        return self.grade_level

class GlobalSubject(models.Model):
    """Standardized subjects shared across all students for consistent reporting."""
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class Subject(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subjects')
    global_subject = models.ForeignKey(GlobalSubject, on_delete=models.PROTECT, null=True, blank=True)
    name = models.CharField(max_length=100, blank=True, null=True)
    
    @property
    def display_name(self):
        """Returns the global subject name if linked, otherwise the custom name."""
        if self.global_subject:
            return self.global_subject.name
        return self.name
    
    def __str__(self):
        return f"{self.display_name} ({self.student.name})"

class SchoolDay(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='school_days')
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)

    subjects = models.ManyToManyField(Subject, blank=True, related_name='school_days')
    # subjects_completed removed
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

class Grade(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grades')
    term = models.CharField(max_length=2, choices=[
        ('Q1', 'Q1'), ('Q2', 'Q2'), ('Q3', 'Q3'), ('Q4', 'Q4'),
        ('S1', 'Semester 1'), ('S2', 'Semester 2')
    ])
    score = models.CharField(max_length=5)

    class Meta:
        unique_together = ['student', 'subject', 'term']

    def __str__(self):
        return f"{self.student.name} - {self.subject.name} - {self.term}: {self.score}"

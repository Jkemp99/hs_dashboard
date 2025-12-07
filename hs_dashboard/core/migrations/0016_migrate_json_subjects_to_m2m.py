from django.db import migrations

def migrate_subjects_forward(apps, schema_editor):
    SchoolDay = apps.get_model('core', 'SchoolDay')
    Subject = apps.get_model('core', 'Subject')
    
    for day in SchoolDay.objects.all():
        if day.subjects_completed:
            # It's a list of strings
            for subject_name in day.subjects_completed:
                if subject_name and isinstance(subject_name, str): # Verify it's a string and not empty
                    subject, created = Subject.objects.get_or_create(
                        student=day.student,
                        name=subject_name
                    )
                    day.subjects.add(subject)

def migrate_subjects_reverse(apps, schema_editor):
    # Optional: Logic to move back M2M to JSON if needed, but primary goal is forward
    # Just passing implementation for now as we are removing JSON field locally anyway
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_remove_student_association'),
    ]

    operations = [
        migrations.RunPython(migrate_subjects_forward, migrate_subjects_reverse),
    ]

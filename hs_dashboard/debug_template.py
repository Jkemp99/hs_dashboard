
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.template import loader, Context
from django.conf import settings
from django.contrib.auth.models import User
from django.test import RequestFactory
from django.middleware.csrf import get_token

def debug_template():
    from core.models import Student, FamilyProfile
    
    # Mock user and request
    try:
        user = User.objects.first()
        if not user:
            print("No user found.")
            return
            
        request = RequestFactory().get('/settings/')
        request.user = user
        
        # Add CSRF token
        csrf_token = get_token(request)
        
        # Context mimics settings_view but simplified
        context = {
            'user': user,
            'students': Student.objects.filter(user=user),
            'grade_choices': Student.GRADE_CHOICES,
            'csrf_token': csrf_token,
            # Add other necessary context keys if needed
            'associations': [],
            'global_subjects': [],
            'calendar_weeks': [],
        }
        
        print("Rendering core/partials/student_list.html...")
        try:
            t = loader.get_template('core/partials/student_list.html')
            t.render(context, request)
            print("✓ partials/student_list.html rendered successfully.")
        except Exception as e:
            print(f"✗ Error rendering partials/student_list.html: {e}")

        print("\nRendering core/settings.html...")
        try:
            t = loader.get_template('core/settings.html')
            t.render(context, request)
            print("✓ settings.html rendered successfully.")
        except Exception as e:
            print(f"✗ Error rendering settings.html: {e}")
            
    except Exception as e:
        print(f"Setup error: {e}")

if __name__ == "__main__":
    debug_template()

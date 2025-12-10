from django import template

register = template.Library()

@register.filter
def eq(value, arg):
    """
    Returns True if value == arg, False otherwise.
    Usage: {% if value|eq:arg %}...{% endif %}
    """
    return value == arg

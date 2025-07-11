from django import template

register = template.Library()

@register.filter
def get_field(obj, attr):
    value = getattr(obj, attr, 0)
    return value if value is not None else 0 
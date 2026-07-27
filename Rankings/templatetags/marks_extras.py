from django import template

register = template.Library()

@register.filter
def stagger_class(index):
    """Row entrance stagger: delay = min(index * 45ms, 500ms), as a CSS class
    (no inline style attributes) — see .stagger-N in site.css."""
    return f"stagger-{min(index, 11)}"

@register.filter
def subject_stagger_class(index):
    """Subject bar entrance stagger: delay = index * 60ms, as a CSS class."""
    return f"substagger-{min(index, 9)}"

@register.filter
def bar_class(pct):
    """Progress bar width, rounded to the nearest 5%, as a CSS class."""
    bucket = min(max(int(round(pct / 5.0) * 5), 0), 100)
    return f"bar-{bucket}"

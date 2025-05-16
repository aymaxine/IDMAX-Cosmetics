from django import template

register = template.Library()

@register.filter
def dictget(dictionary, key):
    """
    Get a value from a dictionary by key.
    Usage: {{ dictionary|dictget:key }}
    """
    if dictionary is None:
        return None

    # Convert key to string if it's not already
    str_key = str(key)

    # Try to get the value from the dictionary
    return dictionary.get(str_key, None)

@register.filter
def attr(obj, attr_name):
    """
    Get an attribute from an object.
    Usage: {{ object|attr:attribute_name }}
    """
    if obj is None:
        return ''

    # Try to get the attribute from the object
    try:
        # First try as a dictionary key
        if isinstance(obj, dict):
            return obj.get(attr_name, '')
        # Then try as an object attribute
        return getattr(obj, attr_name, '')
    except (TypeError, AttributeError):
        return ''

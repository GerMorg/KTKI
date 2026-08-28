import re
from decimal import Decimal, InvalidOperation

_NUMERIC = re.compile(r'^[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?$')

def display_number(value, decimals=None):
    """Compact German display formatting without changing persisted values."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text=value.strip()
        if not _NUMERIC.match(text) or len(text)>40:
            return value
    try:
        number=Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    if not number.is_finite():
        return str(value)
    absolute=abs(number)
    places = decimals if decimals is not None else (8 if absolute and absolute < Decimal('0.01') else 4 if absolute < 1 else 2)
    text=f'{number:.{places}f}'.rstrip('0').rstrip('.')
    if text in ('-0',''):
        text='0'
    return text.replace('.', ',')

def display_tree(value):
    if isinstance(value, dict):
        return {k:display_tree(v) for k,v in value.items()}
    if isinstance(value, list):
        return [display_tree(v) for v in value]
    if isinstance(value, tuple):
        return tuple(display_tree(v) for v in value)
    return display_number(value)

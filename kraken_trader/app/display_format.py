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
        text = value.strip()
        if not _NUMERIC.match(text) or len(text) > 40:
            return value
    try:
        number = Decimal(str(float(value) if isinstance(value, DisplayFloat) else value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    if not number.is_finite():
        return str(value)
    absolute = abs(number)
    places = decimals if decimals is not None else (8 if absolute and absolute < Decimal('0.01') else 4 if absolute < 1 else 2)
    text = f'{number:.{places}f}'.rstrip('0').rstrip('.')
    if text in ('-0', ''):
        text = '0'
    return text.replace('.', ',')


class DisplayFloat(float):
    """Numeric template value that stays calculable but renders compactly.

    v54 converted numbers to localized strings before Jinja evaluated filters and
    arithmetic. Values such as ``0,1375`` then became ``0`` through Jinja's
    ``float`` filter. This float subclass preserves numeric semantics while its
    normal string representation keeps the compact German display format.
    """

    def __new__(cls, value):
        return super().__new__(cls, float(value))

    def __str__(self):
        return display_number(float(self))

    def __repr__(self):
        return str(self)


def display_tree(value):
    """Prepare template values without destroying their numeric semantics."""
    if isinstance(value, dict):
        return {k: display_tree(v) for k, v in value.items()}
    if isinstance(value, list):
        return [display_tree(v) for v in value]
    if isinstance(value, tuple):
        return tuple(display_tree(v) for v in value)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        return DisplayFloat(value)
    if isinstance(value, Decimal):
        return DisplayFloat(value)
    if isinstance(value, str):
        text = value.strip()
        if _NUMERIC.match(text) and len(text) <= 40:
            try:
                return DisplayFloat(text)
            except ValueError:
                pass
    return value

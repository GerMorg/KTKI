from decimal import Decimal, InvalidOperation
import re

_NUMERIC_TEXT = re.compile(r'^[-+]?\d+(?:\.\d+)?$')


def display_number(value, decimals=None):
    """Compact German number formatting without altering numeric semantics."""
    if value is None or isinstance(value, bool):
        return value
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return value
    if not number.is_finite():
        return str(value)
    absolute = abs(number)
    if decimals is None:
        if absolute == 0:
            places = 0
        elif absolute >= Decimal('1'):
            places = 2
        elif absolute >= Decimal('0.1'):
            places = 3
        elif absolute >= Decimal('0.01'):
            places = 4
        elif absolute >= Decimal('0.001'):
            places = 5
        else:
            places = 6
    else:
        places = max(0, int(decimals))
    text = f'{number:.{places}f}'.rstrip('0').rstrip('.')
    if text in ('-0', ''):
        text = '0'
    return text.replace('.', ',')


class DisplayFloat(float):
    """Numeric template value that keeps arithmetic semantics and localized output."""
    def __new__(cls, value):
        return super().__new__(cls, float(value))
    def __str__(self):
        return display_number(float(self))
    def __repr__(self):
        return str(self)


class DisplayNumberText(str):
    """Numeric database text with compact presentation but unchanged numeric value."""
    def __new__(cls, value):
        return super().__new__(cls, value)
    def __str__(self):
        return display_number(super().__str__())
    def __repr__(self):
        return str(self)


def display_tree(value):
    """Format display-only numeric strings while preserving arbitrary text/JSON."""
    if isinstance(value, dict):
        return {key: display_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [display_tree(item) for item in value]
    if isinstance(value, tuple):
        return tuple(display_tree(item) for item in value)
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, float):
        return DisplayFloat(value)
    if isinstance(value, Decimal):
        return DisplayFloat(value)
    if isinstance(value, str) and _NUMERIC_TEXT.fullmatch(value.strip()):
        text = value.strip()
        if '.' in text and len(text.rsplit('.', 1)[1]) > 2:
            return DisplayNumberText(text)
    return value

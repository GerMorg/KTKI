from decimal import Decimal, InvalidOperation


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
    places = decimals if decimals is not None else (
        8 if absolute and absolute < Decimal('0.01')
        else 4 if absolute < 1
        else 2
    )
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


def display_tree(value):
    """Localize actual numeric values while preserving raw database/JSON strings."""
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
    return value

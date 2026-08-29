from decimal import Decimal, InvalidOperation


def display_number(value, decimals=None):
    """Compact German display formatting without changing persisted values."""
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
    """A numeric template value that remains arithmetic-safe but displays localized."""

    def __new__(cls, value):
        return super().__new__(cls, float(value))

    def __str__(self):
        return display_number(float(self))

    def __repr__(self):
        return str(self)


def display_tree(value):
    """Localize numeric runtime values while preserving numeric semantics and raw strings."""
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
    # Keep database text and JSON text byte-for-byte/character-for-character intact.
    return value

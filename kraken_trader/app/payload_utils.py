"""Defensive normalization helpers for external and legacy payloads."""

def as_mapping(value, default=None):
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        mappings = [x for x in value if isinstance(x, dict)]
        if len(mappings) == 1:
            return mappings[0]
        return dict(default or {'status': 'COMPLETED', 'items': mappings})
    if value is None:
        return dict(default or {'status': 'COMPLETED'})
    return {'status': 'COMPLETED', 'value': value}


def as_mapping_list(value):
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, dict):
                out.append(item)
            elif isinstance(item, list):
                out.extend(x for x in item if isinstance(x, dict))
        return out
    return []


def as_pair_mapping(value):
    """Normalize Kraken AssetPairs-style results to a mapping.

    A malformed/list response must never be tuple-unpacked as ``source, pair``.
    """
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        out = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            key = item.get('wsname') or item.get('altname') or item.get('symbol') or item.get('pair')
            if key:
                out[str(key)] = item
        return out
    return {}

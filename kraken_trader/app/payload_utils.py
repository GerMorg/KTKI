"""Defensive normalization helpers for external and legacy payloads."""
from collections.abc import Mapping


def _mapping_like(value):
    if isinstance(value, Mapping):
        return dict(value)
    try:
        keys = value.keys()
    except AttributeError:
        return None
    try:
        return {key: value[key] for key in keys}
    except Exception:
        return None


def as_mapping(value, default=None):
    mapped = _mapping_like(value)
    if mapped is not None:
        return mapped
    if isinstance(value, (list, tuple)):
        mappings = []
        pairs = {}
        for item in value:
            item_mapping = _mapping_like(item)
            if item_mapping is not None:
                mappings.append(item_mapping)
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                pairs[str(item[0])] = item[1]
        if len(mappings) == 1 and not pairs:
            return mappings[0]
        if mappings and not pairs:
            return dict(default or {'status': 'COMPLETED', 'items': mappings})
        if pairs and not mappings:
            return pairs
        if mappings or pairs:
            result = dict(default or {'status': 'COMPLETED'})
            result['items'] = mappings
            result['pairs'] = pairs
            return result
        return dict(default or {'status': 'COMPLETED'})
    if value is None:
        return dict(default or {'status': 'COMPLETED'})
    return {'status': 'COMPLETED', 'value': value}


def as_mapping_list(value):
    mapped = _mapping_like(value)
    if mapped is not None:
        return [mapped]
    if isinstance(value, (list, tuple)):
        out = []
        for item in value:
            item_mapping = _mapping_like(item)
            if item_mapping is not None:
                out.append(item_mapping)
            elif isinstance(item, (list, tuple)):
                for nested in item:
                    nested_mapping = _mapping_like(nested)
                    if nested_mapping is not None:
                        out.append(nested_mapping)
        return out
    return []


def as_pair_mapping(value):
    """Normalize Kraken AssetPairs-style results without tuple-unpacking."""
    mapped = _mapping_like(value)
    if mapped is not None:
        return mapped
    if isinstance(value, (list, tuple)):
        out = {}
        for item in value:
            item_mapping = _mapping_like(item)
            if item_mapping is None:
                continue
            key = item_mapping.get('wsname') or item_mapping.get('altname') or item_mapping.get('symbol') or item_mapping.get('pair')
            if key:
                out[str(key)] = item_mapping
        return out
    return {}

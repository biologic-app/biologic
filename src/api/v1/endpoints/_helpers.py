from collections.abc import Mapping


def parse_includes(include: str | None) -> list[str]:
    if not include:
        return []
    parsed = [value.strip() for value in include.split(",") if value.strip()]
    return list(dict.fromkeys(parsed))


def parse_list_filters(
    query_params: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, tuple[str | None, str | None]]]:
    exact_filters: dict[str, str] = {}
    range_filters: dict[str, tuple[str | None, str | None]] = {}
    reserved = {"offset", "limit", "sort_by", "sort_order", "include"}

    for key, value in query_params.items():
        if key in reserved:
            continue
        if key.endswith("_from"):
            field_name = key[:-5]
            current_from, current_to = range_filters.get(field_name, (None, None))
            range_filters[field_name] = (value, current_to)
            continue
        if key.endswith("_to"):
            field_name = key[:-3]
            current_from, current_to = range_filters.get(field_name, (None, None))
            range_filters[field_name] = (current_from, value)
            continue
        exact_filters[key] = value

    return exact_filters, range_filters

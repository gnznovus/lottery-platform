import re

from scraping.types import ExtractedField


THAI_DIGITS = str.maketrans("\u0e50\u0e51\u0e52\u0e53\u0e54\u0e55\u0e56\u0e57\u0e58\u0e59", "0123456789")


def _tokenize_numeric_value(raw_value: str) -> list[str]:
    translated = raw_value.translate(THAI_DIGITS)
    if re.search(r"[A-Za-z\u0E00-\u0E7F]", translated):
        return []

    cleaned = translated.replace(",", "")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return []
    return [part for part in cleaned.split(" ") if part]


def _normalize_text_value(raw_value: str) -> list[str]:
    cleaned = " ".join(raw_value.replace("\xa0", " ").split())
    if not cleaned:
        return []
    if re.fullmatch(r"[^A-Za-z\u0E00-\u0E7F0-9]+", cleaned):
        return []
    return [cleaned]


def normalize_extracted_fields(extracted_fields: list[ExtractedField], reward_definitions: list[dict] | None = None) -> list[ExtractedField]:
    definition_map = {definition["reward_type"]: definition for definition in (reward_definitions or [])}
    normalized = []

    for field in extracted_fields:
        definition = definition_map.get(field.reward_type, {})
        value_type = definition.get("value_type", "number")
        values = []

        for raw_value in field.values:
            if value_type == "text":
                values.extend(_normalize_text_value(raw_value))
            else:
                values.extend(_tokenize_numeric_value(raw_value))

        normalized.append(
            ExtractedField(
                reward_type=field.reward_type,
                raw_label=field.raw_label,
                values=values,
                metadata=field.metadata,
            )
        )

    return normalized

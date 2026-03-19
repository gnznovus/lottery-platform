from scraping.types import ExtractedField


class ValidationError(ValueError):
    pass


def _field_context(field: ExtractedField) -> str:
    label = field.raw_label or field.metadata.get("raw_label") or "<missing label>"
    return f"reward_type={field.reward_type}, label={label!r}, values={field.values!r}"


def validate_extracted_fields(extracted_fields: list[ExtractedField], reward_definitions: list[dict]) -> None:
    definition_map = {definition["reward_type"]: definition for definition in reward_definitions}

    for field in extracted_fields:
        definition = definition_map[field.reward_type]
        expected_count = definition.get("expected_count")
        digit_length = definition.get("digit_length")
        required = definition.get("required", True)
        value_type = definition.get("value_type", "number")

        if required and not field.values:
            raise ValidationError(f"Missing values for {_field_context(field)}")

        if expected_count is not None and field.values and len(field.values) != expected_count:
            raise ValidationError(
                f"Expected {expected_count} values but got {len(field.values)} for {_field_context(field)}"
            )

        if value_type == "text":
            continue

        if digit_length is not None:
            for value in field.values:
                if len(value) != digit_length or not value.isdigit():
                    raise ValidationError(
                        f"Expected {digit_length} digits but got {value!r} for {_field_context(field)}"
                    )

import re
from datetime import date, datetime


class DrawDateParseError(ValueError):
    pass


THAI_MONTHS = {
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}


def parse_thai_text_date(raw_value: str) -> date:
    cleaned = " ".join(raw_value.strip().split())
    match = re.fullmatch(r"(\d{1,2})\s+([^\s]+)\s+(\d{4})", cleaned)
    if not match:
        raise DrawDateParseError(f"Unsupported Thai draw date format: {raw_value}")

    day = int(match.group(1))
    month_name = match.group(2)
    year = int(match.group(3))

    month = THAI_MONTHS.get(month_name)
    if month is None:
        raise DrawDateParseError(f"Unsupported Thai month name: {month_name}")

    if year > 2400:
        year -= 543

    return date(year, month, day)


def parse_draw_date_value(raw_value: str | None) -> date | None:
    if not raw_value:
        return None

    cleaned = raw_value.strip()
    if len(cleaned) == 8 and cleaned.isdigit():
        day = int(cleaned[:2])
        month = int(cleaned[2:4])
        year = int(cleaned[4:])
        return datetime(year - 543, month, day).date()

    if len(cleaned) == 10 and cleaned[4] == '-' and cleaned[7] == '-':
        return datetime.strptime(cleaned, '%Y-%m-%d').date()

    if any(month_name in cleaned for month_name in THAI_MONTHS):
        return parse_thai_text_date(cleaned)

    raise DrawDateParseError(f'Unsupported draw date format: {raw_value}')

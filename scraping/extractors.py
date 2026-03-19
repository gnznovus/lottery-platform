import re

from bs4 import BeautifulSoup

from scraping.types import ExtractedField


class ExtractionError(RuntimeError):
    pass


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _container_nodes(soup: BeautifulSoup, extraction_config: dict):
    selector = extraction_config.get("container_selector")
    if not selector:
        return [soup]
    nodes = soup.select(selector)
    if not nodes:
        raise ExtractionError(f"No containers matched selector: {selector}")
    return nodes


def _extract_label_groups_from_tables(html: str, extraction_config: dict, reward_definitions: list[dict]) -> list[ExtractedField]:
    soup = BeautifulSoup(html, "html.parser")
    containers = _container_nodes(soup, extraction_config)
    extracted = []

    value_selector = extraction_config.get("value_selector", "td")
    label_selector = extraction_config.get("label_selector", "p")

    for reward_definition in reward_definitions:
        aliases = [alias.strip() for alias in reward_definition.get("aliases", []) if alias.strip()]
        reward_type = reward_definition["reward_type"]
        found = False

        for container in containers:
            label_node = None
            for candidate in container.select(label_selector):
                label_text = _normalize_text(candidate.get_text(" ", strip=True))
                if any(alias in label_text for alias in aliases):
                    label_node = candidate
                    break

            if label_node is None:
                continue

            table_node = label_node.find_next(reward_definition.get("table_tag", "table"))
            if table_node is None:
                continue

            raw_values = [
                _normalize_text(node.get_text(" ", strip=True))
                for node in table_node.select(value_selector)
                if _normalize_text(node.get_text(" ", strip=True))
            ]

            extracted.append(
                ExtractedField(
                    reward_type=reward_type,
                    raw_label=_normalize_text(label_node.get_text(" ", strip=True)),
                    values=raw_values,
                    metadata={"aliases": aliases, "mode": "label_groups"},
                )
            )
            found = True
            break

        if not found:
            extracted.append(
                ExtractedField(
                    reward_type=reward_type,
                    raw_label="",
                    values=[],
                    metadata={"aliases": aliases, "missing": True, "mode": "label_groups"},
                )
            )

    return extracted


def _prepare_document_lines(html: str, extraction_config: dict) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    root_selector = extraction_config.get("root_selector")
    scope = soup.select_one(root_selector) if root_selector else soup
    if root_selector and scope is None:
        raise ExtractionError(f"No root node matched selector: {root_selector}")

    text_lines = [_normalize_text(line) for line in scope.get_text("\n").splitlines()]
    text_lines = [line for line in text_lines if line]

    start_marker = extraction_config.get("start_marker")
    end_marker = extraction_config.get("end_marker")

    if start_marker:
        for index, line in enumerate(text_lines):
            if start_marker in line:
                text_lines = text_lines[index:]
                break

    if end_marker:
        for index, line in enumerate(text_lines):
            if end_marker in line:
                text_lines = text_lines[:index]
                break

    return text_lines


def _extract_document_lines(html: str, extraction_config: dict, reward_definitions: list[dict]) -> list[ExtractedField]:
    lines = _prepare_document_lines(html, extraction_config)
    extracted = []
    alias_map = {}
    for definition in reward_definitions:
        for alias in definition.get("aliases", []):
            alias_map[alias] = definition["reward_type"]

    all_aliases = list(alias_map.keys())

    for definition in reward_definitions:
        aliases = [alias.strip() for alias in definition.get("aliases", []) if alias.strip()]
        reward_type = definition["reward_type"]
        found_index = None
        found_label = ""

        for index, line in enumerate(lines):
            if any(alias in line for alias in aliases):
                found_index = index
                found_label = line
                break

        if found_index is None:
            extracted.append(
                ExtractedField(
                    reward_type=reward_type,
                    raw_label="",
                    values=[],
                    metadata={"aliases": aliases, "missing": True, "mode": "document_lines"},
                )
            )
            continue

        collected_lines = []
        for line in lines[found_index + 1 :]:
            if any(alias in line for alias in all_aliases):
                break
            collected_lines.append(line)

        extracted.append(
            ExtractedField(
                reward_type=reward_type,
                raw_label=found_label,
                values=collected_lines,
                metadata={"aliases": aliases, "mode": "document_lines"},
            )
        )

    return extracted


def _extract_ordered_values(html: str, extraction_config: dict, reward_definitions: list[dict]) -> list[ExtractedField]:
    lines = _prepare_document_lines(html, extraction_config)
    pattern = extraction_config.get("value_pattern", r"^[0-9]+(?:\s+[0-9]+)*$")
    value_re = re.compile(pattern)
    value_lines = [line for line in lines if value_re.fullmatch(line)]

    extracted = []
    for index, definition in enumerate(reward_definitions):
        aliases = [alias.strip() for alias in definition.get("aliases", []) if alias.strip()]
        reward_type = definition["reward_type"]
        value = value_lines[index] if index < len(value_lines) else None
        extracted.append(
            ExtractedField(
                reward_type=reward_type,
                raw_label=aliases[0] if aliases else reward_type,
                values=[value] if value else [],
                metadata={"aliases": aliases, "mode": "ordered_values", "position": index},
            )
        )

    return extracted


def extract_fields(html: str, extraction_config: dict, reward_definitions: list[dict]) -> list[ExtractedField]:
    mode = extraction_config.get("mode", "label_groups")
    if mode == "label_groups":
        return _extract_label_groups_from_tables(html, extraction_config, reward_definitions)
    if mode == "document_lines":
        return _extract_document_lines(html, extraction_config, reward_definitions)
    if mode == "ordered_values":
        return _extract_ordered_values(html, extraction_config, reward_definitions)
    raise ExtractionError(f"Unsupported extraction mode: {mode}")

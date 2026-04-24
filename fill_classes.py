import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright


def class_sex(ianseo_name: str) -> str:
    if ianseo_name.endswith("M"):
        return "0"
    if ianseo_name.endswith("W"):
        return "1"
    return "-1"


def class_description(class_data: dict) -> str:
    name = str(class_data["name"])
    division = str(class_data["ianseo_division"])
    first_word, separator, rest = name.partition(" ")

    if separator and first_word[:1].upper() == division[:1].upper():
        return rest
    return name


def load_classes(path: Path) -> list[dict]:
    with path.expanduser().open(encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, list):
        raise ValueError("Class JSON must contain a list of class objects.")

    required_fields = {
        "ianseo_name",
        "ianseo_division",
        "name",
        "age_start",
        "age_end",
    }
    for index, class_data in enumerate(classes, start=1):
        missing_fields = required_fields - class_data.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise ValueError(f"Class entry {index} is missing: {fields}")

    return classes


def add_class(page, class_data: dict, view_order: int) -> dict:
    ianseo_name = str(class_data["ianseo_name"])
    form = {
        "New_ClId": ianseo_name,
        "New_ClDescription": class_description(class_data),
        "New_ClIsPara": "0",
        "New_ClAthlete": "1",
        "New_ClViewOrder": str(view_order),
        "New_ClAgeFrom": "1", # no upgrade classes supported str(class_data["age_start"]),
        "New_ClAgeTo": "100", # no upgrade classes supported str(class_data["age_end"]),
        "New_ClValidClass": ianseo_name,
        "New_ClSex": class_sex(ianseo_name),
        "New_ClValidDivision": "",
    }

    return page.evaluate(
        """async (form) => {
            const params = new URLSearchParams(form);
            const response = await fetch(`AddCl.php?${params.toString()}`, {
                headers: { Accept: "application/json" },
            });
            return await response.json();
        }""",
        form,
    )


def run(playwright: Playwright, classes: list[dict]) -> None:
    browser = playwright.chromium.launch(headless=False)
    try:
        context = browser.new_context()
        page = context.new_page()
        page.goto("http://localhost:8000/")
        page.get_by_role("cell", name="jubi26", exact=True).click()
        page.get_by_role("row", name=re.compile("Öffnen jubi26")).get_by_role("link").click()
        page.get_by_role("link", name="Turnier", exact=True).click()
        page.get_by_role("link", name="Turnierdaten ändern").click()
        page.get_by_role("link", name="Bogenklassen und Altersklassen").click()

        errors = []
        seen_class_codes = set()
        view_order = 1
        for class_data in classes:
            ianseo_name = str(class_data["ianseo_name"])
            if ianseo_name in seen_class_codes:
                print(
                    "Skipped duplicate "
                    f"{class_data['ianseo_division']} / {ianseo_name} "
                    f"({class_data['name']})"
                )
                continue

            result = add_class(page, class_data, view_order)
            seen_class_codes.add(ianseo_name)
            label = (
                f"{class_data['ianseo_division']} / {ianseo_name} "
                f"({class_description(class_data)})"
            )
            if result.get("error"):
                errors.append(f"{label}: {result.get('errormsg', 'unknown error')}")
                print(f"ERROR {label}: {result.get('errormsg', 'unknown error')}")
                continue
            print(f"Added {label}")
            view_order += 1

        if errors:
            raise RuntimeError("Could not add all classes:\n" + "\n".join(errors))
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill Ianseo classes from JSON.")
    parser.add_argument("classes_json", type=Path, default="~/Downloads/jubilaumsturnier-100-jahre-psv-classes.json")
    args = parser.parse_args()

    classes = load_classes(args.classes_json)
    with sync_playwright() as playwright:
        run(playwright, classes)


if __name__ == "__main__":
    main()

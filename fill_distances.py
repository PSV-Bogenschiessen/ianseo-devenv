import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright


def load_classes(path: Path) -> list[dict]:
    with path.expanduser().open(encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, list):
        raise ValueError("Class JSON must contain a list of class objects.")

    required_fields = {
        "ianseo_name",
        "ianseo_division",
        "target_faces",
    }
    for index, class_data in enumerate(classes, start=1):
        missing_fields = required_fields - class_data.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise ValueError(f"Class entry {index} is missing: {fields}")
        if not class_data["target_faces"]:
            raise ValueError(f"Class entry {index} has no target_faces.")
        if "distance" not in class_data["target_faces"][0]:
            raise ValueError(f"Class entry {index} target_faces[0] is missing: distance")

    return classes


def delete_all_distances(page) -> None:
    page.on("dialog", lambda dialog: dialog.accept())
    page.wait_for_selector("#tbody")
    page.wait_for_timeout(500)

    deleted = 0
    trash_buttons = page.locator("#tbody i.fa-trash-can[onclick='deleteRow(this)']")
    while trash_buttons.count():
        previous_count = trash_buttons.count()
        trash_buttons.first.click()
        deleted += 1

        try:
            page.wait_for_function(
                """
                (previousCount) =>
                    document.querySelectorAll(
                        "#tbody i.fa-trash-can[onclick='deleteRow(this)']"
                    ).length < previousCount
                """,
                arg=previous_count,
                timeout=5000,
            )
        except TimeoutError:
            page.wait_for_timeout(500)

    print(f"Deleted {deleted} distance entries.")


def add_distance(page, class_data: dict) -> None:
    division = str(class_data["ianseo_division"])
    class_name = str(class_data["ianseo_name"])
    class_filter = f"{division}{class_name}"
    distance = class_data["target_faces"][0]["distance"]

    page.locator('input[name="cl"]').fill(class_filter)
    page.locator('input[name="td-1"]').fill(f"{distance}m - 1")
    page.locator('input[name="td-2"]').fill(f"{distance}m - 2")
    page.get_by_role("button", name="OK").click()
    page.wait_for_timeout(300)
    print(f"Added distance {class_filter}: {distance}m")


def fill_distances(page, classes: list[dict]) -> None:
    for class_data in classes:
        add_distance(page, class_data)


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
        page.get_by_role("link", name="Entfernungen").click()

        delete_all_distances(page)
        fill_distances(page, classes)
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill Ianseo distances from JSON.")
    parser.add_argument("classes_json", type=Path)
    args = parser.parse_args()

    classes = load_classes(args.classes_json)
    with sync_playwright() as playwright:
        run(playwright, classes)


if __name__ == "__main__":
    main()

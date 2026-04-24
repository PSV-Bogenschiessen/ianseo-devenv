import argparse
import json
import re
from pathlib import Path

from playwright.sync_api import Playwright, TimeoutError, sync_playwright


TARGET_TYPE_COMPLETE = "5"


def load_target_faces(path: Path) -> list[dict]:
    with path.expanduser().open(encoding="utf-8") as file:
        classes = json.load(file)

    if not isinstance(classes, list):
        raise ValueError("Class JSON must contain a list of class objects.")

    target_faces = {}
    for index, class_data in enumerate(classes, start=1):
        if "target_faces" not in class_data:
            raise ValueError(f"Class entry {index} is missing: target_faces")
        if not class_data["target_faces"]:
            raise ValueError(f"Class entry {index} has no target_faces.")

        target_face = class_data["target_faces"][0]
        required_fields = {"name", "size"}
        missing_fields = required_fields - target_face.keys()
        if missing_fields:
            fields = ", ".join(sorted(missing_fields))
            raise ValueError(f"Class entry {index} target_faces[0] is missing: {fields}")

        target_faces[target_face["name"]] = target_face

    return list(target_faces.values())


def delete_all_target_faces(page) -> None:
    page.on("dialog", lambda dialog: dialog.accept())
    page.wait_for_selector("#tbody")
    page.wait_for_timeout(500)

    deleted = 0
    trash_buttons = page.locator("#tbody i.fa-trash-can[onclick='deleteTarget(this)']")
    while trash_buttons.count():
        previous_count = trash_buttons.count()
        trash_buttons.first.click()
        deleted += 1

        try:
            page.wait_for_function(
                """
                (previousCount) =>
                    document.querySelectorAll(
                        "#tbody i.fa-trash-can[onclick='deleteTarget(this)']"
                    ).length < previousCount
                """,
                arg=previous_count,
                timeout=5000,
            )
        except TimeoutError:
            page.wait_for_timeout(500)

    print(f"Deleted {deleted} target face entries.")


def add_target_face(page, target_face: dict) -> None:
    name = str(target_face["name"])
    size = str(target_face["size"])

    page.locator("#TdName").fill(name)
    page.locator("#TdClasses").fill("%")

    face_selects = page.locator('select[id^="TdFace"]')
    for index in range(face_selects.count()):
        face_selects.nth(index).select_option(TARGET_TYPE_COMPLETE)

    diameter_inputs = page.locator('input[id^="TdDiam"]')
    for index in range(diameter_inputs.count()):
        diameter_inputs.nth(index).fill(size)

    page.get_by_role("button", name="OK").click()
    page.wait_for_timeout(300)
    print(f"Added target face {name}: {size}cm")


def fill_target_faces(page, target_faces: list[dict]) -> None:
    for target_face in target_faces:
        add_target_face(page, target_face)


def run(playwright: Playwright, target_faces: list[dict]) -> None:
    browser = playwright.chromium.launch(headless=False)
    try:
        context = browser.new_context()
        page = context.new_page()
        page.goto("http://localhost:8000/")
        page.get_by_role("cell", name="jubi26", exact=True).click()
        page.get_by_role("row", name=re.compile("Öffnen jubi26")).get_by_role("link").click()
        page.get_by_role("link", name="Turnier", exact=True).click()
        page.get_by_role("link", name="Turnierdaten ändern").click()
        page.get_by_role("link", name="Scheibenauflagen").click()

        delete_all_target_faces(page)
        fill_target_faces(page, target_faces)
    finally:
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fill Ianseo target faces from JSON.")
    parser.add_argument("classes_json", type=Path)
    args = parser.parse_args()

    target_faces = load_target_faces(args.classes_json)
    with sync_playwright() as playwright:
        run(playwright, target_faces)


if __name__ == "__main__":
    main()

import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "recover_habr_links_for_n8n.py"
SPEC = importlib.util.spec_from_file_location("recover_habr_links_for_n8n", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

clean_title = MODULE.clean_title
normalized_title = MODULE.normalized_title


def test_clean_title_removes_habr_suffix_and_html() -> None:
    assert clean_title("Время в криптографии &#x2F; Хабр") == "Время в криптографии"
    assert clean_title("<b>Android</b>. Glance Widgets. Начало") == "Android. Glance Widgets. Начало"


def test_normalized_title_matches_legacy_translation_prefix() -> None:
    db_title = "[Перевод] Если ваш запрос на слияние сгенерирован ИИ"
    habr_title = "Если ваш запрос на слияние сгенерирован ИИ"

    assert normalized_title(db_title) == normalized_title(habr_title)


def test_normalized_title_matches_yo_and_spacing_variants() -> None:
    db_title = "QA-инженер в продукте: как я ушёл из аутсорса"
    habr_title = "QA-инженер в продукте :  как я ушел из аутсорса"

    assert normalized_title(db_title) == normalized_title(habr_title)

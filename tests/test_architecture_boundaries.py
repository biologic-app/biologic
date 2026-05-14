from pathlib import Path

CONTEXTS = {
    "access_control",
    "audit",
    "catalogs",
    "laboratory_workflow",
    "notifications",
}
LAYERS = {"domain", "application", "infrastructure", "presentation"}


def test_context_layer_packages_exist() -> None:
    root = Path("src/contexts")

    for context in CONTEXTS:
        context_path = root / context
        assert (context_path / "__init__.py").is_file()
        for layer in LAYERS:
            assert (context_path / layer / "__init__.py").is_file()


def test_core_does_not_import_contexts() -> None:
    for path in Path("src/core").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "src.contexts" not in source, path


def test_domain_does_not_import_fastapi_or_sqlalchemy() -> None:
    for path in Path("src/contexts").glob("*/domain/**/*.py"):
        source = path.read_text(encoding="utf-8")
        assert "fastapi" not in source.lower(), path
        assert "sqlalchemy" not in source.lower(), path

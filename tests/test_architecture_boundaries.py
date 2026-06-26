from pathlib import Path

# Contexts still living under src/contexts/. They are being collapsed one at a
# time into the flat single-context layout src/{domain,application,
# infrastructure,presentation}; migrated modules are listed in FLAT_DOMAINS.
CONTEXTS = {
    "laboratory_workflow",
    "notifications",
}
LAYERS = {"domain", "application", "infrastructure", "presentation"}

# Modules already migrated onto the flat single-context layout.
FLAT_DOMAINS = {"audit", "catalogs", "access_control"}


def test_context_layer_packages_exist() -> None:
    root = Path("src/contexts")

    for context in CONTEXTS:
        context_path = root / context
        assert (context_path / "__init__.py").is_file()
        for layer in LAYERS:
            assert (context_path / layer / "__init__.py").is_file()


def test_flat_domains_are_migrated_out_of_contexts() -> None:
    for domain in FLAT_DOMAINS:
        assert not (Path("src/contexts") / domain).exists(), domain
        assert (Path("src/domain") / domain).is_dir(), domain
        assert (Path("src/application") / domain).is_dir(), domain


def test_core_does_not_import_contexts() -> None:
    for path in Path("src/core").glob("*.py"):
        source = path.read_text(encoding="utf-8")
        assert "src.contexts" not in source, path


def test_domain_does_not_import_fastapi_or_sqlalchemy() -> None:
    domain_files = [
        *Path("src/contexts").glob("*/domain/**/*.py"),
        *Path("src/domain").glob("**/*.py"),
    ]
    for path in domain_files:
        # The Unit of Work protocol lives in src/domain/uow.py and references
        # repository *ports* only — no framework imports.
        source = path.read_text(encoding="utf-8")
        assert "fastapi" not in source.lower(), path
        assert "sqlalchemy" not in source.lower(), path

"""Regression tests for the VitePress documentation site."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "docs"


def test_theme_components_exist() -> None:
    """The docs theme should expose the active component set."""
    components_dir = DOCS_ROOT / ".vitepress" / "theme" / "components"

    for name in (
        "ThemeAsset",
        "ReferenceList",
        "AlgorithmCard",
        "CitationBlock",
        "ArchitectureDiagram",
    ):
        assert (components_dir / f"{name}.vue").exists(), f"missing component: {name}"


def test_key_pages_exist() -> None:
    """Key documentation pages should exist."""
    expected_pages = [
        DOCS_ROOT / "zh" / "academy" / "pipeline-foundations.md",
        DOCS_ROOT / "zh" / "academy" / "data-products.md",
        DOCS_ROOT / "zh" / "architecture" / "system-overview.md",
        DOCS_ROOT / "zh" / "architecture" / "module-design.md",
        DOCS_ROOT / "zh" / "architecture" / "testing-strategy.md",
        DOCS_ROOT / "zh" / "algorithms" / "quality-control.md",
        DOCS_ROOT / "zh" / "algorithms" / "taxonomic-classification.md",
        DOCS_ROOT / "zh" / "algorithms" / "diversity-metrics.md",
        DOCS_ROOT / "zh" / "analysis" / "taxonomic-profiling.md",
        DOCS_ROOT / "zh" / "analysis" / "diversity-analysis.md",
        DOCS_ROOT / "zh" / "analysis" / "functional-profiling.md",
        DOCS_ROOT / "zh" / "research" / "citations.md",
        DOCS_ROOT / "zh" / "research" / "competition.md",
    ]

    for page in expected_pages:
        assert page.exists(), f"missing page: {page.relative_to(PROJECT_ROOT)}"


def test_navigation_sections_configured() -> None:
    """The config should register navigation sections."""
    config_text = (DOCS_ROOT / ".vitepress" / "config.ts").read_text(encoding="utf-8")

    for section in ("学院", "架构", "算法", "指南", "参考", "研究"):
        assert section in config_text


def test_removed_fictional_pages_are_gone() -> None:
    """Fictional or redundant pages should have been removed."""
    removed = [
        DOCS_ROOT / "zh" / "algorithms" / "performance-benchmarks.md",
        DOCS_ROOT / "zh" / "academy" / "algorithm-deep-dive.md",
        DOCS_ROOT / "zh" / "architecture" / "runtime-topology.md",
    ]

    for page in removed:
        assert (
            not page.exists()
        ), f"page should have been removed: {page.relative_to(PROJECT_ROOT)}"

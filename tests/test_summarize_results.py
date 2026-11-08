# -*- coding: utf-8 -*-
"""测试结果汇总模块。"""

from micos.summarize_results import generate_summary_report, parse_kraken_reports


def test_generate_summary_report_supports_named_layout(tmp_path):
    """支持新的命名目录结构。"""
    results_dir = tmp_path / "results"
    (results_dir / "quality_control" / "fastqc_reports").mkdir(parents=True)
    (results_dir / "taxonomic_profiling").mkdir(parents=True)
    (results_dir / "diversity_analysis").mkdir(parents=True)
    (results_dir / "functional_annotation").mkdir(parents=True)

    (
        results_dir / "quality_control" / "fastqc_reports" / "sample_fastqc.html"
    ).write_text("ok", encoding="utf-8")
    (results_dir / "taxonomic_profiling" / "feature-table.biom").write_text(
        "biom", encoding="utf-8"
    )
    (results_dir / "diversity_analysis" / "alpha.qza").write_text(
        "qza", encoding="utf-8"
    )
    (results_dir / "functional_annotation" / "sample_pathabundance.tsv").write_text(
        "path", encoding="utf-8"
    )

    output_file = tmp_path / "report" / "summary.html"
    generate_summary_report(results_dir, output_file)

    html_text = output_file.read_text(encoding="utf-8")
    assert "quality_control/fastqc_reports/sample_fastqc.html" in html_text
    assert "taxonomic_profiling/feature-table.biom" in html_text
    assert "diversity_analysis/alpha.qza" in html_text
    assert "functional_annotation/sample_pathabundance.tsv" in html_text


def test_generate_summary_report_ignores_numbered_layout(tmp_path):
    """不再支持旧的编号目录结构（1_quality_control 等）。"""
    results_dir = tmp_path / "results"
    (results_dir / "1_quality_control" / "fastqc_reports").mkdir(parents=True)
    (results_dir / "2_taxonomic_profiling").mkdir(parents=True)

    (
        results_dir / "1_quality_control" / "fastqc_reports" / "sample_fastqc.html"
    ).write_text("ok", encoding="utf-8")
    (results_dir / "2_taxonomic_profiling" / "feature-table.biom").write_text(
        "biom", encoding="utf-8"
    )

    output_file = tmp_path / "summary.html"
    generate_summary_report(results_dir, output_file)

    html_text = output_file.read_text(encoding="utf-8")
    # 旧编号目录下的文件不被收录
    assert "1_quality_control/" not in html_text
    assert "2_taxonomic_profiling/" not in html_text


def test_generate_summary_report_includes_metrics(tmp_path):
    """报告应包含 Kraken Top taxa、Alpha 多样性与运行清单。"""
    results_dir = tmp_path / "results"
    (results_dir / "taxonomic_profiling").mkdir(parents=True)
    (results_dir / "diversity_analysis" / "alpha_diversity").mkdir(parents=True)
    (results_dir / "taxonomic_profiling" / "sample1.report").write_text(
        " 80.00\t800\t800\tR\t1\troot\n"
        " 60.00\t600\t600\tS\t562\tEscherichia coli\n"
        " 20.00\t200\t200\tS\t1280\tStaphylococcus aureus\n"
        " 20.00\t200\t0\tU\t0\tunclassified\n",
        encoding="utf-8",
    )
    (
        results_dir / "diversity_analysis" / "alpha_diversity" / "alpha-diversity.tsv"
    ).write_text(
        "sample-id\tshannon\nsample1\t3.21\nsample2\t2.87\n",
        encoding="utf-8",
    )
    (results_dir / "run_manifest.json").write_text(
        '{"run_id":"test-run","status":"completed","started_at":"2026-11-06T00:00:00+00:00","stages":[{"name":"质量控制","status":"completed","duration_sec":1.2}]}',
        encoding="utf-8",
    )

    output_file = tmp_path / "summary.html"
    generate_summary_report(results_dir, output_file)
    html_text = output_file.read_text(encoding="utf-8")

    assert "样本数" in html_text
    assert "Top taxa" in html_text
    assert "Escherichia coli" in html_text
    assert "shannon" in html_text.lower()
    assert "3.2100" in html_text
    assert "test-run" in html_text
    assert "质量控制" in html_text


def test_parse_kraken_reports_does_not_double_subtract_unclassified(tmp_path):
    """Kraken2 report 的 R 行已是分类 reads，未分类只在 U 行扣一次。"""
    results_dir = tmp_path / "results"
    (results_dir / "taxonomic_profiling").mkdir(parents=True)
    (results_dir / "taxonomic_profiling" / "sample1.report").write_text(
        " 60.00\t600\t600\tR\t1\troot\n"
        " 40.00\t400\t400\tS\t562\tEscherichia coli\n"
        " 20.00\t200\t0\tU\t0\tunclassified\n",
        encoding="utf-8",
    )

    summary = parse_kraken_reports(results_dir)

    assert summary is not None
    assert summary.total_reads == 800
    assert summary.classified_reads == 600

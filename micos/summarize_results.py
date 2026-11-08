# -*- coding: utf-8 -*-
"""结果汇总模块。"""

from __future__ import annotations

import csv
import datetime
import html
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SECTION_PATTERNS = {
    "质量控制": [
        "quality_control/fastqc_reports/*.html",
        "quality_control/fastqc_reports/*.zip",
        "quality_control/kneaddata/*_kneaddata*log*",
        "quality_control/kneaddata/*_paired_*.fastq",
    ],
    "物种分类 (Kraken2)": [
        "taxonomic_profiling/*.kraken",
        "taxonomic_profiling/*.report",
    ],
    "分类可视化 (Krona)": [
        "taxonomic_profiling/*.krona.html",
    ],
    "BIOM 表": [
        "taxonomic_profiling/feature-table.biom",
    ],
    "多样性分析 (QIIME2)": [
        "diversity_analysis/*.qza",
        "diversity_analysis/*.qzv",
        "diversity_analysis/**/*.tsv",
        "diversity_analysis/**/*.txt",
    ],
    "功能注释 (HUMAnN)": [
        "functional_annotation/*genefamilies*.tsv*",
        "functional_annotation/*pathabundance*.tsv*",
        "functional_annotation/*pathcoverage*.tsv*",
        "functional_annotation/*.log",
    ],
}


@dataclass(frozen=True)
class TaxonAbundance:
    """一个物种的分类 reads 数。"""

    name: str
    reads: int


@dataclass(frozen=True)
class KrakenSummary:
    """Kraken2 报告汇总。"""

    sample_count: int
    total_reads: int
    classified_reads: int
    top_taxa: list[TaxonAbundance]


@dataclass(frozen=True)
class AlphaSummary:
    """Alpha 多样性表汇总。"""

    metric: str
    values: list[tuple[str, float]]

    @property
    def min_value(self) -> float:
        return min(value for _, value in self.values)

    @property
    def max_value(self) -> float:
        return max(value for _, value in self.values)

    @property
    def mean_value(self) -> float:
        return sum(value for _, value in self.values) / len(self.values)


@dataclass(frozen=True)
class SummaryStats:
    """报告用到的聚合统计。"""

    kraken: KrakenSummary | None = None
    alpha: AlphaSummary | None = None
    manifest: dict[str, Any] | None = None


def find_files(root: Path, patterns: list[str]) -> list[Path]:
    """按模式查找文件并去重。"""
    found: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for file_path in sorted(root.glob(pattern)):
            if not file_path.is_file():
                continue
            resolved = file_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            found.append(file_path)
    return found


def _parse_kraken_report(path: Path) -> tuple[int, int, dict[str, int]]:
    """解析单个 Kraken2 report，返回总 reads、分类 reads、物种计数。"""
    total_reads = 0
    classified_reads = 0
    unclassified_reads = 0
    species: dict[str, int] = {}

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        fields = line.rstrip("\n").split("\t")
        if len(fields) < 6:
            continue
        try:
            clade_reads = int(fields[1])
        except ValueError:
            continue
        rank = fields[3].strip()
        name = fields[5].strip()

        if rank == "R":
            # Kraken2 report 的 root 行只统计已分类 reads；未分类单独出现在 U 行。
            classified_reads += clade_reads
        elif rank == "U":
            unclassified_reads += clade_reads
        elif rank == "S":
            species[name] = species.get(name, 0) + clade_reads

    if not classified_reads:
        # 部分裁剪过的 report 没有 R 行，用物种 clade 之和回退。
        classified_reads = sum(species.values())

    total_reads = classified_reads + unclassified_reads
    return total_reads, classified_reads, species


def parse_kraken_reports(results_dir: Path) -> KrakenSummary | None:
    """聚合 taxonomic_profiling/*.report。"""
    reports = sorted((results_dir / "taxonomic_profiling").glob("*.report"))
    if not reports:
        return None

    total_reads = 0
    classified_reads = 0
    species: dict[str, int] = {}
    for report in reports:
        report_total, report_classified, report_species = _parse_kraken_report(report)
        total_reads += report_total
        classified_reads += report_classified
        for name, reads in report_species.items():
            species[name] = species.get(name, 0) + reads

    top_taxa = [
        TaxonAbundance(name=name, reads=reads)
        for name, reads in sorted(
            species.items(), key=lambda item: item[1], reverse=True
        )[:10]
    ]
    return KrakenSummary(
        sample_count=len(reports),
        total_reads=total_reads,
        classified_reads=classified_reads,
        top_taxa=top_taxa,
    )


def _find_alpha_table(results_dir: Path) -> Path | None:
    """寻找 QIIME2 导出的 alpha 多样性表。"""
    candidates = sorted((results_dir / "diversity_analysis").rglob("*.tsv"))
    for candidate in candidates:
        name = candidate.name.lower()
        if "alpha" in name:
            return candidate
    for candidate in candidates:
        try:
            header = candidate.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()[:1]
        except OSError:
            continue
        if header and "shannon" in header[0].lower():
            return candidate
    return None


def parse_alpha_diversity(results_dir: Path) -> AlphaSummary | None:
    """解析 alpha 多样性 TSV。"""
    path = _find_alpha_table(results_dir)
    if path is None:
        return None

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if len(lines) < 2:
        return None

    reader = csv.DictReader(lines, delimiter="\t")
    if not reader.fieldnames:
        return None
    id_column = reader.fieldnames[0]
    metric_columns = [name for name in reader.fieldnames[1:] if name]
    if not metric_columns:
        return None
    metric = next(
        (name for name in metric_columns if "shannon" in name.lower()),
        metric_columns[-1],
    )

    values: list[tuple[str, float]] = []
    for row in reader:
        sample_id = (row.get(id_column) or "").strip()
        raw_value = (row.get(metric) or "").strip()
        if not sample_id or not raw_value:
            continue
        try:
            values.append((sample_id, float(raw_value)))
        except ValueError:
            continue
    if not values:
        return None
    return AlphaSummary(metric=metric, values=values)


def parse_manifest(results_dir: Path) -> dict[str, Any] | None:
    """读取 run_manifest.json；不存在或损坏时返回 None。"""
    path = results_dir / "run_manifest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def collect_stats(results_dir: Path) -> SummaryStats:
    """收集报告所需的聚合统计。"""
    return SummaryStats(
        kraken=parse_kraken_reports(results_dir),
        alpha=parse_alpha_diversity(results_dir),
        manifest=parse_manifest(results_dir),
    )


def _fmt_int(value: int) -> str:
    return f"{value:,}"


def _metric_label(metric: str) -> str:
    return metric.replace("_", " ").strip().title()


def _card(label: str, value: str, hint: str = "") -> str:
    hint_html = f'<div class="hint">{html.escape(hint)}</div>' if hint else ""
    return (
        '<div class="card">'
        f'<div class="label">{html.escape(label)}</div>'
        f'<div class="metric">{html.escape(value)}</div>'
        f"{hint_html}"
        "</div>"
    )


def _render_cards(stats: SummaryStats) -> str:
    cards: list[str] = []
    if stats.kraken:
        summary = stats.kraken
        classified_pct = (
            summary.classified_reads / summary.total_reads * 100
            if summary.total_reads
            else 0.0
        )
        cards.extend(
            [
                _card("样本数", str(summary.sample_count), "Kraken2 报告"),
                _card("总 reads", _fmt_int(summary.total_reads)),
                _card("物种 reads", _fmt_int(summary.classified_reads)),
                _card("分类率", f"{classified_pct:.1f}%"),
            ]
        )
        if summary.top_taxa:
            cards.append(
                _card("最丰富物种", summary.top_taxa[0].name, "按物种 clade reads")
            )
    if stats.alpha:
        cards.extend(
            [
                _card(
                    f"{_metric_label(stats.alpha.metric)} 均值",
                    f"{stats.alpha.mean_value:.3f}",
                    f"{len(stats.alpha.values)} 个样本",
                ),
                _card(
                    "范围", f"{stats.alpha.min_value:.3f} – {stats.alpha.max_value:.3f}"
                ),
            ]
        )
    if not cards:
        cards.append(_card("分析产物", "等待结果", "运行 full-run 后自动汇总"))
    return '<section class="cards">' + "".join(cards) + "</section>"


def _render_kraken(stats: KrakenSummary | None) -> str:
    if not stats or not stats.top_taxa:
        return ""
    max_reads = max(taxon.reads for taxon in stats.top_taxa) or 1
    rows = []
    for taxon in stats.top_taxa:
        width = taxon.reads / max_reads * 100
        share = (
            taxon.reads / stats.classified_reads * 100
            if stats.classified_reads
            else 0.0
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(taxon.name)}</td>"
            f'<td class="num">{_fmt_int(taxon.reads)}</td>'
            f'<td class="share"><div class="bar"><span style="width:{width:.1f}%"></span></div>'
            f"<small>{share:.1f}%</small></td>"
            "</tr>"
        )
    return (
        '<section class="panel">'
        "<h2>Top taxa</h2>"
        '<p class="muted">按 Kraken2 物种层级 clade reads 汇总，最多显示 10 个。</p>'
        '<table><thead><tr><th>物种</th><th class="num">reads</th><th>占比</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
        "</section>"
    )


def _render_alpha(stats: AlphaSummary | None) -> str:
    if not stats:
        return ""
    rows = [
        "<tr>"
        f"<td>{html.escape(sample)}</td>"
        f'<td class="num">{value:.4f}</td>'
        "</tr>"
        for sample, value in stats.values[:50]
    ]
    suffix = (
        f'<p class="muted">仅显示前 50 个样本，共 {len(stats.values)} 个。</p>'
        if len(stats.values) > 50
        else ""
    )
    return (
        '<section class="panel">'
        f"<h2>Alpha 多样性 · {html.escape(_metric_label(stats.metric))}</h2>"
        '<table><thead><tr><th>样本</th><th class="num">值</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
        f"{suffix}"
        "</section>"
    )


def _render_manifest(manifest: dict[str, Any] | None) -> str:
    if not manifest:
        return ""
    status = str(manifest.get("status", "unknown"))
    status_class = "ok" if status == "completed" else "warn"
    stages = manifest.get("stages") or []
    stage_rows = []
    if isinstance(stages, list):
        for stage in stages:
            if not isinstance(stage, dict):
                continue
            stage_rows.append(
                "<tr>"
                f"<td>{html.escape(str(stage.get('name', '')))}</td>"
                f"<td><span class=\"badge {status_class if stage.get('status') == 'completed' else 'warn'}\">"
                f"{html.escape(str(stage.get('status', '')))}</span></td>"
                f"<td class=\"num\">{html.escape(str(stage.get('duration_sec', '—')))}s</td>"
                "</tr>"
            )
    stages_html = (
        '<table><thead><tr><th>阶段</th><th>状态</th><th class="num">耗时</th></tr></thead>'
        f"<tbody>{''.join(stage_rows)}</tbody></table>"
        if stage_rows
        else '<p class="muted">尚未记录阶段信息。</p>'
    )
    return (
        '<section class="panel">'
        "<h2>运行清单</h2>"
        '<div class="meta-grid">'
        f'<div><span>run_id</span><strong>{html.escape(str(manifest.get("run_id", "—")))}</strong></div>'
        f'<div><span>状态</span><strong><span class="badge {status_class}">{html.escape(status)}</span></strong></div>'
        f'<div><span>开始</span><strong>{html.escape(str(manifest.get("started_at", "—")))}</strong></div>'
        f'<div><span>结束</span><strong>{html.escape(str(manifest.get("finished_at") or "—"))}</strong></div>'
        "</div>"
        f"{stages_html}"
        '<p class="muted"><a href="run_manifest.json">查看 run_manifest.json</a></p>'
        "</section>"
    )


def _render_files(
    results_dir: Path,
    report_dir: Path,
    sections: dict[str, list[Path]],
) -> str:
    parts: list[str] = []
    missing: list[str] = []
    for section_name, files in sections.items():
        if not files:
            missing.append(section_name)
            continue
        parts.append(
            f'<section class="panel"><h2>{html.escape(section_name)} '
            f'<span class="count">{len(files)}</span></h2>'
        )
        parts.append('<ul class="files">')
        for file_path in files:
            resolved_file = file_path.resolve()
            if resolved_file.is_relative_to(report_dir):
                rel = resolved_file.relative_to(report_dir)
            else:
                try:
                    rel = Path(os.path.relpath(resolved_file, start=report_dir))
                except ValueError:
                    rel = resolved_file
            parts.append(
                f'<li><a href="{html.escape(rel.as_posix())}" target="_blank">'
                f"{html.escape(rel.as_posix())}</a></li>"
            )
        parts.append("</ul></section>")
    if missing:
        parts.append(
            '<section class="panel"><h2>未找到的产物</h2>'
            f'<p class="muted">{html.escape("、".join(missing))}</p></section>'
        )
    return "".join(parts)


def render_html(
    title: str,
    results_dir: Path,
    report_dir: Path,
    sections: dict[str, list[Path]],
    stats: SummaryStats | None = None,
) -> str:
    """渲染汇总 HTML。"""
    stats = stats or SummaryStats()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f4f7fb;
      --card: #ffffff;
      --ink: #0f1f33;
      --muted: #5b6b82;
      --border: #e1e8f2;
      --accent: #2563eb;
      --accent-2: #0f766e;
      --shadow: 0 18px 50px rgba(15, 31, 51, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
        "Noto Sans", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.55;
    }}
    .wrap {{ max-width: 1080px; margin: 0 auto; padding: 28px 20px 64px; }}
    .hero {{
      background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 58%, #0f766e 100%);
      color: #fff;
      border-radius: 24px;
      padding: 32px;
      box-shadow: var(--shadow);
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: -0.02em; }}
    .hero p {{ margin: 0; color: rgba(255, 255, 255, 0.78); font-size: 14px; }}
    .hero code {{ color: #d8f3ff; }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
      margin: 18px 0 26px;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: 0 10px 28px rgba(15, 31, 51, 0.04);
    }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .metric {{ font-size: 26px; font-weight: 750; margin-top: 6px; word-break: break-word; }}
    .hint {{ color: var(--muted); font-size: 12px; margin-top: 4px; }}
    .panel {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 22px;
      margin-top: 16px;
      box-shadow: 0 10px 28px rgba(15, 31, 51, 0.04);
      overflow-x: auto;
    }}
    .panel h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .muted {{ color: var(--muted); font-size: 13px; }}
    .count {{
      display: inline-block; min-width: 24px; padding: 1px 8px; margin-left: 6px;
      border-radius: 999px; background: #eaf0fb; color: var(--accent);
      font-size: 12px; text-align: center;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid var(--border); text-align: left; }}
    th {{ color: var(--muted); font-size: 12px; font-weight: 600; }}
    tr:last-child td {{ border-bottom: none; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .share {{ min-width: 180px; }}
    .bar {{ height: 7px; background: #e8eefb; border-radius: 999px; overflow: hidden; }}
    .bar span {{ display: block; height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), var(--accent-2)); }}
    .share small {{ color: var(--muted); }}
    .meta-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 10px; margin-bottom: 14px;
    }}
    .meta-grid div {{ background: #f8fafc; border-radius: 12px; padding: 10px 12px; }}
    .meta-grid span {{ display: block; color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.07em; }}
    .meta-grid strong {{ font-size: 13px; word-break: break-word; }}
    .badge {{ display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 12px; }}
    .badge.ok {{ background: #dcfce7; color: #166534; }}
    .badge.warn {{ background: #fef3c7; color: #92400e; }}
    .files {{ margin: 0; padding-left: 20px; }}
    .files li {{ margin: 4px 0; }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    footer {{ color: var(--muted); font-size: 12px; margin-top: 28px; text-align: center; }}
  </style>
</head>
<body>
<div class="wrap">
  <header class="hero">
    <h1>{html.escape(title)}</h1>
    <p>生成时间：{now} ｜ 结果目录：<code>{html.escape(str(results_dir))}</code></p>
  </header>
  {_render_cards(stats)}
  {_render_manifest(stats.manifest)}
  {_render_kraken(stats.kraken)}
  {_render_alpha(stats.alpha)}
  {_render_files(results_dir, report_dir, sections)}
  <footer>MICOS-2024 · 自包含 HTML 报告 · 结果解释请结合运行清单与原始数据</footer>
</div>
</body>
</html>
"""


def generate_summary_report(results_dir: Path, output_file: Path) -> None:
    """生成结果汇总 HTML 报告。"""
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if not results_dir.exists():
        raise FileNotFoundError(f"结果目录不存在: {results_dir}")

    sections: dict[str, list[Path]] = {}
    for section_name, patterns in SECTION_PATTERNS.items():
        sections[section_name] = find_files(results_dir, patterns)

    html_text = render_html(
        "MICOS-2024 结果汇总报告",
        results_dir,
        output_file.parent,
        sections,
        collect_stats(results_dir),
    )
    output_file.write_text(html_text, encoding="utf-8")


def run_summarize(results_dir: str, output_file: str) -> None:
    """执行结果汇总并生成 HTML 报告。"""
    logger.info("步骤 5: 开始生成总结报告...")
    results_path = Path(results_dir).resolve()
    output_path = Path(output_file).resolve()
    generate_summary_report(results_path, output_path)
    logger.info(f"结果报告已生成: {output_path}")

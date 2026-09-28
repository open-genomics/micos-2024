---
title: CLI 参考
---

# CLI 参考

本页对齐 `micos/cli.py` 中当前实现的 Click 命令。

## 调用模式

```bash
micos [全局选项] <命令> [命令选项]
```

也可以通过 `python -m micos.cli` 调用。

## 全局选项

| 选项 | 说明 |
| --- | --- |
| `--config` | 指定分析配置文件路径 |
| `--log-file` | 指定日志输出文件 |
| `--verbose` | 打开调试级日志 |
| `--dry-run` | 只打印计划，不真正执行 |
| `--version` | 输出版本信息 |

## `validate-config`

```bash
micos validate-config --config config/analysis.yaml
```

## `full-run`

```bash
micos full-run \
  --input-dir data/raw_input \
  --results-dir results \
  --threads 16 \
  --kneaddata-db /db/kneaddata/human_genome \
  --kraken2-db /db/kraken2/standard
```

跳过参数：`--skip-qc`、`--skip-taxonomy`、`--skip-functional`、`--skip-diversity`

可选参数：`--metadata` 指定样本元数据 TSV（`sample-id` 列与 FASTQ 文件名 join，
模板见 `config/samples.tsv.template`）。

## `run quality-control`

```bash
micos run quality-control \
  --input-dir data/raw_input \
  --output-dir results/quality_control \
  --threads 8 \
  --kneaddata-db /db/kneaddata/human_genome
```

## `run taxonomic-profiling`

```bash
micos run taxonomic-profiling \
  --input-dir results/quality_control/kneaddata \
  --output-dir results/taxonomic_profiling \
  --threads 16 \
  --kraken2-db /db/kraken2/standard \
  --confidence 0.1
```

## `run diversity-analysis`

```bash
micos run diversity-analysis \
  --input-biom results/taxonomic_profiling/feature-table.biom \
  --output-dir results/diversity_analysis
```

## `run functional-annotation`

```bash
micos run functional-annotation \
  --input-dir results/quality_control/kneaddata \
  --output-dir results/functional_annotation \
  --threads 8
```

## `run summarize-results`

```bash
micos run summarize-results \
  --results-dir results \
  --output-file results/micos_summary_report.html
```

## Shell 包装脚本

| 包装脚本 | 角色 |
| --- | --- |
| `scripts/run_full_analysis.sh` | `micos full-run` 的薄包装层 |
| `scripts/run_module.sh` | 把模块执行委托给稳定 CLI |

## 返回码

| 码 | 含义 |
| --- | --- |
| `0` | 成功 |
| `1` | 一般错误 |
| `2` | 参数无效 |
| `3` | 配置错误 |
| `4` | 缺少依赖 |
| `5` | 数据库错误 |
| `6` | I/O 错误 |
| `130` | 用户中断 |

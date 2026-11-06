---
title: 快速开始
---

# 快速开始

## 选择运行方式

| 方式 | 适用场景 | 主要入口 |
| --- | --- | --- |
| Python CLI | 本地开发、可控环境 | `micos` 或 `python -m micos.cli` |
| Shell 包装层 | 兼容旧用法 | `scripts/run_full_analysis.sh`, `scripts/run_module.sh` |
| 工作流与容器 | 实验性/部分步骤参考 | `steps/`, `containers/` |

## 安装

```bash
git clone https://github.com/open-genomics/micos-2024.git
cd micos-2024
pip install -e ".[dev]"
```

也可以使用 Conda / Mamba：

```bash
mamba env create -f environment.yml
conda activate micos-2024
pip install -e .
```

`environment.yml` 安装外部生信工具，`pip install -e .` 安装 `micos` 命令本身，两步都需要。

## 配置

```bash
cp config/analysis.yaml.template config/analysis.yaml
cp config/databases.yaml.template config/databases.yaml
cp config/samples.tsv.template config/samples.tsv
```

然后把数据库路径改成你本地真实可用的位置。

## 环境自检

```bash
micos doctor
micos doctor --json
```

`doctor` 会检查外部工具、Kraken2/KneadData 数据库路径和 Python 环境。

## 验证配置

```bash
micos validate-config --config config/analysis.yaml
```

这一步能提前发现路径和模板残留问题。

## 运行完整流程

```bash
micos full-run \
  --input-dir data/raw_input \
  --results-dir results \
  --threads 16 \
  --kneaddata-db /path/to/kneaddata_db \
  --kraken2-db /path/to/kraken2_db
```

## 使用包装脚本

```bash
./scripts/run_full_analysis.sh \
  --config config/analysis.yaml \
  --input-dir data/raw_input \
  --results-dir results
```

包装脚本委托给 CLI，在自动化或排错场景中仍建议优先使用主 CLI。

## 使用容器

```bash
sudo singularity build kraken2.sif steps/03_taxonomic_profiling_kraken/kraken2.def
```

容器定义用于锁定执行环境，不是一键全自动部署。

## 运行后查看结果

- `results/quality_control/`
- `results/taxonomic_profiling/`
- `results/diversity_analysis/`
- `results/functional_annotation/`
- `results/run_manifest.json`
- `results/micos_summary_report.html`

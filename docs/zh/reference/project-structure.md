---
title: 项目结构
---

# 项目结构

## 顶层地图

| 路径 | 职责 |
| --- | --- |
| `micos/` | 稳定 Python 包与 CLI 编排核心 |
| `config/` | 配置模板与样本元数据 |
| `steps/` | 步骤级 WDL 工作流资产 |
| `scripts/` | 包装层和主 CLI 之外的专家分析脚本 |
| `containers/` | Singularity 定义与环境资产 |
| `tests/` | Python 测试 |
| `docs/` | 文档站 |

## 稳定核心

```text
micos/
├── cli.py
├── full_run.py
├── quality_control.py
├── taxonomic_profiling.py
├── diversity_analysis.py
├── functional_annotation.py
├── summarize_results.py
├── sample.py
├── config.py
├── manifest.py
├── doctor.py
├── errors.py
└── utils.py
```

## 运行产物

```text
results/
├── run_manifest.json
├── micos_summary_report.html
├── quality_control/
├── taxonomic_profiling/
├── diversity_analysis/
└── functional_annotation/
```

## 扩展脚本

```text
scripts/
├── run_full_analysis.sh
├── run_module.sh
├── download_databases.sh
├── verify_installation.sh
├── network_analysis.py
├── phylogenetic_analysis.py
├── amplicon_analysis.py
├── metatranscriptome_analysis.py
└── differential_abundance_analysis.R
```

这棵子树既有兼容层，也有专家扩展分析。它不属于稳定公共接口。

---
title: 部署模式
---

# 部署模式

MICOS-2024 支持多种部署方式，不同模式服务于不同目标。

## 直接 Python 执行

适合本地开发、调试和已有可控 Python 环境的场景。反馈最快，与 `micos/cli.py` 对齐最直接。

## Shell 包装层执行

适合保持旧有 shell-first 工作流、渐进迁移到主 CLI 的场景。包装脚本委托给 CLI，不是独立流程实现。

## 工作流驱动执行（实验性）

适合需要 workflow engine 集成、显式表达步骤图的场景。相关资产是**实验性单步骤参考**，不是生产工作流：

- `steps/01_quality_control/fastqc.wdl`
- `steps/02_read_cleaning/kneaddata.wdl`
- `steps/03_taxonomic_profiling_kraken/kraken2.wdl`
- `steps/04_taxonomic_conversion_biom/kraken-biom.wdl`
- `steps/05_taxonomic_visualization_krona/krona.wdl`
- `steps/06_qiime2_analysis/*.wdl`

## 容器化执行（部分步骤）

适合固定依赖栈、团队交付、防止环境漂移的场景。当前只覆盖部分步骤，不是统一全流程镜像：

- `containers/singularity/*.def`

## 实践建议

1. 先用稳定 CLI 路径
2. 再用工作流资产做系统集成
3. 再用容器锁定环境
4. 包装脚本只在需要兼容旧流程时使用

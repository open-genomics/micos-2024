---
title: 故障排除
---

# 故障排除

## `validate-config` 一开始就失败

通常是以下问题：

- 模板占位符没有替换
- `config/databases.yaml` 指向了不存在的路径
- `config/analysis.yaml` 与数据库配置不一致

先运行：

```bash
micos doctor
micos validate-config --config config/analysis.yaml
```

## `full-run` 提示缺少数据库路径

稳定 CLI 需要明确提供 KneadData 和 Kraken2 数据库路径：

```bash
micos full-run \
  --kneaddata-db /db/kneaddata/human_genome \
  --kraken2-db /db/kraken2/standard
```

## 提示“未找到配对的 FASTQ 文件”或“未找到清洗后的配对样本”

当前 `full-run` 按双端流程设计：

- 原始输入命名应为 `sample_R1.fastq.gz` / `sample_R2.fastq.gz`
- KneadData 输出应包含 `sample_paired_1.fastq` / `sample_paired_2.fastq`

如果输入为空，CLI 会以退出码 6 结束，而不是生成空报告。先检查命名，再运行
`micos doctor` 确认工具和数据库路径。

## 报告里只有部分产物

检查 `results/run_manifest.json` 中各阶段状态。被 `--skip-*` 跳过的阶段不会生成产物；
失败阶段会记录 `failed` 和错误摘要。

## 包装脚本行为和预期不同

包装脚本是委托层，委托给 CLI 命令。先检查它委托到的 CLI 命令。

## 容器就绪但运行仍然失败

环境就绪不等于流程正确。Compose 示例帮助准备环境，但不能替代配置验证和命令级检查。

## 文档里提到了高级分析，但主 CLI 里找不到

这些能力可能位于 `scripts/` 而不是稳定 CLI。请结合[项目结构](./reference/project-structure)和 [CLI 参考](./reference/cli)判断它属于哪一层。

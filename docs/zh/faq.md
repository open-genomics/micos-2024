---
title: 常见问题
---

# 常见问题

## MICOS-2024 是 workflow engine 吗

不是。它是一个围绕宏基因组工具栈构建的 CLI 平台，同时包含 `steps/` 下的 WDL 工作流资产和 `containers/` 下的环境资产。

## `scripts/` 里的所有脚本都属于稳定公共接口吗

不是。很多脚本是专家扩展或探索性能力。稳定的命令面请看 [CLI 参考](./reference/cli.md)。

## 新项目应该优先用包装脚本还是 Python CLI

优先用 Python CLI。包装脚本适合兼容旧工作流，但不是新项目的事实标准。

## 为什么配置模板里没有 QC / Kraken2 confidence 这些参数

活动配置模板只保留已接入 CLI 的字段（`enforce-effective-configuration`，未知字段
`extra="forbid"` 直接拒绝）。未接入的愿景参数收纳在
[配置愿景参数路线图](./roadmap.md)，接入对应 CLI 后再移回模板。

## 从哪里开始了解项目

建议顺序：

1. [首页](./)
2. [流程基础](./academy/pipeline-foundations)
3. [系统总览](./architecture/system-overview)
4. [CLI 参考](./reference/cli)

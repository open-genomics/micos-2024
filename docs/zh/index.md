---
layout: home
hero:
  name: MICOS-2024
  text: 宏基因组分析平台
  tagline: 串联质控、物种分类、多样性分析和功能注释的一站式 Python CLI
  actions:
    - theme: brand
      text: 快速开始
      link: /zh/guides/getting-started
    - theme: alt
      text: 系统总览
      link: /zh/architecture/system-overview
    - theme: alt
      text: GitHub
      link: https://github.com/open-genomics/micos-2024
features:
  - title: 质量控制
    details: FastQC 评估 + KneadData 宿主去除
  - title: 物种分类
    details: Kraken2 分类 + kraken-biom 转换 + Krona 可视化
  - title: 多样性分析
    details: QIIME2 计算 Shannon Alpha 和 Bray-Curtis Beta 多样性
  - title: 功能注释
    details: HUMAnN 基因家族和代谢通路丰度
  - title: 结果汇总
    details: 自动生成 HTML 结果索引报告
  - title: 可追溯运行
    details: run_manifest.json + micos doctor + 自包含 HTML 报告
---

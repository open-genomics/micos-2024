---
title: 参考文献
---

# 参考文献

MICOS-2024 建立在成熟的宏基因组和微生物组工具之上。

<script setup>
const references = [
  {
    authors: 'Wood DE, Lu J, Langmead B',
    title: 'Improved metagenomic analysis with Kraken 2',
    venue: 'Genome Biology',
    year: '2019',
    link: 'https://doi.org/10.1186/s13059-019-1891-0',
    note: '物种分类模块的方法学基线。',
  },
  {
    authors: 'Bolyen E, Rideout JR, Dillon MR, et al.',
    title: 'Reproducible, interactive, scalable and extensible microbiome data science using QIIME 2',
    venue: 'Nature Biotechnology',
    year: '2019',
    link: 'https://doi.org/10.1038/s41587-019-0209-9',
    note: '多样性分析模块的基础工具。',
  },
  {
    authors: 'McIver LJ, Abu-Ali G, Franzosa EA, et al.',
    title: "bioBakery: a meta'omic analysis environment",
    venue: 'Bioinformatics',
    year: '2018',
    link: 'https://doi.org/10.1093/bioinformatics/btx754',
    note: 'KneadData 和 HUMAnN 所属的工具生态。',
  },
  {
    authors: 'Franzosa EA, McIver LJ, Rahnavard G, et al.',
    title: 'Species-level functional profiling of metagenomes and metatranscriptomes',
    venue: 'Nature Methods',
    year: '2018',
    link: 'https://doi.org/10.1038/s41592-018-0176-y',
    note: 'HUMAnN 功能注释的方法学参考。',
  },
  {
    authors: 'McMurdie PJ, Holmes S',
    title: 'phyloseq: an R package for reproducible interactive analysis and graphics of microbiome census data',
    venue: 'PLoS ONE',
    year: '2013',
    link: 'https://doi.org/10.1371/journal.pone.0061217',
    note: 'scripts/ 中 R 侧统计分析的基础。',
  },
]
</script>

## 如何引用 MICOS-2024

项目自身的引用方式请参考仓库中的 `CITATION.cff`（机器可读）和 `CITATION.md`（人读版本）。如果使用了某一分析分支，也应同时引用相应工具论文。

<ReferenceList :items="references" />

# 引用指南 (Citation Guide)

## 如何引用MICOS-2024

机器可读的引用元数据见 [`CITATION.cff`](CITATION.cff)。如果您在研究中使用了 MICOS-2024，请按照以下格式引用：

### APA格式

```
MICOS-2024 Team. (2024). MICOS-2024: Metagenomic Intelligence and Comprehensive Omics Suite. 
GitHub repository. https://github.com/open-genomics/micos-2024
```

### BibTeX格式

```bibtex
@software{micos2024,
  title = {MICOS-2024: Metagenomic Intelligence and Comprehensive Omics Suite},
  author = {{MICOS-2024 Team}},
  year = {2024},
  url = {https://github.com/open-genomics/micos-2024},
  note = {2024 "猛犸杯" 生物信息学竞赛参赛项目，现由 Open Genomics 维护}
}
```

### 学术论文格式

```
MICOS-2024 Team. MICOS-2024: A comprehensive metagenomic analysis suite for microbiome research. 
Available at: https://github.com/open-genomics/micos-2024 (2024).
```

## 相关工具引用

MICOS-2024集成了多个优秀的生物信息学工具，如果您使用了特定功能，请同时引用相关工具：

### 核心工具

**Kraken2** (分类学分类):
```
Wood, D.E., Lu, J. & Langmead, B. Improved metagenomic analysis with Kraken 2. 
Genome Biol 20, 257 (2019). https://doi.org/10.1186/s13059-019-1891-0
```

**QIIME2** (微生物组分析):
```
Bolyen, E., Rideout, J.R., Dillon, M.R. et al. Reproducible, interactive, scalable and 
extensible microbiome data science using QIIME 2. Nat Biotechnol 37, 852–857 (2019). 
https://doi.org/10.1038/s41587-019-0209-9
```

**KneadData** (质量控制):
```
McIver, L.J., Abu-Ali, G., Franzosa, E.A. et al. bioBakery: a meta'omic analysis 
environment. Bioinformatics 34, 1235–1237 (2018). 
https://doi.org/10.1093/bioinformatics/btx754
```

**Krona** (可视化):
```
Ondov, B.D., Bergman, N.H. & Phillippy, A.M. Interactive metagenomic visualization 
in a Web browser. BMC Bioinformatics 12, 385 (2011). 
https://doi.org/10.1186/1471-2105-12-385
```

### 统计分析工具

**DESeq2** (差异丰度分析):
```
Love, M.I., Huber, W. & Anders, S. Moderated estimation of fold change and dispersion 
for RNA-seq data with DESeq2. Genome Biol 15, 550 (2014). 
https://doi.org/10.1186/s13059-014-0550-8
```

**ALDEx2** (组合数据分析):
```
Fernandes, A.D., Reid, J.N., Macklaim, J.M. et al. Unifying the analysis of 
high-throughput sequencing datasets: characterizing RNA-seq, 16S rRNA gene sequencing 
and selective growth experiments by compositional data analysis. Microbiome 2, 15 (2014). 
https://doi.org/10.1186/2049-2618-2-15
```

**ANCOM-BC** (偏差校正分析):
```
Lin, H., Peddada, S.D. Analysis of compositions of microbiomes with bias correction. 
Nat Commun 11, 3514 (2020). https://doi.org/10.1038/s41467-020-17041-7
```

**Phyloseq** (R包生态分析):
```
McMurdie, P.J., Holmes, S. phyloseq: an R package for reproducible interactive analysis 
and graphics of microbiome census data. PLoS One 8, e61217 (2013). 
https://doi.org/10.1371/journal.pone.0061217
```

## 致谢

感谢华大基因举办的"猛犸杯"生物信息学竞赛为本项目提供的平台和支持。

感谢所有开源生物信息学工具的开发者和维护者，他们的贡献使得MICOS-2024的开发成为可能。

## 许可证

本项目采用MIT许可证。详细信息请参见[LICENSE](LICENSE)文件。

## 联系方式

如有引用相关问题，请通过以下方式联系：

- GitHub Issues: https://github.com/open-genomics/micos-2024/issues
- GitHub Discussions: https://github.com/open-genomics/micos-2024/discussions

---

*最后更新: 2024年*

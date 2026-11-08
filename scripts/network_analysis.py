#!/usr/bin/env python3
"""
MICOS-2024 网络分析和共现分析模块
Network Analysis and Co-occurrence Analysis Module

该模块提供微生物组网络分析功能，包括：
- 微生物共现网络构建
- 网络拓扑分析
- 关键物种识别
- 网络可视化
- 模块化分析
- 网络稳定性分析

作者: MICOS-2024 团队
版本: 1.0.0
许可证: MIT
"""

import argparse
import logging
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import yaml

# 仅抑制特定的 DeprecationWarning
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 网络分析相关库
try:
    import matplotlib.pyplot as plt
    import networkx as nx
    from scipy.stats import spearmanr, t
except ImportError as e:
    print(f"警告: 缺少必要的依赖包: {e}")

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """网络分析器"""

    def __init__(self, config_file: str, output_dir: str):
        """
        初始化网络分析器

        Args:
            config_file: 配置文件路径
            output_dir: 输出目录路径
        """
        self.config_file = config_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 加载配置
        self.config = self._load_config()

        # 设置输出子目录
        self.correlation_dir = self.output_dir / "correlation_analysis"
        self.network_dir = self.output_dir / "network_construction"
        self.topology_dir = self.output_dir / "topology_analysis"
        self.visualization_dir = self.output_dir / "visualization"
        self.modules_dir = self.output_dir / "module_analysis"

        # 创建输出目录
        for dir_path in [
            self.correlation_dir,
            self.network_dir,
            self.topology_dir,
            self.visualization_dir,
            self.modules_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> Dict:
        """加载配置文件"""
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"成功加载配置文件: {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}

    def run_correlation_analysis(
        self, abundance_file: str, method: str = "spearman"
    ) -> str:
        """
        运行相关性分析

        Args:
            abundance_file: 物种丰度文件路径
            method: 相关性计算方法 ('spearman', 'pearson')

        Returns:
            相关性矩阵文件路径
        """
        logger.info(f"开始相关性分析，使用{method}方法...")

        try:
            # 读取丰度数据
            df = pd.read_csv(abundance_file, sep="\t", index_col=0)

            # 数据预处理
            df = self._preprocess_abundance_data(df)

            # 计算相关性矩阵
            if method == "spearman":
                corr_matrix, p_values = self._calculate_spearman_correlation(df)
            elif method == "pearson":
                corr_matrix, p_values = self._calculate_pearson_correlation(df)
            else:
                raise ValueError(f"不支持的相关性方法: {method}")

            # 保存结果
            corr_file = self.correlation_dir / f"{method}_correlation_matrix.tsv"
            pval_file = self.correlation_dir / f"{method}_pvalues_matrix.tsv"

            corr_matrix.to_csv(corr_file, sep="\t")
            p_values.to_csv(pval_file, sep="\t")

            logger.info(f"相关性分析完成: {corr_file}")
            return str(corr_file)

        except Exception as e:
            logger.error(f"相关性分析失败: {e}")
            return ""

    def _preprocess_abundance_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """预处理丰度数据"""
        logger.info("预处理丰度数据...")

        # 移除低丰度物种
        min_abundance = self.config.get("network_analysis", {}).get(
            "min_abundance", 0.001
        )
        df = df[df.mean(axis=1) >= min_abundance]

        # 移除在少数样本中出现的物种
        min_prevalence = self.config.get("network_analysis", {}).get(
            "min_prevalence", 0.1
        )
        prevalence_threshold = int(df.shape[1] * min_prevalence)
        df = df[(df > 0).sum(axis=1) >= prevalence_threshold]

        # 对数转换
        df = np.log10(df + 1e-6)

        logger.info(f"预处理后保留 {df.shape[0]} 个物种")
        return df

    def _calculate_spearman_correlation(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """计算Spearman相关性"""
        logger.info("计算Spearman相关性...")

        # 一次性传入整个矩阵：scipy 只对每个变量排秩一次，再成对计算，
        # 避免旧实现每对都重复 rank 两行。
        corr_matrix, p_values = spearmanr(df.to_numpy(dtype=float).T)
        corr_matrix = np.asarray(corr_matrix, dtype=float)
        p_values = np.asarray(p_values, dtype=float)

        corr_df = pd.DataFrame(corr_matrix, index=df.index, columns=df.index)
        pval_df = pd.DataFrame(p_values, index=df.index, columns=df.index)

        return corr_df, pval_df

    def _calculate_pearson_correlation(
        self, df: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """计算Pearson相关性"""
        logger.info("计算Pearson相关性...")

        data = df.to_numpy(dtype=float)
        # np.corrcoef 一次算完整个相关矩阵；p 值仍按与 scipy.pearsonr
        # 相同的 t 近似公式向量化计算（df = 样本数 - 2）。
        corr_matrix = np.corrcoef(data)
        n_samples = data.shape[1]
        if n_samples > 2:
            with np.errstate(divide="ignore", invalid="ignore"):
                t_stat = corr_matrix * np.sqrt(
                    (n_samples - 2) / np.clip(1.0 - corr_matrix**2, 1e-300, None)
                )
            p_values = 2.0 * t.sf(np.abs(t_stat), n_samples - 2)
            p_values = np.nan_to_num(p_values, nan=1.0)
        else:
            p_values = np.ones_like(corr_matrix)
        corr_matrix = np.nan_to_num(corr_matrix, nan=0.0)
        np.fill_diagonal(corr_matrix, 1.0)
        np.fill_diagonal(p_values, 0.0)

        corr_df = pd.DataFrame(corr_matrix, index=df.index, columns=df.index)
        pval_df = pd.DataFrame(p_values, index=df.index, columns=df.index)

        return corr_df, pval_df

    def construct_network(self, correlation_file: str, pvalue_file: str) -> str:
        """
        构建共现网络

        Args:
            correlation_file: 相关性矩阵文件路径
            pvalue_file: p值矩阵文件路径

        Returns:
            网络文件路径
        """
        logger.info("构建共现网络...")

        try:
            # 读取相关性和p值矩阵
            corr_matrix = pd.read_csv(correlation_file, sep="\t", index_col=0)
            pval_matrix = pd.read_csv(pvalue_file, sep="\t", index_col=0)

            # 设置阈值
            corr_threshold = self.config.get("network_analysis", {}).get(
                "correlation_threshold", 0.6
            )
            pval_threshold = self.config.get("network_analysis", {}).get(
                "pvalue_threshold", 0.05
            )

            # 创建网络
            G = nx.Graph()

            # 添加节点
            for node in corr_matrix.index:
                G.add_node(node)

            # 添加边
            for i, node1 in enumerate(corr_matrix.index):
                for j, node2 in enumerate(corr_matrix.columns):
                    if i < j:  # 避免重复边
                        corr_val = corr_matrix.iloc[i, j]
                        pval = pval_matrix.iloc[i, j]

                        # 检查是否满足阈值条件
                        if abs(corr_val) >= corr_threshold and pval <= pval_threshold:
                            G.add_edge(
                                node1,
                                node2,
                                weight=abs(corr_val),
                                correlation=corr_val,
                                pvalue=pval,
                                edge_type="positive" if corr_val > 0 else "negative",
                            )

            # 保存网络
            network_file = self.network_dir / "cooccurrence_network.gml"
            nx.write_gml(G, network_file)

            # 保存网络统计信息
            self._save_network_stats(G)

            logger.info(f"网络构建完成: {network_file}")
            logger.info(
                f"网络包含 {G.number_of_nodes()} 个节点和 {G.number_of_edges()} 条边"
            )

            return str(network_file)

        except Exception as e:
            logger.error(f"网络构建失败: {e}")
            return ""

    def _save_network_stats(self, G: nx.Graph):
        """保存网络统计信息"""
        stats = {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": nx.density(G),
            "average_clustering": nx.average_clustering(G),
            "connected_components": nx.number_connected_components(G),
        }

        # 如果网络连通，计算更多统计信息
        if nx.is_connected(G):
            stats["average_path_length"] = nx.average_shortest_path_length(G)
            stats["diameter"] = nx.diameter(G)

        stats_file = self.network_dir / "network_statistics.yaml"
        with open(stats_file, "w") as f:
            yaml.dump(stats, f, default_flow_style=False)

        logger.info(f"网络统计信息已保存: {stats_file}")

    def analyze_network_topology(self, network_file: str) -> str:
        """
        分析网络拓扑结构

        Args:
            network_file: 网络文件路径

        Returns:
            拓扑分析结果文件路径
        """
        logger.info("分析网络拓扑结构...")

        try:
            # 加载网络
            G = nx.read_gml(network_file)

            # 计算节点中心性指标
            centrality_metrics = self._calculate_centrality_metrics(G)

            # 检测网络模块
            modules = self._detect_network_modules(G)

            # 识别关键节点
            key_nodes = self._identify_key_nodes(G, centrality_metrics)

            # 保存拓扑分析结果
            topology_file = self.topology_dir / "topology_analysis.tsv"
            centrality_df = pd.DataFrame(centrality_metrics)
            centrality_df.to_csv(topology_file, sep="\t")

            # 保存模块信息
            modules_file = self.modules_dir / "network_modules.tsv"
            modules_df = pd.DataFrame(list(modules.items()), columns=["Node", "Module"])
            modules_df.to_csv(modules_file, sep="\t", index=False)

            # 保存关键节点信息
            key_nodes_file = self.topology_dir / "key_nodes.tsv"
            key_nodes_df = pd.DataFrame(key_nodes)
            key_nodes_df.to_csv(key_nodes_file, sep="\t", index=False)

            logger.info(f"拓扑分析完成: {topology_file}")
            return str(topology_file)

        except Exception as e:
            logger.error(f"拓扑分析失败: {e}")
            return ""

    def _calculate_centrality_metrics(self, G: nx.Graph) -> Dict:
        """计算节点中心性指标"""
        logger.info("计算节点中心性指标...")

        centrality_metrics = {
            "node": list(G.nodes()),
            "degree_centrality": list(nx.degree_centrality(G).values()),
            "betweenness_centrality": list(nx.betweenness_centrality(G).values()),
            "closeness_centrality": list(nx.closeness_centrality(G).values()),
            "eigenvector_centrality": list(
                nx.eigenvector_centrality(G, max_iter=1000).values()
            ),
            "clustering_coefficient": list(nx.clustering(G).values()),
        }

        return centrality_metrics

    def _detect_network_modules(self, G: nx.Graph) -> Dict:
        """检测网络模块"""
        logger.info("检测网络模块...")

        try:
            import community as community_louvain

            # 使用Louvain算法检测社区
            partition = community_louvain.best_partition(G)
            return partition
        except ImportError:
            logger.warning("未安装python-louvain包，跳过模块检测")
            return {}

    def _identify_key_nodes(self, G: nx.Graph, centrality_metrics: Dict) -> List[Dict]:
        """识别关键节点"""
        logger.info("识别关键节点...")

        # 计算综合重要性分数
        nodes = centrality_metrics["node"]
        degree_cent = centrality_metrics["degree_centrality"]
        between_cent = centrality_metrics["betweenness_centrality"]
        close_cent = centrality_metrics["closeness_centrality"]

        key_nodes = []
        for i, node in enumerate(nodes):
            # 综合分数 = 度中心性 + 介数中心性 + 接近中心性
            composite_score = degree_cent[i] + between_cent[i] + close_cent[i]

            key_nodes.append(
                {
                    "node": node,
                    "degree_centrality": degree_cent[i],
                    "betweenness_centrality": between_cent[i],
                    "closeness_centrality": close_cent[i],
                    "composite_score": composite_score,
                }
            )

        # 按综合分数排序
        key_nodes.sort(key=lambda x: x["composite_score"], reverse=True)

        return key_nodes

    def visualize_network(self, network_file: str, layout: str = "spring") -> str:
        """
        可视化网络

        Args:
            network_file: 网络文件路径
            layout: 布局算法

        Returns:
            可视化文件路径
        """
        logger.info("生成网络可视化...")

        try:
            # 加载网络
            G = nx.read_gml(network_file)

            # 设置图形大小
            plt.figure(figsize=(15, 12))

            # 选择布局算法
            if layout == "spring":
                pos = nx.spring_layout(G, k=1, iterations=50)
            elif layout == "circular":
                pos = nx.circular_layout(G)
            elif layout == "kamada_kawai":
                pos = nx.kamada_kawai_layout(G)
            else:
                pos = nx.spring_layout(G)

            # 绘制节点
            node_sizes = [G.degree(node) * 50 for node in G.nodes()]
            nx.draw_networkx_nodes(
                G, pos, node_size=node_sizes, node_color="lightblue", alpha=0.7
            )

            # 绘制边
            positive_edges = [
                (u, v)
                for u, v, d in G.edges(data=True)
                if d.get("edge_type") == "positive"
            ]
            negative_edges = [
                (u, v)
                for u, v, d in G.edges(data=True)
                if d.get("edge_type") == "negative"
            ]

            nx.draw_networkx_edges(
                G, pos, edgelist=positive_edges, edge_color="green", alpha=0.6, width=1
            )
            nx.draw_networkx_edges(
                G,
                pos,
                edgelist=negative_edges,
                edge_color="red",
                alpha=0.6,
                width=1,
                style="dashed",
            )

            # 添加标签（仅对度较高的节点）
            high_degree_nodes = [node for node in G.nodes() if G.degree(node) > 5]
            labels = {node: node for node in high_degree_nodes}
            nx.draw_networkx_labels(G, pos, labels, font_size=8)

            plt.title("Microbial Co-occurrence Network", fontsize=16, fontweight="bold")
            plt.axis("off")

            # 添加图例
            from matplotlib.lines import Line2D

            legend_elements = [
                Line2D([0], [0], color="green", lw=2, label="Positive correlation"),
                Line2D(
                    [0],
                    [0],
                    color="red",
                    lw=2,
                    linestyle="--",
                    label="Negative correlation",
                ),
            ]
            plt.legend(handles=legend_elements, loc="upper right")

            # 保存图形
            viz_file = self.visualization_dir / "network_visualization.png"
            plt.savefig(viz_file, dpi=300, bbox_inches="tight")
            plt.close()

            logger.info(f"网络可视化完成: {viz_file}")
            return str(viz_file)

        except Exception as e:
            logger.error(f"网络可视化失败: {e}")
            return ""

    def generate_network_report(self, network_file: str) -> str:
        """
        生成网络分析报告

        Args:
            network_file: 网络文件路径

        Returns:
            报告文件路径
        """
        logger.info("生成网络分析报告...")

        try:
            # 加载网络
            G = nx.read_gml(network_file)

            # 生成HTML报告
            html_content = self._create_network_html_report(G)

            # 保存报告
            report_file = self.output_dir / "network_analysis_report.html"
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info(f"网络分析报告已生成: {report_file}")
            return str(report_file)

        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return ""

    def _create_network_html_report(self, G: nx.Graph) -> str:
        """创建HTML报告"""
        html_content = f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>MICOS-2024 网络分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; background-color: #f0f0f0; padding: 20px; }}
                .section {{ margin: 20px 0; }}
                .stats {{ background-color: #e8f4fd; padding: 15px; border-radius: 5px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .visualization {{ text-align: center; margin: 20px 0; }}
                .visualization img {{ max-width: 100%; height: auto; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>MICOS-2024 网络分析报告</h1>
                <p>生成时间: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>

            <div class="section">
                <h2>网络基本统计</h2>
                <div class="stats">
                    <p><strong>节点数:</strong> {G.number_of_nodes()}</p>
                    <p><strong>边数:</strong> {G.number_of_edges()}</p>
                    <p><strong>网络密度:</strong> {nx.density(G):.4f}</p>
                    <p><strong>平均聚类系数:</strong> {nx.average_clustering(G):.4f}</p>
                    <p><strong>连通分量数:</strong> {nx.number_connected_components(G)}</p>
                </div>
            </div>

            <div class="section">
                <h2>网络可视化</h2>
                <div class="visualization">
                    <img src="visualization/network_visualization.png" alt="Network Visualization">
                </div>
            </div>

            <div class="section">
                <h2>分析文件</h2>
                <ul>
                    <li><a href="topology_analysis/topology_analysis.tsv">拓扑分析结果</a></li>
                    <li><a href="topology_analysis/key_nodes.tsv">关键节点信息</a></li>
                    <li><a href="module_analysis/network_modules.tsv">网络模块信息</a></li>
                    <li><a href="network_construction/network_statistics.yaml">网络统计信息</a></li>
                </ul>
            </div>
        </body>
        </html>
        """

        return html_content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MICOS-2024 网络分析和共现分析")
    parser.add_argument("-c", "--config", required=True, help="配置文件路径")
    parser.add_argument("-i", "--input", required=True, help="物种丰度文件路径")
    parser.add_argument("-o", "--output", required=True, help="输出目录路径")
    parser.add_argument(
        "--method",
        choices=["spearman", "pearson"],
        default="spearman",
        help="相关性计算方法",
    )
    parser.add_argument(
        "--mode",
        choices=["correlation", "network", "complete"],
        default="complete",
        help="分析模式",
    )
    parser.add_argument(
        "--layout",
        choices=["spring", "circular", "kamada_kawai"],
        default="spring",
        help="网络布局算法",
    )

    args = parser.parse_args()

    # 创建分析器
    analyzer = NetworkAnalyzer(args.config, args.output)

    # 根据模式运行分析
    if args.mode == "correlation":
        corr_file = analyzer.run_correlation_analysis(args.input, args.method)
        logger.info(f"相关性分析完成: {corr_file}")

    elif args.mode == "network":
        logger.error("网络模式需要先运行相关性分析")
        sys.exit(1)

    elif args.mode == "complete":
        # 运行完整分析流程
        logger.info("开始完整网络分析流程...")

        # 1. 相关性分析
        corr_file = analyzer.run_correlation_analysis(args.input, args.method)
        if not corr_file:
            logger.error("相关性分析失败")
            sys.exit(1)

        # 2. 构建网络
        pval_file = corr_file.replace("correlation_matrix", "pvalues_matrix")
        network_file = analyzer.construct_network(corr_file, pval_file)
        if not network_file:
            logger.error("网络构建失败")
            sys.exit(1)

        # 3. 拓扑分析
        topology_file = analyzer.analyze_network_topology(network_file)
        if topology_file:
            logger.info(f"拓扑分析完成: {topology_file}")

        # 4. 网络可视化
        viz_file = analyzer.visualize_network(network_file, args.layout)
        if viz_file:
            logger.info(f"网络可视化完成: {viz_file}")

        # 5. 生成报告
        report_file = analyzer.generate_network_report(network_file)
        if report_file:
            logger.info(f"分析报告生成完成: {report_file}")

    logger.info("网络分析完成")
    print(f"结果已保存到: {args.output}")


if __name__ == "__main__":
    main()

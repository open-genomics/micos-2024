# MICOS-2024: Metagenomic Intelligence and Comprehensive Omics Suite

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("micos-2024")
except (PackageNotFoundError, RuntimeError):
    # 源码目录直接运行、或环境中存在重复 editable 安装时使用发布版本回退。
    __version__ = "1.2.0"

__all__ = ["__version__"]

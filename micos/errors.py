# -*- coding: utf-8 -*-
"""MICOS 运行时错误类型。"""

from __future__ import annotations


class MicosError(Exception):
    """所有可预期 MICOS 错误的基类。"""

    exit_code = 1


class NoSamplesError(MicosError):
    """输入目录中没有发现可处理的样本。"""

    exit_code = 6


class MissingInputError(MicosError):
    """阶段所需的上游输入文件不存在。"""

    exit_code = 6


class StageOutputError(MicosError):
    """阶段执行完成但没有生成预期产物。"""

    exit_code = 1

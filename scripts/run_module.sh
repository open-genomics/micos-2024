#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="$PROJECT_ROOT/config/analysis.yaml"
RESULTS_DIR=""
THREADS=""
MODULE=""

show_usage() {
    echo "用法: $0 <module_name> [options]"
    echo ""
    echo "当前支持并委托给 micos CLI 的模块:"
    echo "  quality_control      - 运行质量控制分析"
    echo "  taxonomic_profiling  - 运行物种分类分析"
    echo "  diversity_analysis   - 运行多样性分析"
    echo "  functional_annotation- 运行功能注释分析"
    echo "  summarize_results    - 汇总结果并生成 HTML 报告"
    echo "  report_generation    - summarize_results 的兼容别名"
    echo ""
    echo "选项:"
    echo "  -c, --config FILE    指定配置文件 (默认: config/analysis.yaml)"
    echo "  -o, --output DIR     指定结果目录 (默认取配置中的 output_dir 或 results/)"
    echo "  -t, --threads NUM    指定线程数 (默认取配置中的 max_threads 或 16)"
    echo "  -h, --help           显示此帮助信息"
}

run_micos() {
    if command -v micos >/dev/null 2>&1; then
        micos "$@"
    else
        PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 -m micos.cli "$@"
    fi
}

load_defaults() {
    local config_arg="$1"
    DEFAULT_INPUT_DIR=""
    DEFAULT_RESULTS_DIR=""
    DEFAULT_THREADS=""
    DEFAULT_KNEADDATA_DB=""
    DEFAULT_KRAKEN2_DB=""

    # 配置缺失时不要因为 set -e 在读取默认值阶段静默退出；
    # 交给各模块的 require_value 给出可操作的提示。
    if [[ ! -f "$config_arg" ]]; then
        return 0
    fi

    local defaults
    if ! defaults=$(PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}" python3 - "$config_arg" <<'PY'
from micos.utils import get_full_run_defaults
import sys
config_path = sys.argv[1] if len(sys.argv) > 1 else None
defaults = get_full_run_defaults(config_path)
print(defaults.get('input_dir', ''), defaults.get('results_dir', ''), defaults.get('threads', ''), defaults.get('kneaddata_db', ''), defaults.get('kraken2_db', ''), sep='\t')
PY
    ); then
        echo "警告: 无法读取配置 $config_arg，使用空默认值。" >&2
        return 0
    fi

    IFS=$'\t' read -r DEFAULT_INPUT_DIR DEFAULT_RESULTS_DIR DEFAULT_THREADS DEFAULT_KNEADDATA_DB DEFAULT_KRAKEN2_DB <<< "$defaults"
}

require_value() {
    local value="$1"
    local message="$2"
    if [[ -z "$value" ]]; then
        echo "$message" >&2
        exit 1
    fi
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -o|--output)
            RESULTS_DIR="$2"
            shift 2
            ;;
        -t|--threads)
            THREADS="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            if [[ -z "$MODULE" ]]; then
                MODULE="$1"
                shift
            else
                echo "未知参数: $1" >&2
                show_usage
                exit 1
            fi
            ;;
    esac
done

if [[ -z "$MODULE" ]]; then
    echo "请指定要运行的模块。" >&2
    show_usage
    exit 1
fi

case "$MODULE" in
    quality_control|taxonomic_profiling|diversity_analysis|functional_annotation|summarize_results|report_generation)
        ;;
    *)
        echo "模块 '$MODULE' 当前未纳入稳定 Shell 包装层。请直接使用 micos CLI，或先实现对应 Python 主链路后再开放。" >&2
        exit 1
        ;;
esac

load_defaults "$CONFIG_FILE"
INPUT_DIR="${DEFAULT_INPUT_DIR:-$PROJECT_ROOT/data/raw_input}"
RESULTS_DIR="${RESULTS_DIR:-${DEFAULT_RESULTS_DIR:-$PROJECT_ROOT/results}}"
THREADS="${THREADS:-${DEFAULT_THREADS:-16}}"
KNEADDATA_DB="${DEFAULT_KNEADDATA_DB:-}"
KRAKEN2_DB="${DEFAULT_KRAKEN2_DB:-}"

case "$MODULE" in
    quality_control)
        require_value "$KNEADDATA_DB" "质量控制模块需要 KneadData 数据库路径，请在配置中设置或改用 micos full-run。"
        run_micos --config "$CONFIG_FILE" run quality-control \
            --input-dir "$INPUT_DIR" \
            --output-dir "$RESULTS_DIR/quality_control" \
            --threads "$THREADS" \
            --kneaddata-db "$KNEADDATA_DB"
        ;;
    taxonomic_profiling)
        require_value "$KRAKEN2_DB" "物种分类模块需要 Kraken2 数据库路径，请在配置中设置或改用 micos full-run。"
        run_micos --config "$CONFIG_FILE" run taxonomic-profiling \
            --input-dir "$RESULTS_DIR/quality_control/kneaddata" \
            --output-dir "$RESULTS_DIR/taxonomic_profiling" \
            --threads "$THREADS" \
            --kraken2-db "$KRAKEN2_DB"
        ;;
    diversity_analysis)
        run_micos --config "$CONFIG_FILE" run diversity-analysis \
            --input-biom "$RESULTS_DIR/taxonomic_profiling/feature-table.biom" \
            --output-dir "$RESULTS_DIR/diversity_analysis"
        ;;
    functional_annotation)
        run_micos --config "$CONFIG_FILE" run functional-annotation \
            --input-dir "$RESULTS_DIR/quality_control/kneaddata" \
            --output-dir "$RESULTS_DIR/functional_annotation" \
            --threads "$THREADS"
        ;;
    summarize_results|report_generation)
        run_micos --config "$CONFIG_FILE" run summarize-results \
            --results-dir "$RESULTS_DIR" \
            --output-file "$RESULTS_DIR/micos_summary_report.html"
        ;;
esac

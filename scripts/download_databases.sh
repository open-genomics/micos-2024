#!/bin/bash
# MICOS-2024 数据库下载脚本
# 用于下载常用的分析数据库

set -e

# 默认数据库目录
DB_ROOT="${MICOS_DB_ROOT:-$HOME/micos_databases}"
THREADS="${THREADS:-8}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建目录
mkdir -p "$DB_ROOT"

# 下载 Kraken2 数据库
download_kraken2() {
    local db_type=$1
    local db_name=$2
    local db_url=$3
    local expected_sha=${4:-}

    log_info "下载 Kraken2 $db_name 数据库..."
    local target_dir="$DB_ROOT/kraken2/$db_type"

    if [ -d "$target_dir" ]; then
        log_warn "目录已存在: $target_dir"
        read -p "是否覆盖? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "跳过 $db_name"
            return
        fi
        rm -rf "$target_dir"
    fi

    mkdir -p "$target_dir"
    cd "$target_dir"

    wget -q --show-progress "$db_url" -O "${db_type}.tar.gz"

    # 校验下载完整性：优先使用调用方提供的 SHA256；未提供时明确警告，
    # 避免把"解压了但内容不可信"当成成功。
    if [ -n "$expected_sha" ]; then
        local actual_sha
        actual_sha=$(sha256sum "${db_type}.tar.gz" | awk '{print $1}')
        if [ "$actual_sha" != "$expected_sha" ]; then
            log_error "SHA256 校验失败: 期望 $expected_sha，实际 $actual_sha"
            rm -f "${db_type}.tar.gz"
            return 1
        fi
        log_info "SHA256 校验通过"
    else
        log_warn "未提供 ${db_name} 的 SHA256，跳过完整性校验；"
        log_warn "可通过 MICOS_KRAKEN2_${db_type^^}_SHA256 环境变量指定。"
    fi

    tar -xzf "${db_type}.tar.gz"
    rm "${db_type}.tar.gz"

    log_info "Kraken2 $db_name 数据库下载完成: $target_dir"
}

# 下载 HUMAnN 数据库
download_humann() {
    log_info "下载 HUMAnN 数据库..."
    local target_dir="$DB_ROOT/humann"

    if ! command -v humann &> /dev/null; then
        log_error "HUMAnN 未安装，请先安装 HUMAnN"
        return 1
    fi

    humann_databases --download chocophlan full "$target_dir"
    humann_databases --download uniref diamond_databases "$target_dir"

    log_info "HUMAnN 数据库下载完成: $target_dir"
}

# 下载 KneadData 数据库
download_kneaddata() {
    local db_name=$1

    log_info "下载 KneadData $db_name 数据库..."
    local target_dir="$DB_ROOT/kneaddata/$db_name"

    if ! command -v kneaddata_database &> /dev/null; then
        log_error "KneadData 未安装，请先安装 KneadData"
        return 1
    fi

    mkdir -p "$target_dir"
    kneaddata_database --download "$db_name" "$target_dir"

    log_info "KneadData $db_name 数据库下载完成: $target_dir"
}

# 显示帮助
show_help() {
    echo "MICOS-2024 数据库下载脚本"
    echo ""
    echo "用法: $0 [选项] [数据库类型]"
    echo ""
    echo "数据库类型:"
    echo "  kraken2-minikraken   MiniKraken2 数据库 (~8GB)"
    echo "  kraken2-standard     Kraken2 标准数据库 (~40GB)"
    echo "  kraken2-pluspf       Kraken2 PlusPF 数据库 (~70GB)"
    echo "  humann               HUMAnN 数据库"
    echo "  kneaddata-human      KneadData 人类基因组数据库"
    echo "  all                  下载所有数据库"
    echo ""
    echo "环境变量:"
    echo "  MICOS_DB_ROOT        数据库根目录 (默认: ~/micos_databases)"
    echo "  THREADS              并行线程数 (默认: 8)"
    echo "  MICOS_KRAKEN2_MINIKRAKEN_SHA256 / _STANDARD_SHA256 / _PLUSPF_SHA256"
    echo "                       对应数据库 tar.gz 的 SHA256；提供后下载即校验"
    echo ""
    echo "示例:"
    echo "  $0 kraken2-minikraken"
    echo "  MICOS_DB_ROOT=/data/dbs $0 all"
}

# 主程序
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi

    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        kraken2-minikraken)
            download_kraken2 "minikraken" "MiniKraken2" \
                "https://genome-idx.s3.amazonaws.com/kraken/minikraken2_v2_8GB.tar.gz" \
                "${MICOS_KRAKEN2_MINIKRAKEN_SHA256:-}"
            ;;
        kraken2-standard)
            download_kraken2 "standard" "Standard" \
                "https://genome-idx.s3.amazonaws.com/kraken/kraken2_standard_20230605.tar.gz" \
                "${MICOS_KRAKEN2_STANDARD_SHA256:-}"
            ;;
        kraken2-pluspf)
            download_kraken2 "pluspf" "PlusPF" \
                "https://genome-idx.s3.amazonaws.com/kraken/Kraken2%20PlusPF%20%2820231230%29.tar.gz" \
                "${MICOS_KRAKEN2_PLUSPF_SHA256:-}"
            ;;
        humann)
            download_humann
            ;;
        kneaddata-human)
            download_kneaddata "human_genome"
            ;;
        all)
            log_info "下载所有数据库..."
            download_kraken2 "minikraken" "MiniKraken2" \
                "https://genome-idx.s3.amazonaws.com/kraken/minikraken2_v2_8GB.tar.gz" \
                "${MICOS_KRAKEN2_MINIKRAKEN_SHA256:-}"
            download_humann
            download_kneaddata "human_genome"
            ;;
        *)
            log_error "未知数据库类型: $1"
            show_help
            exit 1
            ;;
    esac

    log_info "数据库下载完成！"
    log_info "请更新 config/databases.yaml 中的路径: $DB_ROOT"
}

main "$@"

#!/bin/bash

# MICOS-2024 安装验证脚本
# 作者: MICOS-2024 团队
# 版本: 1.0.0

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 计数器
PASSED=0
FAILED=0
TOTAL=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    PASSED=$((PASSED + 1))
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    FAILED=$((FAILED + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# 测试函数
test_command() {
    local cmd=$1
    local name=$2
    TOTAL=$((TOTAL + 1))
    
    if command -v "$cmd" &> /dev/null; then
        local version=$($cmd --version 2>/dev/null | head -n1 || echo "版本未知")
        log_success "$name 已安装 ($version)"
    else
        log_error "$name 未找到"
    fi
}

test_python_package() {
    local package=$1
    local name=$2
    TOTAL=$((TOTAL + 1))
    
    if python -c "import $package" 2>/dev/null; then
        local version=$(python -c "import $package; print(getattr($package, '__version__', '版本未知'))" 2>/dev/null)
        log_success "$name 已安装 ($version)"
    else
        log_error "$name 未安装"
    fi
}

test_r_package() {
    local package=$1
    local name=$2
    TOTAL=$((TOTAL + 1))
    
    if R -e "library($package)" &>/dev/null; then
        log_success "$name (R包) 已安装"
    else
        log_error "$name (R包) 未安装"
    fi
}

test_docker_image() {
    local image=$1
    local name=$2
    TOTAL=$((TOTAL + 1))
    
    if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "$image"; then
        log_success "$name Docker镜像已存在"
    else
        log_warning "$name Docker镜像未找到 (可选)"
    fi
}

# 显示标题
show_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                MICOS-2024 安装验证                          ║"
    echo "║              检查所有依赖和工具安装状态                     ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
}

# 系统信息
show_system_info() {
    log_info "系统信息检查..."
    echo "  操作系统: $(uname -s) $(uname -r)"
    echo "  架构: $(uname -m)"
    echo "  内存: $(free -h 2>/dev/null | awk '/^Mem:/ {print $2}' || echo '未知')"
    echo "  磁盘空间: $(df -h . | awk 'NR==2 {print $4}') 可用"
    echo ""
}

# 核心工具检查
check_core_tools() {
    log_info "检查核心生物信息学工具..."
    
    test_command "fastqc" "FastQC"
    test_command "kneaddata" "KneadData"
    test_command "kraken2" "Kraken2"
    test_command "kraken-biom" "Kraken-BIOM"
    test_command "ktImportTaxonomy" "Krona"
    test_command "qiime" "QIIME2"
    test_command "humann" "HUMAnN"
    
    echo ""
}

# Python包检查
check_python_packages() {
    log_info "检查Python包..."
    
    test_command "micos" "MICOS CLI"
    test_python_package "numpy" "NumPy"
    test_python_package "pandas" "Pandas"
    test_python_package "scipy" "SciPy"
    test_python_package "matplotlib" "Matplotlib"
    test_python_package "seaborn" "Seaborn"
    test_python_package "sklearn" "Scikit-learn"
    test_python_package "Bio" "Biopython"
    
    echo ""
}

# R包检查
check_r_packages() {
    log_info "检查R包..."
    
    if command -v R &> /dev/null; then
        test_r_package "ggplot2" "ggplot2"
        test_r_package "dplyr" "dplyr"
        test_r_package "phyloseq" "phyloseq"
        test_r_package "DESeq2" "DESeq2"
        test_r_package "biomformat" "biomformat"
    else
        log_error "R 未安装"
        TOTAL=$((TOTAL + 5))
        FAILED=$((FAILED + 5))
    fi
    
    echo ""
}

# 容器检查
check_containers() {
    log_info "检查Docker容器..."
    
    if command -v docker &> /dev/null; then
        test_docker_image "biocontainers/fastqc" "FastQC"
        test_docker_image "micos-kneaddata:0.12.0" "KneadData"
        test_docker_image "micos-kraken2:2.1.3" "Kraken2"
        test_docker_image "micos-kraken-biom:1.2.0" "Kraken-BIOM"
        test_docker_image "micos-krona:2.8.1" "Krona"
        test_docker_image "quay.io/qiime2/metagenome:2024.5" "QIIME2"
    else
        log_warning "Docker 未安装，跳过容器检查"
    fi
    
    echo ""
}

# 工作流引擎检查（可选）
check_workflow_engines() {
    log_info "检查工作流引擎（可选）..."

    if command -v cromwell &> /dev/null; then
        log_success "Cromwell 已安装（WDL 工作流可选）"
    else
        log_warning "Cromwell 未安装（仅在运行 WDL 工作流时需要）"
    fi

    echo ""
}

# 文件系统检查
check_filesystem() {
    log_info "检查项目文件结构..."
    TOTAL=$((TOTAL + 1))
    
    local required_dirs=("docs" "scripts" "steps" "config")
    local missing_dirs=()
    
    for dir in "${required_dirs[@]}"; do
        if [ ! -d "$dir" ]; then
            missing_dirs+=("$dir")
        fi
    done
    
    if [ ${#missing_dirs[@]} -eq 0 ]; then
        log_success "项目目录结构完整"
    else
        log_error "缺少目录: ${missing_dirs[*]}"
    fi
    
    # 检查关键文件
    TOTAL=$((TOTAL + 1))
    local required_files=("README.md" "environment.yml")
    local missing_files=()
    
    for file in "${required_files[@]}"; do
        if [ ! -f "$file" ]; then
            missing_files+=("$file")
        fi
    done
    
    if [ ${#missing_files[@]} -eq 0 ]; then
        log_success "关键文件完整"
    else
        log_error "缺少文件: ${missing_files[*]}"
    fi
    
    echo ""
}

# 性能测试
run_performance_test() {
    log_info "运行性能测试..."
    
    # 测试Python性能
    TOTAL=$((TOTAL + 1))
    local python_time=$(python -c "
import time
import numpy as np
start = time.time()
a = np.random.rand(1000, 1000)
b = np.random.rand(1000, 1000)
c = np.dot(a, b)
end = time.time()
print(f'{end - start:.2f}')
" 2>/dev/null || echo "999")
    
    if (( $(echo "$python_time < 5.0" | bc -l 2>/dev/null || echo 0) )); then
        log_success "Python性能测试通过 (${python_time}s)"
    else
        log_warning "Python性能较慢 (${python_time}s)"
    fi
    
    # 测试内存
    TOTAL=$((TOTAL + 1))
    local available_mem=$(free -m 2>/dev/null | awk '/^Mem:/ {print $7}' || echo 0)
    if [ "$available_mem" -gt 8000 ]; then
        log_success "可用内存充足 (${available_mem}MB)"
    else
        log_warning "可用内存不足 (${available_mem}MB)"
    fi
    
    echo ""
}

# 生成报告
generate_report() {
    echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                        验证报告                              ║${NC}"
    echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "总计测试: $TOTAL"
    echo -e "通过: ${GREEN}$PASSED${NC}"
    echo -e "失败: ${RED}$FAILED${NC}"
    echo ""
    
    local success_rate=$(( PASSED * 100 / TOTAL ))
    
    if [ "$success_rate" -ge 90 ]; then
        echo -e "${GREEN}✅ 安装验证通过！成功率: ${success_rate}%${NC}"
        echo -e "${GREEN}🚀 MICOS-2024 已准备就绪！${NC}"
    elif [ "$success_rate" -ge 70 ]; then
        echo -e "${YELLOW}⚠️  安装基本完成，但有一些问题。成功率: ${success_rate}%${NC}"
        echo -e "${YELLOW}💡 建议检查失败的组件${NC}"
    else
        echo -e "${RED}❌ 安装验证失败！成功率: ${success_rate}%${NC}"
        echo -e "${RED}🔧 请重新安装或检查依赖${NC}"
    fi
    
    echo ""
    echo "详细日志已保存到: verification_$(date +%Y%m%d_%H%M%S).log"
}

# 主函数
main() {
    # 重定向输出到日志文件
    exec > >(tee "verification_$(date +%Y%m%d_%H%M%S).log")
    exec 2>&1
    
    show_header
    show_system_info
    check_core_tools
    check_python_packages
    check_r_packages
    check_containers
    check_workflow_engines
    check_filesystem
    run_performance_test
    generate_report
}

# 运行主函数
main "$@"

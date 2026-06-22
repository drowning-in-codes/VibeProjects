#!/bin/bash

echo "================================"
echo "autoTwit 安装脚本"
echo "================================"
echo ""

# 检查 Python 版本
echo "1. 检查 Python 版本..."
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "   当前 Python 版本: $python_version"

if ! command -v python &> /dev/null; then
    echo "   ❌ 未找到 Python，请先安装 Python 3.11+"
    exit 1
fi

# 检查 Node.js 版本
echo ""
echo "2. 检查 Node.js 版本..."
if ! command -v node &> /dev/null; then
    echo "   ❌ 未找到 Node.js，请先安装 Node.js 18+"
    exit 1
fi

node_version=$(node --version)
echo "   当前 Node.js 版本: $node_version"

# 创建虚拟环境
echo ""
echo "3. 创建 Python 虚拟环境..."
if [ ! -d "venv" ]; then
    python -m venv venv
    echo "   ✅ 虚拟环境创建完成"
else
    echo "   ℹ️  虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo ""
echo "4. 安装 Python 依赖..."
if [ -f "venv/Scripts/activate" ]; then
    # Windows
    source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
    # Linux/Mac
    source venv/bin/activate
fi

pip install -r requirements.txt
echo "   ✅ Python 依赖安装完成"

# 安装 Node.js 依赖
echo ""
echo "5. 安装 XActions..."
npm install
echo "   ✅ XActions 安装完成"

# 创建配置文件
echo ""
echo "6. 初始化配置..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "   ✅ 已创建 .env 文件，请编辑并填入你的配置"
else
    echo "   ℹ️  .env 文件已存在"
fi

# 创建必要的目录
mkdir -p data logs

echo ""
echo "================================"
echo "安装完成！"
echo "================================"
echo ""
echo "下一步："
echo "1. 编辑 .env 文件，填入 X_AUTH_TOKEN 和 ANTHROPIC_API_KEY"
echo "2. 编辑 config.yaml，设置目标用户"
echo "3. 测试爬取: python main.py crawl <username>"
echo "4. 启动系统: python main.py start"
echo ""
echo "详细文档请查看 README.md"

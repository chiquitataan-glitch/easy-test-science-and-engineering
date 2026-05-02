#!/bin/bash
set -e

echo "=== V0.5 部署脚本 ==="
echo ""

BRANCH=${1:-develop}
echo "[1/5] 拉取最新代码 (分支: $BRANCH)..."
git fetch origin
git checkout $BRANCH
git pull origin $BRANCH

echo "[2/5] 备份数据库..."
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U ${POSTGRES_USER:-easy_test} ${POSTGRES_DB:-easy_test} > data/backups/backup_$(date +%Y%m%d_%H%M%S).sql 2>/dev/null || echo "  (跳过：数据库未运行或首次部署)"

echo "[3/5] 重新构建镜像..."
docker compose -f docker-compose.prod.yml build --no-cache backend nginx

echo "[4/5] 重启服务..."
docker compose -f docker-compose.prod.yml up -d --remove-orphans

echo "[5/5] 等待健康检查..."
sleep 10
docker compose -f docker-compose.prod.yml ps

echo ""
echo "=== 部署完成 ==="
echo "检查状态: docker compose -f docker-compose.prod.yml ps"
echo "查看日志: docker compose -f docker-compose.prod.yml logs -f"

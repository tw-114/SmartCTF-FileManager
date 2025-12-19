测试：
启动：docker compose up --build（后台：docker compose ps）
查看状态：docker compose ps
日志：docker compose logs -f backend
docker compose logs -f db
停止但保留数据库卷（数据还在）：docker compose down
停止并连同数据库数据一起清空（会删除 volume，下一次会重新初始化）：docker compose down -v

# 设置 HTTP 代理
$env:HTTP_PROXY = "http://127.0.0.1:7897"
# 设置 HTTPS 代理
$env:HTTPS_PROXY = "http://127.0.0.1:7897"
# （可选）设置不需要代理的地址（如本地服务）
$env:NO_PROXY = "localhost,127.0.0.1,*.local"

# 停止并删除旧容器
docker compose down

# 重新构建（确保依赖更新）
docker compose up --build -d

# 查看日志确认是否正常
docker compose logs -f backend
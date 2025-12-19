# 邮件转钉钉通知服务

## 部署步骤

1. 配置
```bash
cp config/config.json.example config/config.json
# 编辑 config/config.json 填入你的配置
```

2. 启动
```bash
docker-compose up -d
```

3. 查看日志
```bash
docker-compose logs -f
```

4. 停止
```bash
docker-compose stop
```

## 自定义检查间隔

修改 docker-compose.yml 添加 command:
```yaml
command: ["python", "main.py", "-c", "/app/config/config.json", "-d", "-i", "30"]
```

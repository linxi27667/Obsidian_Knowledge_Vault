---
title: Docker 学习笔记
tags: [docker, 容器, 运维]
created: 2026-05-04
source: 菜鸟教程 + 实践
---

# Docker 学习笔记

## 一、Docker 是什么

Docker 是一个开源的**应用容器引擎**，基于 Go 语言开发。它把应用和依赖打包成**镜像**，然后随时随地运行成**容器**。

### 核心优势

| 优势 | 说明 |
|------|------|
| 环境一致 | 开发、测试、生产运行环境完全一致 |
| 轻量快速 | 容器直接运行于宿主机内核，无需完整操作系统 |
| 快速部署 | 秒级启动，比虚拟机快得多 |
| 隔离安全 | 容器之间相互隔离，互不影响 |
| 资源高效 | 多个容器共享系统资源，开销极小 |

### 核心概念

```
镜像 (Image)     =  只读模板，打包好的软件（类似 .exe 安装包）
容器 (Container) =  镜像的运行实例（类似打开的应用程序）
仓库 (Registry)  =  存放镜像的地方（类似 App Store）
Dockerfile       =  文本文件，描述如何自动构建镜像
```

### 三大架构

```
Docker 客户端 (CLI)  →  Docker 守护进程 (Daemon)  →  容器运行时
```

## 二、安装 Docker

### Windows / macOS

下载 Docker Desktop：https://www.docker.com/products/docker-desktop

安装后启动即可，自带 Docker CLI 和 Docker Compose。

### Linux (Ubuntu/Debian)

```bash
# 卸载旧版本
sudo apt-get remove docker docker-engine docker.io containerd runc

# 安装依赖
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg lsb-release

# 添加官方 GPG 密钥
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# 添加仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

### 镜像加速（国内）

编辑 `/etc/docker/daemon.json`：

```json
{
  "registry-mirrors": [
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

重启 Docker 生效。

## 三、基础命令

### 3.1 查看信息

```bash
docker --version          # 查看版本
docker info               # 查看系统信息（容器数、镜像数等）
docker images             # 列出本地所有镜像
docker ps                 # 列出运行中的容器
docker ps -a              # 列出所有容器（包括已停止的）
```

### 3.2 镜像操作

```bash
docker pull nginx                     # 从仓库拉取镜像
docker pull nginx:latest              # 指定版本拉取
docker rmi nginx                      # 删除镜像
docker rmi $(docker images -q)        # 删除所有本地镜像
docker build -t my-app:1.0 .          # 从 Dockerfile 构建镜像
docker tag my-app:1.0 my-repo/my-app  # 打标签
docker push my-repo/my-app            # 推送到仓库
```

### 3.3 容器操作

```bash
# 启动容器
docker run -d --name my-nginx -p 8080:80 nginx
# -d: 后台运行
# --name: 指定容器名
# -p 宿主机端口:容器端口（端口映射）

# 进入容器交互式终端
docker exec -it my-nginx /bin/bash

# 停止 / 启动 / 重启
docker stop my-nginx
docker start my-nginx
docker restart my-nginx

# 删除容器
docker rm my-nginx

# 查看日志
docker logs my-nginx
docker logs -f my-nginx       # 实时跟踪日志

# 查看容器详情
docker inspect my-nginx

# 查看端口映射
docker port my-nginx

# 查看容器内进程
docker top my-nginx

# 查看资源使用
docker stats

# 清理所有已停止容器
docker container prune
```

### 3.4 常用 run 参数速查

| 参数 | 作用 | 示例 |
|------|------|------|
| `-d` | 后台运行 | `docker run -d nginx` |
| `-p` | 端口映射 | `-p 8080:80` |
| `-v` | 卷挂载 | `-v /host:/container` |
| `--name` | 容器名称 | `--name my-app` |
| `-it` | 交互式终端 | `-it ubuntu /bin/bash` |
| `-e` | 环境变量 | `-e MYSQL_ROOT_PASSWORD=123` |
| `--network` | 指定网络 | `--network my-net` |
| `--restart` | 重启策略 | `--restart always` |

## 四、Dockerfile

Dockerfile 是描述**如何构建镜像**的文本文件。

### 基本指令

| 指令 | 作用 | 示例 |
|------|------|------|
| `FROM` | 指定基础镜像 | `FROM ubuntu:22.04` |
| `RUN` | 构建时执行命令 | `RUN apt-get update && apt-get install -y nginx` |
| `COPY` | 复制文件到镜像 | `COPY ./app /app` |
| `ADD` | 复制（支持自动解压 + URL） | `ADD http://example.com/app.tar.gz /app` |
| `WORKDIR` | 设置工作目录 | `WORKDIR /app` |
| `ENV` | 设置环境变量（构建+运行时可用） | `ENV APP_ENV=production` |
| `ARG` | 构建参数（仅构建时可用） | `ARG VERSION=1.0` |
| `EXPOSE` | 声明端口（文档用，不实际映射） | `EXPOSE 8080` |
| `CMD` | 容器启动命令（可被覆盖） | `CMD ["nginx", "-g", "daemon off;"]` |
| `ENTRYPOINT` | 容器启动命令（不可被覆盖） | `ENTRYPOINT ["nginx"]` |
| `VOLUME` | 创建数据卷 | `VOLUME ["/data"]` |
| `USER` | 设置运行用户 | `USER nobody` |
| `HEALTHCHECK` | 健康检查 | `HEALTHCHECK CMD curl -f http://localhost/` |
| `LABEL` | 添加元数据 | `LABEL maintainer="me@example.com"` |

### CMD vs ENTRYPOINT

| | CMD | ENTRYPOINT |
|---|---|---|
| 可被 `docker run` 后面的参数覆盖 | ✅ | ❌（需用 `--entrypoint`） |
| 用途 | 默认命令 | 固定入口程序 |

**组合使用**（ENTRYPOINT 固定 + CMD 默认参数）：
```dockerfile
ENTRYPOINT ["nginx", "-c"]
CMD ["/etc/nginx/nginx.conf"]
```

### COPY vs ADD

| | COPY | ADD |
|---|---|---|
| 复制文件 | ✅ | ✅ |
| 自动解压 tar | ❌ | ✅ |
| 支持 URL | ❌ | ✅ |
| 推荐度 | **推荐** | 仅在需要解压/URL 时用 |

### 构建命令

```bash
docker build -t my-app:1.0 .
```

`.` 是构建上下文路径，表示把当前目录下的文件发送给 Docker 引擎。

### 最佳实践

```dockerfile
# 1. 用具体的版本标签，不用 latest
FROM node:18-alpine

# 2. 设置工作目录
WORKDIR /app

# 3. 先复制依赖文件，利用缓存
COPY package*.json ./
RUN npm ci --production

# 4. 再复制代码（代码变动不触发依赖重新安装）
COPY . .

# 5. 声明端口
EXPOSE 3000

# 6. 用非 root 用户运行
USER node

# 7. 用 ENTRYPOINT + CMD
ENTRYPOINT ["node"]
CMD ["server.js"]
```

## 五、数据卷（Volume）

数据卷用于**持久化数据**，容器删除后数据不丢失。

```bash
# 创建数据卷
docker volume create my-data

# 挂载数据卷
docker run -d -v my-data:/var/lib/mysql mysql:8.0

# 挂载宿主机目录
docker run -d -v /host/path:/container/path nginx

# 查看所有数据卷
docker volume ls

# 删除未使用的数据卷
docker volume prune
```

### 三种挂载方式

| 方式 | 语法 | 适用场景 |
|------|------|----------|
| 命名卷 | `-v my-data:/data` | 数据持久化（数据库等） |
| 绑定挂载 | `-v /host/path:/data` | 开发时热更新代码 |
| tmpfs | `--tmpfs /data` | 临时数据，不留磁盘 |

## 六、网络

```bash
# 查看网络
docker network ls

# 创建网络
docker network create my-net

# 容器加入网络
docker run -d --name app1 --network my-net nginx
docker run -d --name app2 --network my-net redis

# 容器间可通过名称互相访问
# app1 可以 ping 到 app2
```

### 网络模式

| 模式 | 说明 |
|------|------|
| `bridge` | 默认，容器通过虚拟网桥通信 |
| `host` | 直接使用宿主机网络 |
| `none` | 无网络 |
| `container` | 共享另一个容器的网络 |

## 七、Docker Compose

Compose 用于**定义和运行多容器应用**，用 YAML 文件描述所有服务。

### 三步走

1. 用 Dockerfile 定义应用环境
2. 用 `docker-compose.yml` 定义服务
3. 执行 `docker-compose up` 启动全部

### docker-compose.yml 示例

```yaml
version: '3'
services:
  web:
    build: .                    # 从 Dockerfile 构建
    ports:
      - "5000:5000"
    volumes:
      - .:/app                  # 代码热更新
    depends_on:
      - redis
    environment:
      - REDIS_HOST=redis
    restart: unless-stopped

  redis:
    image: redis:7-alpine       # 直接用镜像
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:

networks:
  default:
    driver: bridge
```

### 常用指令

| 指令 | 作用 |
|------|------|
| `version` | Compose 文件版本 |
| `build` | 构建镜像的上下文路径 |
| `image` | 指定运行的镜像 |
| `ports` | 端口映射 |
| `volumes` | 挂载数据卷 |
| `depends_on` | 服务依赖关系 |
| `environment` | 环境变量 |
| `networks` | 配置网络 |
| `restart` | 重启策略：`no` / `always` / `on-failure` / `unless-stopped` |
| `command` | 覆盖默认启动命令 |

### Compose 命令

```bash
docker-compose up              # 启动所有服务（前台）
docker-compose up -d           # 后台启动
docker-compose down            # 停止并删除容器、网络
docker-compose down -v         # 同时删除数据卷
docker-compose ps              # 查看服务状态
docker-compose logs            # 查看日志
docker-compose logs -f web     # 实时跟踪 web 服务日志
docker-compose build           # 重新构建镜像
docker-compose restart         # 重启服务
```

### 实战：一键部署 WordPress

```yaml
version: '3'
services:
  wordpress:
    image: wordpress:latest
    ports:
      - "8080:80"
    environment:
      WORDPRESS_DB_HOST: db
      WORDPRESS_DB_USER: wp
      WORDPRESS_DB_PASSWORD: wp123
      WORDPRESS_DB_NAME: wordpress
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: mysql:8.0
    environment:
      MYSQL_DATABASE: wordpress
      MYSQL_USER: wp
      MYSQL_ROOT_PASSWORD: root123
      MYSQL_PASSWORD: wp123
    volumes:
      - db-data:/var/lib/mysql
    restart: unless-stopped

volumes:
  db-data:
```

## 八、实战案例

### 8.1 运行 Nginx 静态服务器

```bash
docker run -d --name my-web -p 8080:80 -v ./html:/usr/share/nginx/html nginx
```

### 8.2 运行 MySQL

```bash
docker run -d --name my-mysql \
  -p 3306:3306 \
  -e MYSQL_ROOT_PASSWORD=123456 \
  -v mysql-data:/var/lib/mysql \
  mysql:8.0
```

### 8.3 运行 Redis

```bash
docker run -d --name my-redis -p 6379:6379 redis:7-alpine
```

### 8.4 运行 Mosquitto（MQTT Broker）

```bash
docker run -d --name mosquitto -p 1883:1883 -p 9001:9001 eclipse-mosquitto
```

### 8.5 构建并运行自己的 Node.js 应用

```dockerfile
# Dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
```

```bash
docker build -t my-node-app .
docker run -d --name my-app -p 3000:3000 my-node-app
```

## 九、常见问题

### 容器退出了怎么办？

```bash
docker logs <容器名>          # 查看日志排查原因
docker start <容器名>          # 重新启动
```

### 如何清理无用镜像和容器？

```bash
docker system prune -a        # 清理所有未使用的镜像、容器、网络、构建缓存
```

### 容器内没有想要的工具？

```bash
docker exec -it <容器名> apt-get update && apt-get install -y vim
```

### 如何查看容器的 IP 地址？

```bash
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' <容器名>
```

## 十、速查表

```
# 镜像
docker pull <image>          # 拉取
docker images                # 列表
docker rmi <image>           # 删除
docker build -t <name> .     # 构建
docker tag <old> <new>       # 打标签
docker push <image>          # 推送

# 容器
docker run -d --name <n> -p <host>:<container> <image>
docker ps                    # 运行中
docker ps -a                 # 全部
docker stop/start/restart <n>
docker rm <n>
docker exec -it <n> /bin/bash
docker logs -f <n>
docker inspect <n>
docker stats                 # 资源监控

# 数据卷
docker volume create <name>
docker volume ls
docker run -v <name>:/path <image>

# 网络
docker network create <name>
docker run --network <name> <image>

# Compose
docker-compose up -d
docker-compose down
docker-compose logs -f
```

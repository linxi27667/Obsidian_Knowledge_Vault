# Docker容器化详解

## 核心概念

- **镜像(Image)** - 只读模板
- **容器(Container)** - 运行实例
- **Dockerfile** - 构建脚本
- **Compose** - 多容器编排

---

## 一、Docker基础

### 1.1 镜像操作

```bash
# 搜索镜像
docker search ubuntu
docker search esp-idf

# 拉取镜像
docker pull ubuntu:22.04
docker pull espressif/idf:v5.1

# 列出镜像
docker images
docker image ls

# 删除镜像
docker rmi ubuntu:22.04
docker image rm <image_id>

# 清理未使用镜像
docker image prune -a

# 构建镜像
docker build -t myapp:1.0 .
docker build -f Dockerfile.prod -t myapp:prod .

# 标记镜像
docker tag myapp:1.0 registry.example.com/myapp:1.0

# 推送镜像
docker push registry.example.com/myapp:1.0

# 导出/导入镜像
docker save -o myapp.tar myapp:1.0
docker load -i myapp.tar

# 镜像历史
docker history myapp:1.0

# 镜像检查
docker inspect myapp:1.0
```

### 1.2 容器操作

```bash
# 创建并运行容器
docker run -it ubuntu:22.04 /bin/bash
docker run -d --name myapp -p 8080:80 nginx
docker run --rm ubuntu:22.04 echo "Hello"

# 常用参数
# -d        后台运行
# -it       交互式终端
# --name    容器名称
# -p        端口映射(host:container)
# -v        卷挂载
# -e        环境变量
# --network 网络
# --restart 重启策略
# --memory  内存限制
# --cpu     CPU限制

# 列出容器
docker ps          # 运行中
docker ps -a       # 所有容器
docker ps -q       # 仅ID

# 停止/启动/重启
docker stop myapp
docker start myapp
docker restart myapp

# 进入容器
docker exec -it myapp /bin/bash
docker exec myapp ls /app

# 查看日志
docker logs myapp
docker logs -f myapp        # 实时
docker logs --tail 100 myapp # 最后100行

# 删除容器
docker rm myapp
docker rm -f myapp    # 强制删除
docker container prune  # 清理已停止容器

# 容器信息
docker inspect myapp
docker stats myapp    # 资源使用
docker top myapp      # 进程列表

# 复制文件
docker cp myapp:/app/log.txt ./
docker cp ./config.yml myapp:/app/

# 容器提交(保存修改)
docker commit myapp myapp:modified
```

---

## 二、Dockerfile

### 2.1 基本指令

```dockerfile
# 基础镜像
FROM ubuntu:22.04

# 维护者信息
LABEL maintainer="developer@example.com"

# 设置工作目录
WORKDIR /app

# 复制文件
COPY requirements.txt .
COPY src/ ./src/

# 添加文件(支持URL和tar)
ADD https://example.com/file.tar.gz /tmp/

# 运行命令
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install -r requirements.txt

# 环境变量
ENV APP_ENV=production
ENV PYTHONUNBUFFERED=1

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python3", "app.py"]

# 入口点
ENTRYPOINT ["python3"]

# 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8080/health || exit 1

# 卷
VOLUME ["/data"]

# ARG(构建时变量)
ARG VERSION=1.0
```

### 2.2 多阶段构建

```dockerfile
# 阶段1: 构建
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 阶段2: 运行
FROM node:18-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["node", "dist/index.js"]
```

### 2.3 嵌入式开发镜像

```dockerfile
# ESP-IDF开发环境
FROM espressif/idf:v5.1

WORKDIR /project

# 安装额外工具
RUN apt-get update && apt-get install -y \
    git \
    wget \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 复制项目
COPY . .

# 设置环境
ENV IDF_PATH=/opt/esp/idf

# 入口点
ENTRYPOINT ["/opt/esp/idf/export.sh"]
CMD ["idf.py", "build"]
```

```dockerfile
# STM32开发环境
FROM ubuntu:22.04

# 安装工具链
RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    cmake \
    ninja-build \
    git \
    && rm -rf /var/lib/apt/lists/*

# 安装OpenOCD
RUN apt-get install -y openocd

WORKDIR /project
COPY . .

CMD ["make"]
```

---

## 三、Docker Compose

### 3.1 Compose文件

```yaml
# docker-compose.yml
version: '3.8'

services:
  # 应用服务
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8080:8080"
    environment:
      - NODE_ENV=production
      - DB_HOST=postgres
    depends_on:
      - postgres
      - redis
    networks:
      - backend
    restart: unless-stopped
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M

  # 数据库
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: secret
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - backend

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    networks:
      - backend

  # Nginx
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./certs:/etc/nginx/certs
    depends_on:
      - app
    networks:
      - frontend
      - backend

volumes:
  postgres_data:

networks:
  frontend:
  backend:
```

### 3.2 Compose命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 重建服务
docker-compose up -d --build

# 扩展服务
docker-compose up -d --scale app=3

# 执行命令
docker-compose exec app bash

# 查看配置
docker-compose config

# 停止并删除所有内容
docker-compose down -v  # 包含卷
```

---

## 四、数据管理

### 4.1 卷(Volume)

```bash
# 创建卷
docker volume create mydata

# 列出卷
docker volume ls

# 使用卷
docker run -v mydata:/data ubuntu

# 只读挂载
docker run -v mydata:/data:ro ubuntu

# 删除卷
docker volume rm mydata

# 清理未使用卷
docker volume prune
```

### 4.2 绑定挂载

```bash
# 挂载主机目录
docker run -v /host/path:/container/path ubuntu

# 当前目录挂载
docker run -v $(pwd):/app ubuntu

# 只读挂载
docker run -v $(pwd):/app:ro ubuntu

# 挂载单个文件
docker run -v /host/config.yml:/app/config.yml ubuntu
```

---

## 五、网络

### 5.1 网络管理

```bash
# 创建网络
docker network create mynet

# 列出网络
docker network ls

# 连接网络
docker network connect mynet mycontainer

# 断开网络
docker network disconnect mynet mycontainer

# 网络详情
docker network inspect mynet

# 删除网络
docker network rm mynet

# 使用网络
docker run --network mynet --name app1 ubuntu
docker run --network mynet --name app2 ubuntu
# app1和app2可以通过容器名通信
```

### 5.2 网络类型

```bash
# bridge - 默认网络
docker network create --driver bridge mynet

# overlay - 跨主机网络
docker network create --driver overlay mynet

# host - 使用主机网络
docker run --network host ubuntu

# none - 无网络
docker run --network none ubuntu
```

---

## 六、安全

### 6.1 安全实践

```dockerfile
# 使用非root用户
FROM ubuntu:22.04
RUN useradd -r -s /bin/false appuser
USER appuser

# 最小化镜像
FROM alpine:3.18
RUN apk add --no-cache python3

# 多阶段构建减少攻击面
FROM golang:1.21 AS builder
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o app

FROM scratch
COPY --from=builder /app/app /app
CMD ["/app"]

# 只读文件系统
docker run --read-only ubuntu

# 限制能力
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE ubuntu

# 安全扫描
docker scan myapp:1.0
```

### 6.2 镜像签名

```bash
# Docker Content Trust
export DOCKER_CONTENT_TRUST=1

# 签名镜像
docker push myapp:1.0  # 自动签名

# 验证签名
docker pull myapp:1.0  # 自动验证
```

---

## 七、CI/CD集成

### 7.1 GitHub Actions

```yaml
# .github/workflows/docker.yml
name: Docker Build

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to DockerHub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          push: true
          tags: |
            myapp:latest
            myapp:${{ github.sha }}
```

### 7.2 GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA .
    - docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA

test:
  stage: test
  image: $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
  script:
    - ./run_tests.sh

deploy:
  stage: deploy
  script:
    - docker pull $CI_REGISTRY_IMAGE:$CI_COMMIT_SHA
    - docker-compose up -d
```

---

## 八、嵌入式CI/CD

### 8.1 固件构建容器

```yaml
# docker-compose.yml for embedded CI
version: '3.8'

services:
  # ESP32构建
  esp32-build:
    image: espressif/idf:v5.1
    volumes:
      - ./esp32-project:/project
    working_dir: /project
    command: idf.py build

  # STM32构建
  stm32-build:
    image: stm32-builder:latest
    build:
      context: .
      dockerfile: Dockerfile.stm32
    volumes:
      - ./stm32-project:/project
    working_dir: /project
    command: make

  # 固件测试
  firmware-test:
    image: pytest-embedded:latest
    volumes:
      - ./tests:/tests
      - ./build:/build
    command: pytest /tests/

  # 文档生成
  docs:
    image: sphinxdoc/sphinx
    volumes:
      - ./docs:/docs
    working_dir: /docs
    command: make html
```

### 8.2 Dockerfile.stm32

```dockerfile
FROM ubuntu:22.04

# 安装ARM工具链
RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    libnewlib-arm-none-eabi \
    cmake \
    ninja-build \
    git \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 安装Python工具
RUN pip3 install \
    pyocd \
    pyserial

# 安装OpenOCD
RUN apt-get update && apt-get install -y openocd

WORKDIR /project

# 入口点
ENTRYPOINT ["/bin/bash"]
```

---

## 九、私有仓库

### 9.1 Harbor

```yaml
# docker-compose.yml for Harbor
version: '3.8'

services:
  registry:
    image: goharbor/registry-photon:v2.8.0
    volumes:
      - /data/registry:/storage
    environment:
      - REGISTRY_HTTP_ADDR=:5000

  harbor-core:
    image: goharbor/harbor-core:v2.8.0
    environment:
      - CORE_SECRET=secret
      - JOBSERVICE_SECRET=secret

  harbor-portal:
    image: goharbor/harbor-portal:v2.8.0
    ports:
      - "80:80"
      - "443:443"
```

```bash
# 推送到私有仓库
docker tag myapp:1.0 harbor.example.com/myproject/myapp:1.0
docker push harbor.example.com/myproject/myapp:1.0

# 从私有仓库拉取
docker pull harbor.example.com/myproject/myapp:1.0
```

---

## 十、监控与日志

### 10.1 容器监控

```bash
# 资源使用统计
docker stats

# 容器事件
docker events

# 容器检查
docker inspect myapp

# 导出指标到Prometheus
# 使用cAdvisor
docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  --detach=true \
  --name=cadvisor \
  gcr.io/cadvisor/cadvisor:latest
```

### 10.2 日志驱动

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

```bash
# 使用syslog驱动
docker run --log-driver syslog myapp

# 使用fluentd驱动
docker run --log-driver fluentd myapp
```

---

## 附录：常用命令速查

| 命令 | 说明 |
|------|------|
| `docker run` | 创建并运行容器 |
| `docker ps` | 列出容器 |
| `docker images` | 列出镜像 |
| `docker build` | 构建镜像 |
| `docker exec` | 执行命令 |
| `docker logs` | 查看日志 |
| `docker stop` | 停止容器 |
| `docker rm` | 删除容器 |
| `docker rmi` | 删除镜像 |
| `docker-compose up` | 启动服务 |
| `docker-compose down` | 停止服务 |

---

## 相关链接

- [[Docker容器化]] - Docker基础
- [[CI-CD流水线]] - CI/CD
- [[Git版本控制]] - Git
- [[嵌入式项目管理详解]] - 项目管理

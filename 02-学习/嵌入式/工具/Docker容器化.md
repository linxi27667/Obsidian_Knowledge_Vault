# Docker容器化

## 核心概念

- **Docker** - 容器化平台
- **镜像(Image)** - 只读模板
- **容器(Container)** - 镜像的运行实例
- **Dockerfile** - 构建镜像的脚本

---

## 一、Docker基础

### 1.1 安装

```bash
# Ubuntu
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# 添加用户到docker组
sudo usermod -aG docker $USER
```

---

### 1.2 基本命令

```bash
# 拉取镜像
docker pull ubuntu:22.04

# 查看镜像
docker images

# 运行容器
docker run -it ubuntu:22.04 /bin/bash

# 查看运行中容器
docker ps

# 查看所有容器
docker ps -a

# 停止容器
docker stop <container_id>

# 删除容器
docker rm <container_id>

# 删除镜像
docker rmi <image_id>
```

---

### 1.3 容器管理

```bash
# 进入运行中容器
docker exec -it <container_id> /bin/bash

# 查看日志
docker logs <container_id>

# 拷贝文件
docker cp file.txt <container_id>:/path/
docker cp <container_id>:/path/file.txt ./

# 容器状态
docker inspect <container_id>
```

---

## 二、Dockerfile

### 2.1 基本语法

```dockerfile
# 基础镜像
FROM ubuntu:22.04

# 维护者信息
LABEL maintainer="user@example.com"

# 环境变量
ENV DEBIAN_FRONTEND=noninteractive

# 工作目录
WORKDIR /app

# 安装依赖
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    && rm -rf /var/lib/apt/lists/*

# 拷贝文件
COPY . .

# 构建
RUN make

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["./app"]
```

---

### 2.2 指令说明

| 指令 | 说明 |
|------|------|
| FROM | 基础镜像 |
| RUN | 执行命令 |
| CMD | 容器启动命令 |
| ENTRYPOINT | 入口点 |
| COPY | 拷贝文件 |
| ADD | 拷贝文件(可解压) |
| ENV | 环境变量 |
| ARG | 构建参数 |
| WORKDIR | 工作目录 |
| EXPOSE | 暴露端口 |
| VOLUME | 挂载点 |
| USER | 运行用户 |
| LABEL | 元数据 |

---

### 2.3 多阶段构建

```dockerfile
# 构建阶段
FROM gcc:12 AS builder
WORKDIR /app
COPY . .
RUN make

# 运行阶段
FROM ubuntu:22.04
WORKDIR /app
COPY --from=builder /app/myapp .
CMD ["./myapp"]
```

---

## 三、Docker Compose

### 3.1 基本配置

**docker-compose.yml：**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    volumes:
      - ./data:/app/data
    environment:
      - NODE_ENV=production
    depends_on:
      - db

  db:
    image: postgres:14
    environment:
      POSTGRES_PASSWORD: password
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:
```

---

### 3.2 命令

```bash
# 启动
docker-compose up -d

# 停止
docker-compose down

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 重建
docker-compose build
docker-compose up -d --build
```

---

## 四、嵌入式开发容器

### 4.1 ESP-IDF容器

```dockerfile
FROM espressif/idf:v5.1

WORKDIR /app
COPY . .

# 构建
RUN . $IDF_PATH/export.sh && idf.py build

CMD ["idf.py", "monitor"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  esp32:
    build: .
    volumes:
      - .:/app
      - /dev/ttyUSB0:/dev/ttyUSB0
    devices:
      - /dev/ttyUSB0:/dev/ttyUSB0
    privileged: true
```

---

### 4.2 STM32开发容器

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    cmake \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .

RUN cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/arm-toolchain.cmake
RUN cmake --build build
```

---

### 4.3 工具链容器

```dockerfile
FROM ubuntu:22.04

# 嵌入式工具链
RUN apt-get update && apt-get install -y \
    gcc-arm-none-eabi \
    gdb-multiarch \
    openocd \
    minicom \
    picocom \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Python工具
RUN pip3 install \
    esptool \
    pyserial \
    platformio

WORKDIR /workspace
```

---

## 五、CI/CD集成

### 5.1 GitHub Actions

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: espressif/idf:v5.1

    steps:
    - uses: actions/checkout@v4

    - name: Build
      run: |
        . $IDF_PATH/export.sh
        idf.py build
```

---

### 5.2 GitLab CI

```yaml
build:
  image: espressif/idf:v5.1
  script:
    - . $IDF_PATH/export.sh
    - idf.py build
  artifacts:
    paths:
      - build/*.bin
```

---

## 六、镜像优化

### 6.1 减小镜像大小

```dockerfile
# 使用Alpine基础镜像
FROM alpine:3.18

# 多阶段构建
FROM gcc:12-alpine AS builder
WORKDIR /app
COPY . .
RUN make

FROM alpine:3.18
COPY --from=builder /app/myapp /usr/local/bin/
CMD ["myapp"]
```

---

### 6.2 缓存优化

```dockerfile
# 先拷贝依赖文件
COPY package.json .
RUN npm install

# 再拷贝源码
COPY . .
RUN npm run build
```

---

### 6.3 .dockerignore

```
.git
build/
*.o
*.elf
*.bin
node_modules/
```

---

## 七、数据管理

### 7.1 数据卷

```bash
# 创建卷
docker volume create mydata

# 使用卷
docker run -v mydata:/data ubuntu

# 查看卷
docker volume ls

# 删除卷
docker volume rm mydata
```

---

### 7.2 绑定挂载

```bash
# 挂载主机目录
docker run -v /host/path:/container/path ubuntu

# 只读挂载
docker run -v /host/path:/container/path:ro ubuntu
```

---

## 八、网络

### 8.1 网络模式

| 模式 | 说明 |
|------|------|
| bridge | 默认，桥接网络 |
| host | 使用主机网络 |
| none | 无网络 |
| overlay | 跨主机网络 |

---

### 8.2 自定义网络

```bash
# 创建网络
docker network create mynet

# 使用网络
docker run --network mynet --name app1 ubuntu
docker run --network mynet --name app2 ubuntu

# 容器间通信
# app1可以ping app2
```

---

## 九、安全

### 9.1 最佳实践

| 实践 | 说明 |
|------|------|
| 非root用户 | 使用USER指令 |
| 最小镜像 | 使用Alpine/distroless |
| 扫描漏洞 | 使用Trivy/Snyk |
| 签名镜像 | 使用Docker Content Trust |
| 限制资源 | 使用--memory/--cpus |

---

### 9.2 非root用户

```dockerfile
FROM ubuntu:22.04

RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

CMD ["./app"]
```

---

## 附录：常用命令速查

### 镜像命令

| 命令 | 说明 |
|------|------|
| docker build -t name . | 构建镜像 |
| docker pull image | 拉取镜像 |
| docker push image | 推送镜像 |
| docker images | 列出镜像 |
| docker rmi image | 删除镜像 |

### 容器命令

| 命令 | 说明 |
|------|------|
| docker run -it image | 运行容器 |
| docker exec -it id cmd | 执行命令 |
| docker stop id | 停止容器 |
| docker rm id | 删除容器 |
| docker logs id | 查看日志 |

---

## 相关链接

- [[CI-CD流水线]] - CI/CD集成
- [[Makefile与CMake]] - 构建系统
- [[Linux基础]] - Linux命令

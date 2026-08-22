# CI/CD流水线

## 核心概念

- **CI(持续集成)** - 频繁合并代码并自动验证
- **CD(持续交付/部署)** - 自动化发布流程
- **流水线(Pipeline)** - 自动化构建、测试、部署的步骤链
- **构建(Build)** - 编译代码生成可执行文件或固件

---

## 一、CI/CD概述

### 1.1 流程

```
代码提交 → 代码检查 → 编译构建 → 单元测试 → 集成测试 → 部署
```

### 1.2 好处

| 好处 | 说明 |
|------|------|
| 快速反馈 | 提交后立即知道是否有问题 |
| 减少错误 | 自动化测试捕获回归 |
| 提高质量 | 代码检查+测试覆盖 |
| 加速交付 | 自动化减少手动操作 |

---

## 二、GitHub Actions

### 2.1 基本语法

**工作流文件(.github/workflows/ci.yml)：**
```yaml
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Setup
      run: echo "Setting up..."

    - name: Build
      run: make

    - name: Test
      run: make test
```

---

### 2.2 触发条件

```yaml
on:
  push:
    branches: [ main, develop ]
    paths: [ 'src/**' ]
    tags: [ 'v*' ]

  pull_request:
    branches: [ main ]

  schedule:
    - cron: '0 2 * * 1'  # 每周一凌晨2点

  workflow_dispatch:  # 手动触发
```

---

### 2.3 矩阵构建

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        compiler: [gcc, clang]
        target: [esp32, stm32]

    steps:
    - uses: actions/checkout@v4

    - name: Build
      run: make CC=${{ matrix.compiler }} TARGET=${{ matrix.target }}
```

---

### 2.4 缓存

```yaml
steps:
- uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      build/
    key: ${{ runner.os }}-${{ hashFiles('**/requirements.txt') }}
    restore-keys: |
      ${{ runner.os }}-
```

---

### 2.5 制品上传

```yaml
steps:
- name: Upload firmware
  uses: actions/upload-artifact@v3
  with:
    name: firmware
    path: |
      build/*.bin
      build/*.elf
      build/*.hex
```

---

## 三、嵌入式CI/CD

### 3.1 ESP-IDF CI

```yaml
name: ESP-IDF CI

on:
  push:
    branches: [ main ]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: espressif/idf:v5.1

    steps:
    - uses: actions/checkout@v4
      with:
        submodules: recursive

    - name: Build
      shell: bash
      run: |
        . $IDF_PATH/export.sh
        idf.py build

    - name: Upload firmware
      uses: actions/upload-artifact@v3
      with:
        name: firmware
        path: build/*.bin
```

---

### 3.2 STM32 CI

```yaml
name: STM32 CI

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Install ARM toolchain
      run: |
        sudo apt-get update
        sudo apt-get install -y gcc-arm-none-eabi

    - name: Build
      run: |
        cmake -B build -DCMAKE_TOOLCHAIN_FILE=cmake/arm-toolchain.cmake
        cmake --build build

    - name: Upload firmware
      uses: actions/upload-artifact@v3
      with:
        name: firmware
        path: |
          build/*.elf
          build/*.hex
          build/*.bin
```

---

### 3.3 静态分析

```yaml
jobs:
  analysis:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: cppcheck
      run: |
        sudo apt-get install -y cppcheck
        cppcheck --enable=all --error-exitcode=1 src/

    - name: clang-tidy
      run: |
        sudo apt-get install -y clang-tidy
        clang-tidy src/*.c -- -Iinclude
```

---

### 3.4 单元测试

```yaml
jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Install Unity
      run: |
        git clone https://github.com/ThrowTheSwitch/Unity.git

    - name: Build tests
      run: |
        make -C tests

    - name: Run tests
      run: |
        ./tests/test_runner
```

---

## 四、GitLab CI

### 4.1 基本配置

**.gitlab-ci.yml：**
```yaml
stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: espressif/idf:v5.1
  script:
    - . $IDF_PATH/export.sh
    - idf.py build
  artifacts:
    paths:
      - build/*.bin

test:
  stage: test
  script:
    - make test
  coverage: '/Lines:\s+(\d+\.\d+)%/'

deploy:
  stage: deploy
  script:
    - scp build/*.bin user@device:/firmware/
  only:
    - main
```

---

## 五、Jenkins

### 5.1 Jenkinsfile

```groovy
pipeline {
    agent any

    environment {
        IDF_PATH = '/opt/esp-idf'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh '''
                    . $IDF_PATH/export.sh
                    idf.py build
                '''
            }
        }

        stage('Test') {
            steps {
                sh 'make test'
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh 'scp build/*.bin user@device:/firmware/'
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'build/*.bin'
        }
    }
}
```

---

## 六、自动化测试

### 6.1 测试框架集成

**Unity测试示例：**
```c
// test_math.c
#include "unity.h"
#include "math_utils.h"

void setUp(void) {}
void tearDown(void) {}

void test_add(void) {
    TEST_ASSERT_EQUAL(3, add(1, 2));
    TEST_ASSERT_EQUAL(0, add(-1, 1));
}

void test_multiply(void) {
    TEST_ASSERT_EQUAL(6, multiply(2, 3));
    TEST_ASSERT_EQUAL(0, multiply(0, 5));
}

int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_add);
    RUN_TEST(test_multiply);
    return UNITY_END();
}
```

**Makefile：**
```makefile
CC = gcc
CFLAGS = -Wall -Wextra -I../src -IUnity/src

TEST_SRC = test_math.c Unity/src/unity.c ../src/math_utils.c

test: $(TEST_SRC)
	$(CC) $(CFLAGS) -o test_runner $(TEST_SRC)
	./test_runner

.PHONY: test
```

---

### 6.2 覆盖率

```yaml
jobs:
  coverage:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Build with coverage
      run: |
        make CFLAGS="--coverage"

    - name: Run tests
      run: make test

    - name: Generate coverage
      run: |
        gcov src/*.c
        lcov --capture --directory . --output-file coverage.info
        genhtml coverage.info --output-directory coverage_report

    - name: Upload coverage
      uses: actions/upload-artifact@v3
      with:
        name: coverage
        path: coverage_report/
```

---

## 七、版本管理

### 7.1 语义化版本

**格式：** `MAJOR.MINOR.PATCH`

| 变更 | 版本 | 示例 |
|------|------|------|
| 不兼容的API变更 | MAJOR | 2.0.0 |
| 新功能(兼容) | MINOR | 1.1.0 |
| Bug修复 | PATCH | 1.0.1 |

---

### 7.2 自动版本

```yaml
- name: Bump version
  uses: anothrNick/github-tag-action@1.36.0
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    WITH_V: true
    DEFAULT_BUMP: patch
```

---

### 7.3 发布工作流

```yaml
name: Release

on:
  push:
    tags: [ 'v*' ]

jobs:
  release:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v4

    - name: Build
      run: make

    - name: Create Release
      uses: softprops/action-gh-release@v1
      with:
        files: |
          build/*.bin
          build/*.elf
          build/*.hex
        body: |
          ## Changes
          - Bug fixes
          - Performance improvements
```

---

## 八、部署

### 8.1 OTA部署

```yaml
deploy:
  stage: deploy
  script:
    - curl -X POST http://device:8080/ota \
        -F "firmware=@build/firmware.bin"
  only:
    - main
```

---

### 8.2 容器化部署

```dockerfile
# Dockerfile
FROM espressif/idf:v5.1

WORKDIR /app
COPY . .

RUN idf.py build

CMD ["idf.py", "flash", "monitor"]
```

```yaml
deploy:
  stage: deploy
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t myapp .
    - docker push registry/myapp
```

---

## 九、通知

### 9.1 构建通知

```yaml
notify:
  runs-on: ubuntu-latest
  needs: [build, test]

  steps:
  - name: Notify on failure
    if: failure()
    uses: slackapi/slack-github-action@v1
    with:
      payload: |
        {
          "text": "Build failed for ${{ github.repository }}"
        }
```

---

## 附录：工具对比

| 工具 | 特点 | 适用 |
|------|------|------|
| GitHub Actions | GitHub集成 | GitHub项目 |
| GitLab CI | GitLab集成 | GitLab项目 |
| Jenkins | 高度可定制 | 企业级 |
| Travis CI | 简单易用 | 开源项目 |
| CircleCI | 快速 | 云端CI |

---

## 相关链接

- [[Git版本控制]] - Git基础
- [[自动化测试]] - 测试框架
- [[Makefile与CMake]] - 构建系统

# CI/CD详解

## 核心概念

- **CI** - 持续集成
- **CD** - 持续交付/部署
- **流水线** - 自动化构建流程
- **GitHub Actions** - GitHub CI/CD平台

---

## 一、CI/CD基础

### 1.1 CI/CD流程

```
代码提交 → 代码检查 → 单元测试 → 构建 → 集成测试 → 部署
    │         │         │        │         │        │
    └─────────┴─────────┴────────┴─────────┴────────┘
                    持续集成(CI)
                              持续交付/部署(CD)
```

### 1.2 核心原则

```yaml
# CI/CD最佳实践
principles:
  - 频繁提交: 每天多次提交代码
  - 自动化测试: 每次提交自动运行测试
  - 快速反馈: 构建失败立即通知
  - 主干开发: 减少长期分支
  - 环境一致性: 开发/测试/生产环境一致
  - 基础设施即代码: 环境配置版本化
```

---

## 二、GitHub Actions

### 2.1 基本配置

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        run: |
          python -m pytest tests/

      - name: Build
        run: |
          python setup.py build
```

### 2.2 嵌入式CI

```yaml
# .github/workflows/embedded-ci.yml
name: Embedded CI

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'include/**'
      - 'CMakeLists.txt'
  pull_request:
    branches: [main]

jobs:
  # STM32构建
  build-stm32:
    runs-on: ubuntu-latest
    container:
      image: stm32-builder:latest

    steps:
      - uses: actions/checkout@v3

      - name: Build firmware
        run: |
          mkdir build && cd build
          cmake -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake ..
          make -j$(nproc)

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: stm32-firmware
          path: |
            build/firmware.bin
            build/firmware.hex
            build/firmware.elf

  # ESP32构建
  build-esp32:
    runs-on: ubuntu-latest
    container:
      image: espressif/idf:v5.1

    steps:
      - uses: actions/checkout@v3

      - name: Build ESP32 firmware
        run: |
          . $IDF_PATH/export.sh
          idf.py build

      - name: Upload artifact
        uses: actions/upload-artifact@v3
        with:
          name: esp32-firmware
          path: build/*.bin

  # 代码检查
  code-quality:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Run cppcheck
        run: |
          sudo apt-get install -y cppcheck
          cppcheck --enable=all src/

      - name: Run clang-tidy
        run: |
          sudo apt-get install -y clang-tidy
          run-clang-tidy -p build src/*.c

  # 静态分析
  static-analysis:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Run Coverity
        uses: coverityapp/github-action@v1
        with:
          token: ${{ secrets.COVERITY_TOKEN }}

  # 单元测试
  unit-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Install Unity test framework
        run: |
          git clone https://github.com/ThrowTheSwitch/Unity.git

      - name: Build and run tests
        run: |
          gcc -IUnity/src tests/test_*.c Unity/src/unity.c -o test_runner
          ./test_runner

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results.xml
```

### 2.3 多平台构建

```yaml
# .github/workflows/multi-platform.yml
name: Multi-Platform Build

on:
  push:
    tags: ['v*']

jobs:
  build:
    strategy:
      matrix:
        platform:
          - name: STM32F4
            toolchain: arm-none-eabi
            target: stm32f4
          - name: ESP32
            toolchain: xtensa-esp32
            target: esp32
          - name: nRF52
            toolchain: arm-none-eabi
            target: nrf52
          - name: RISC-V
            toolchain: riscv32-unknown-elf
            target: riscv

    runs-on: ubuntu-latest
    name: Build ${{ matrix.platform.name }}

    steps:
      - uses: actions/checkout@v3

      - name: Setup toolchain
        run: |
          sudo apt-get install -y gcc-${{ matrix.platform.toolchain }}

      - name: Build
        run: |
          make TARGET=${{ matrix.platform.target }} -j$(nproc)

      - name: Upload
        uses: actions/upload-artifact@v3
        with:
          name: firmware-${{ matrix.platform.target }}
          path: build/*.bin
```

---

## 三、GitLab CI

### 3.1 基本配置

```yaml
# .gitlab-ci.yml
stages:
  - build
  - test
  - analysis
  - deploy

variables:
  GIT_SUBMODULE_STRATEGY: recursive

# 构建阶段
build:
  stage: build
  image: stm32-builder:latest
  script:
    - mkdir build && cd build
    - cmake ..
    - make -j$(nproc)
  artifacts:
    paths:
      - build/firmware.bin
      - build/firmware.elf
    expire_in: 1 week

# 测试阶段
unit-test:
  stage: test
  image: gcc:latest
  script:
    - gcc -IUnity/src tests/test_*.c Unity/src/unity.c -o test_runner
    - ./test_runner
  artifacts:
    reports:
      junit: test-results.xml

# 代码分析
cppcheck:
  stage: analysis
  image: cppcheck:latest
  script:
    - cppcheck --enable=all --xml --xml-version=2 src/ 2> cppcheck.xml
  artifacts:
    reports:
      codequality: cppcheck.xml

# 静态分析
coverity:
  stage: analysis
  image: coverity:latest
  script:
    - cov-build --dir cov-int make
    - tar czf cov-int.tar.gz cov-int
  artifacts:
    paths:
      - cov-int.tar.gz

# 部署到测试设备
deploy-test:
  stage: deploy
  script:
    - scp build/firmware.bin pi@test-device:/tmp/
    - ssh pi@test-device "sudo flash_firmware /tmp/firmware.bin"
  only:
    - main
  when: manual
```

### 3.2 矩阵构建

```yaml
# 矩阵构建
build-matrix:
  stage: build
  parallel:
    matrix:
      - TARGET: stm32f4
        TOOLCHAIN: arm-none-eabi
      - TARGET: esp32
        TOOLCHAIN: xtensa-esp32
      - TARGET: nrf52
        TOOLCHAIN: arm-none-eabi
  script:
    - make TARGET=$TARGET -j$(nproc)
  artifacts:
    paths:
      - build/*.bin
```

---

## 四、Jenkins

### 4.1 Jenkinsfile

```groovy
// Jenkinsfile
pipeline {
    agent any

    parameters {
        choice(name: 'PLATFORM', choices: ['stm32f4', 'esp32', 'nrf52'])
        booleanParam(name: 'RUN_TESTS', defaultValue: true)
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git submodule update --init --recursive'
            }
        }

        stage('Build') {
            steps {
                sh "make TARGET=${params.PLATFORM} -j\$(nproc)"
            }
        }

        stage('Unit Tests') {
            when {
                expression { params.RUN_TESTS }
            }
            steps {
                sh './run_tests.sh'
            }
            post {
                always {
                    junit 'test-results.xml'
                }
            }
        }

        stage('Static Analysis') {
            steps {
                sh 'cppcheck --enable=all src/'
                sh 'clang-tidy src/*.c'
            }
        }

        stage('Deploy') {
            when {
                branch 'main'
            }
            steps {
                sh 'scp build/firmware.bin deploy@device:/opt/firmware/'
            }
        }
    }

    post {
        success {
            emailext (
                subject: "Build Success: ${env.JOB_NAME}",
                body: "Build ${env.BUILD_NUMBER} succeeded.",
                to: 'team@example.com'
            )
        }
        failure {
            emailext (
                subject: "Build Failed: ${env.JOB_NAME}",
                body: "Build ${env.BUILD_NUMBER} failed.",
                to: 'team@example.com'
            )
        }
    }
}
```

---

## 五、自动化测试

### 5.1 测试框架

```c
// Unity测试框架
#include "unity.h"

// 测试夹具
void setUp(void) {
    // 每个测试前执行
}

void tearDown(void) {
    // 每个测试后执行
}

// 测试用例
void test_add_function(void) {
    TEST_ASSERT_EQUAL_INT(5, add(2, 3));
    TEST_ASSERT_EQUAL_INT(0, add(-1, 1));
    TEST_ASSERT_EQUAL_INT(-3, add(-1, -2));
}

void test_buffer_overflow(void) {
    char buffer[10];
    TEST_ASSERT_EQUAL_INT(0, safe_copy(buffer, "Hello", sizeof(buffer)));
    TEST_ASSERT_EQUAL_STRING("Hello", buffer);
}

// 测试套件
int main(void) {
    UNITY_BEGIN();
    RUN_TEST(test_add_function);
    RUN_TEST(test_buffer_overflow);
    return UNITY_END();
}
```

### 5.2 集成测试

```python
# pytest集成测试
import pytest
import serial
import time

@pytest.fixture
def device():
    """设备连接fixture"""
    dev = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    time.sleep(2)  # 等待设备启动
    yield dev
    dev.close()

def test_device_boot(device):
    """测试设备启动"""
    device.write(b'version\r\n')
    response = device.readline().decode()
    assert 'v1.0.0' in response

def test_sensor_read(device):
    """测试传感器读取"""
    device.write(b'read_sensor\r\n')
    response = device.readline().decode()
    data = parse_sensor_data(response)
    assert 20.0 < data['temperature'] < 30.0
    assert 40.0 < data['humidity'] < 60.0

def test_gpio_output(device):
    """测试GPIO输出"""
    device.write(b'set_led on\r\n')
    response = device.readline().decode()
    assert 'OK' in response

    device.write(b'get_led\r\n')
    response = device.readline().decode()
    assert 'on' in response

@pytest.mark.parametrize("cmd,expected", [
    (b'ping\r\n', b'pong'),
    (b'reset\r\n', b'rebooting'),
    (b'info\r\n', b'System Info'),
])
def test_commands(device, cmd, expected):
    """参数化命令测试"""
    device.write(cmd)
    response = device.readline()
    assert expected in response
```

### 5.3 硬件在环测试

```python
# HIL测试
import pyocd
import time

class HILTester:
    def __init__(self, device_path):
        self.probe = pyocd.probe_debug_probe.create_probe(device_path)
        self.session = pyocd.session.Session(self.probe)
        self.target = self.session.target

    def flash_firmware(self, firmware_path):
        """烧录固件"""
        loader = self.target.get_flash_loader()
        loader.add_data(0x08000000, open(firmware_path, 'rb').read())
        loader.commit()
        self.target.reset()

    def read_register(self, reg):
        """读取寄存器"""
        return self.target.read_core_register(reg)

    def write_register(self, reg, value):
        """写入寄存器"""
        self.target.write_core_register(reg, value)

    def read_memory(self, addr, size):
        """读取内存"""
        return self.target.read_memory_block8(addr, size)

    def write_memory(self, addr, data):
        """写入内存"""
        self.target.write_memory_block8(addr, data)

    def set_breakpoint(self, addr):
        """设置断点"""
        self.target.set_breakpoint(addr)

    def run_to_breakpoint(self, addr, timeout=5):
        """运行到断点"""
        self.set_breakpoint(addr)
        self.target.resume()
        start = time.time()
        while time.time() - start < timeout:
            if self.target.get_state() == 'halted':
                return True
            time.sleep(0.01)
        return False

# HIL测试用例
def test_firmware_flash():
    hil = HILTester('DAPLink')
    hil.flash_firmware('build/firmware.bin')

    # 验证固件版本
    version = hil.read_memory(0x08001000, 4)
    assert version == [0x01, 0x00, 0x00, 0x00]

def test_timer_functionality():
    hil = HILTester('DAPLink')

    # 运行到定时器中断
    hil.run_to_breakpoint(0x08001234)  # 定时器ISR地址

    # 检查计数器
    counter = hil.read_memory(0x20000000, 4)
    assert int.from_bytes(counter, 'little') > 0
```

---

## 六、制品管理

### 6.1 版本标签

```yaml
# 自动版本标签
name: Release

on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build all platforms
        run: |
          make TARGET=stm32f4 -j$(nproc)
          make TARGET=esp32 -j$(nproc)

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            build/stm32f4/firmware.bin
            build/esp32/firmware.bin
          body: |
            ## Changes
            - New feature A
            - Bug fix B
          draft: false
          prerelease: false
```

### 6.2 制品存储

```yaml
# 制品上传
- name: Upload to S3
  uses: aws-actions/configure-aws-credentials@v1
  with:
    aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    aws-region: us-east-1

- name: Upload firmware
  run: |
    aws s3 cp build/firmware.bin s3://firmware-bucket/v${{ github.ref_name }}/
```

---

## 七、通知与监控

### 7.1 通知配置

```yaml
# Slack通知
- name: Slack Notification
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    fields: repo,message,commit,author,action,eventName,ref,workflow
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
  if: always()

# 邮件通知
- name: Send email
  uses: dawidd6/action-send-mail@v2
  with:
    server_address: smtp.gmail.com
    server_port: 465
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: Build ${{ job.status }}: ${{ github.repository }}
    body: Build result: ${{ job.status }}
    to: team@example.com
    from: CI <ci@example.com>
```

---

## 附录：CI/CD工具对比

| 工具 | 特点 | 适用场景 |
|------|------|----------|
| GitHub Actions | GitHub集成 | GitHub项目 |
| GitLab CI | GitLab集成 | GitLab项目 |
| Jenkins | 自定义强 | 企业内部 |
| CircleCI | 云服务 | SaaS项目 |
| Travis CI | 开源友好 | 开源项目 |

---

## 相关链接

- [[CI-CD流水线]] - CI/CD基础
- [[Git版本控制]] - Git
- [[Docker容器化详解]] - Docker
- [[嵌入式项目管理详解]] - 项目管理

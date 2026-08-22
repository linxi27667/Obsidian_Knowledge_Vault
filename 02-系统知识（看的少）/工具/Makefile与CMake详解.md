# Makefile与CMake详解

## 核心概念

- **Makefile** - GNU Make构建脚本
- **CMake** - 跨平台构建系统生成器
- **交叉编译** - 在主机编译目标平台代码
- **构建系统** - 自动化编译流程

---

## 一、Makefile

### 1.1 基本语法

```makefile
# 变量定义
CC = gcc
CFLAGS = -Wall -Wextra -O2
LDFLAGS = -lm
TARGET = myapp

# 源文件
SRCS = main.c utils.c driver.c
OBJS = $(SRCS:.c=.o)

# 默认目标
all: $(TARGET)

# 链接
$(TARGET): $(OBJS)
	$(CC) $(OBJS) -o $(TARGET) $(LDFLAGS)

# 编译规则
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 清理
clean:
	rm -f $(OBJS) $(TARGET)

# 伪目标
.PHONY: all clean

# 自动变量
# $@ - 目标文件
# $< - 第一个依赖
# $^ - 所有依赖
# $? - 比目标新的依赖
```

### 1.2 高级特性

```makefile
# 条件判断
DEBUG ?= 0
ifeq ($(DEBUG), 1)
    CFLAGS += -g -DDEBUG
else
    CFLAGS += -DNDEBUG
endif

# 函数
SOURCES = $(wildcard src/*.c)
OBJECTS = $(SOURCES:.c=.o)
HEADERS = $(wildcard include/*.h)

# 字符串替换
VERSION = 1.0.2
MAJOR = $(word 1,$(subst ., ,$(VERSION)))

# 包含其他Makefile
-include config.mk

# 模式规则
src/%.o: src/%.c $(HEADERS)
	$(CC) $(CFLAGS) -Iinclude -c $< -o $@

# 目标特定变量
debug: CFLAGS += -g -DDEBUG
debug: $(TARGET)

# 多目标
all: app1 app2

app1: app1.o
	$(CC) $^ -o $@

app2: app2.o
	$(CC) $^ -o $@

# 并行构建
# make -j4

# 递归构建
SUBDIRS = src lib test
all:
	for dir in $(SUBDIRS); do \
		$(MAKE) -C $$dir; \
	done

# 自动生成依赖
DEPDIR = .deps
$(DEPDIR)/%.d: %.c
	@mkdir -p $(DEPDIR)
	@$(CC) -MM $(CFLAGS) $< > $@.$$$$; \
	sed 's,\($*\)\.o[ :]*,\1.o $@ : ,g' < $@.$$$$ > $@; \
	rm -f $@.$$$$

-include $(DEPDIR)/$(SRCS:.c=.d)
```

### 1.3 嵌入式Makefile

```makefile
# ARM交叉编译Makefile
PREFIX = arm-none-eabi-
CC = $(PREFIX)gcc
AS = $(PREFIX)as
LD = $(PREFIX)ld
OBJCOPY = $(PREFIX)objcopy
OBJDUMP = $(PREFIX)objdump
SIZE = $(PREFIX)size

# 芯片定义
DEVICE = STM32F407VG
CFLAGS = -mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16
CFLAGS += -D$(DEVICE) -DUSE_HAL_DRIVER
CFLAGS += -I./Drivers/CMSIS/Include
CFLAGS += -I./Drivers/$(DEVICE)/Include
CFLAGS += -Os -Wall -ffunction-sections -fdata-sections

LDFLAGS = -T linker.ld -Wl,--gc-sections
LDFLAGS += -lm -lc -lnosys

# 源文件
C_SOURCES = $(wildcard src/*.c)
ASM_SOURCES = $(wildcard src/*.s)
OBJECTS = $(C_SOURCES:.c=.o) $(ASM_SOURCES:.s=.o)

# 目标
TARGET = firmware

all: $(TARGET).elf $(TARGET).hex $(TARGET).bin size

$(TARGET).elf: $(OBJECTS)
	$(CC) $(OBJECTS) $(LDFLAGS) -o $@

%.hex: %.elf
	$(OBJCOPY) -O ihex $< $@

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

size: $(TARGET).elf
	$(SIZE) $<

# 烧录
flash: $(TARGET).bin
	st-flash write $(TARGET).bin 0x08000000

# 调试
debug: $(TARGET).elf
	$(GDB) -ex "target remote :3333" $<

clean:
	rm -f $(OBJECTS) $(TARGET).elf $(TARGET).hex $(TARGET).bin

.PHONY: all clean flash debug size
```

---

## 二、CMake

### 2.1 基本语法

```cmake
# CMakeLists.txt
cmake_minimum_required(VERSION 3.20)

project(MyApp
    VERSION 1.0.0
    LANGUAGES C CXX
    DESCRIPTION "My embedded application"
)

# C++标准
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# C标准
set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

# 添加可执行文件
add_executable(myapp
    src/main.c
    src/utils.c
    src/driver.c
)

# 包含目录
target_include_directories(myapp PRIVATE
    ${CMAKE_SOURCE_DIR}/include
)

# 编译选项
target_compile_options(myapp PRIVATE
    -Wall -Wextra -O2
)

# 链接库
target_link_libraries(myapp PRIVATE
    m
    pthread
)

# 安装
install(TARGETS myapp DESTINATION bin)
install(FILES config.yml DESTINATION etc)
```

### 2.2 库管理

```cmake
# 静态库
add_library(mylib STATIC
    src/lib.c
)
target_include_directories(mylib PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

# 共享库
add_library(mylib SHARED
    src/lib.c
)
set_target_properties(mylib PROPERTIES
    VERSION 1.0.0
    SOVERSION 1
)

# 接口库(头文件库)
add_library(headerlib INTERFACE)
target_include_directories(headerlib INTERFACE
    ${CMAKE_SOURCE_DIR}/include
)

# 使用库
add_executable(myapp src/main.c)
target_link_libraries(myapp PRIVATE mylib)
```

### 2.3 查找包

```cmake
# 查找系统包
find_package(PkgConfig REQUIRED)
pkg_check_modules(LIBUSB libusb-1.0)

# 查找库
find_library(MATH_LIB m)
find_library(PTHREAD_LIB pthread)

# 使用
target_link_libraries(myapp PRIVATE
    ${LIBUSB_LIBRARIES}
    ${MATH_LIB}
)
target_include_directories(myapp PRIVATE
    ${LIBUSB_INCLUDE_DIRS}
)

# 查找Python
find_package(Python3 COMPONENTS Interpreter Development)

# 自定义Find模块
# cmake/modules/FindMyLib.cmake
# MYLIB_FOUND
# MYLIB_INCLUDE_DIRS
# MYLIB_LIBRARIES
```

### 2.4 条件编译

```cmake
# 选项
option(ENABLE_DEBUG "Enable debug mode" OFF)
option(ENABLE_TESTS "Enable tests" ON)
option(BUILD_SHARED_LIBS "Build shared libraries" OFF)

# 平台检测
if(WIN32)
    add_definitions(-DPLATFORM_WINDOWS)
elseif(UNIX AND NOT APPLE)
    add_definitions(-DPLATFORM_LINUX)
elseif(APPLE)
    add_definitions(-DPLATFORM_MACOS)
endif()

# 编译器检测
if(CMAKE_C_COMPILER_ID STREQUAL "GNU")
    add_compile_options(-Wall -Wextra)
elseif(CMAKE_C_COMPILER_ID STREQUAL "Clang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# 配置文件
configure_file(
    ${CMAKE_SOURCE_DIR}/config.h.in
    ${CMAKE_BINARY_DIR}/config.h
)
# config.h.in:
# #define ENABLE_DEBUG @ENABLE_DEBUG@
# #define VERSION "@PROJECT_VERSION@"
```

---

## 三、交叉编译

### 3.1 工具链文件

```cmake
# cmake/arm-none-eabi.cmake
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

# 工具链路径
set(TOOLCHAIN_PREFIX arm-none-eabi-)
set(CMAKE_C_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_ASM_COMPILER ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_AR ${TOOLCHAIN_PREFIX}ar)
set(CMAKE_OBJCOPY ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_OBJDUMP ${TOOLCHAIN_PREFIX}objdump)
set(CMAKE_SIZE ${TOOLCHAIN_PREFIX}size)

# 芯片标志
set(MCU_FLAGS "-mcpu=cortex-m4 -mthumb -mfloat-abi=hard -mfpu=fpv4-sp-d16")
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${MCU_FLAGS}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${MCU_FLAGS}")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} ${MCU_FLAGS}")

# 链接脚本
set(CMAKE_EXE_LINKER_FLAGS
    "${CMAKE_EXE_LINKER_FLAGS} -T ${CMAKE_SOURCE_DIR}/linker.ld -Wl,--gc-sections"
)

# 不测试编译器
set(CMAKE_TRY_COMPILE_TARGET_TYPE STATIC_LIBRARY)
```

```cmake
# CMakeLists.txt for ARM
cmake_minimum_required(VERSION 3.20)
project(STM32F4 C ASM)

# 使用工具链文件
# cmake -DCMAKE_TOOLCHAIN_FILE=cmake/arm-none-eabi.cmake ..

# 源文件
set(SOURCES
    src/main.c
    src/stm32f4xx_it.c
    Drivers/Src/stm32f4xx_hal.c
    startup_stm32f407vg.s
)

# 创建ELF
add_executable(firmware.elf ${SOURCES})

# 生成HEX和BIN
add_custom_command(TARGET firmware.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex firmware.elf firmware.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary firmware.elf firmware.bin
    COMMAND ${CMAKE_SIZE} firmware.elf
    COMMENT "Generating firmware.hex and firmware.bin"
)

# 烧录命令
add_custom_target(flash
    COMMAND st-flash write firmware.bin 0x08000000
    DEPENDS firmware.elf
)
```

### 3.2 ESP-IDF CMake

```cmake
# CMakeLists.txt for ESP-IDF
cmake_minimum_required(VERSION 3.16)

# 包含ESP-IDF
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# 项目名称
project(my_esp32_app)

# 组件目录
# 默认包含 components/ 目录

# 注册组件
# components/my_component/CMakeLists.txt:
# idf_component_register(
#     SRCS "my_component.c"
#     INCLUDE_DIRS "include"
#     REQUIRES driver esp_wifi
# )
```

### 3.3 Zephyr CMake

```cmake
# CMakeLists.txt for Zephyr
cmake_minimum_required(VERSION 3.20.0)
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(my_zephyr_app)

target_sources(app PRIVATE
    src/main.c
    src/sensor.c
)

target_include_directories(app PRIVATE
    src/include
)
```

---

## 四、构建系统最佳实践

### 4.1 项目结构

```
project/
├── CMakeLists.txt          # 顶层CMake
├── cmake/                  # CMake模块
│   ├── arm-none-eabi.cmake # 工具链
│   └── FindMyLib.cmake     # 自定义查找
├── src/                    # 源代码
│   ├── CMakeLists.txt
│   ├── main.c
│   └── utils.c
├── include/                # 头文件
│   └── myapp/
│       ├── utils.h
│       └── config.h
├── lib/                    # 第三方库
│   └── CMakeLists.txt
├── test/                   # 测试
│   └── CMakeLists.txt
├── docs/                   # 文档
├── scripts/                # 脚本
├── build/                  # 构建目录(git忽略)
└── README.md
```

### 4.2 子目录CMake

```cmake
# src/CMakeLists.txt
add_library(app_lib STATIC
    utils.c
    driver.c
)
target_include_directories(app_lib PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/../include
)

# test/CMakeLists.txt
enable_testing()
find_package(GTest REQUIRED)

add_executable(test_utils test_utils.cpp)
target_link_libraries(test_utils PRIVATE
    app_lib
    GTest::gtest_main
)
add_test(NAME test_utils COMMAND test_utils)
```

---

## 附录：命令对比

| 功能 | Make | CMake |
|------|------|-------|
| 变量 | `VAR = value` | `set(VAR value)` |
| 条件 | `ifeq` | `if()` |
| 循环 | `foreach` | `foreach()` |
| 函数 | `$(func)` | `function()` |
| 包含 | `include` | `include()` |
| 目标 | `target:` | `add_executable()` |
| 依赖 | `target: dep` | `target_link_libraries()` |

---

## 相关链接

- [[Makefile与CMake]] - 构建基础
- [[GCC与链接脚本]] - 编译工具
- [[CI-CD流水线]] - CI/CD
- [[嵌入式项目管理详解]] - 项目管理

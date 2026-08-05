# Makefile与CMake

## 核心概念

- **Make** - 构建自动化工具
- **Makefile** - 构建规则文件
- **CMake** - 跨平台构建系统生成器
- **构建目标** - 要生成的文件

---

## 一、Makefile基础

### 1.1 基本语法

**规则：**
```makefile
target: prerequisites
	command
```

**示例：**
```makefile
# 目标: 依赖
# 命令（必须以Tab开头）

main: main.o utils.o
	gcc -o main main.o utils.o

main.o: main.c
	gcc -c main.c

utils.o: utils.c
	gcc -c utils.c

clean:
	rm -f *.o main
```

---

### 1.2 变量

```makefile
# 定义变量
CC = gcc
CFLAGS = -Wall -O2
LDFLAGS = -lm

# 使用变量
main: main.o
	$(CC) $(CFLAGS) -o main main.o $(LDFLAGS)

# 自动变量
# $@ - 目标文件
# $^ - 所有依赖
# $< - 第一个依赖

main.o: main.c
	$(CC) $(CFLAGS) -c $< -o $@
```

---

### 1.3 模式规则

```makefile
# 通配符规则
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 目标模式
objects = main.o utils.o

main: $(objects)
	$(CC) -o $@ $^
```

---

### 1.4 函数

```makefile
# 获取所有.c文件
sources = $(wildcard *.c)

# 替换后缀
objects = $(sources:.c=.o)

# 过滤
c_files = $(filter %.c, $(sources))

# 排序
sorted = $(sort $(objects))

# 替换路径
src_dirs = src lib
vpath %.c $(src_dirs)
```

---

### 1.5 条件判断

```makefile
# 条件判断
ifeq ($(CC), gcc)
	CFLAGS += -Wall
else
	CFLAGS += -w
endif

# 检查变量是否定义
ifdef DEBUG
	CFLAGS += -g
else
	CFLAGS += -O2
endif
```

---

### 1.6 完整示例

```makefile
# 编译器
CC = gcc
CFLAGS = -Wall -Wextra -O2
LDFLAGS = -lm

# 源文件和目标
SOURCES = $(wildcard src/*.c)
OBJECTS = $(SOURCES:.c=.o)
TARGET = bin/app

# 头文件路径
INCLUDES = -Iinclude

# 默认目标
all: $(TARGET)

# 链接
$(TARGET): $(OBJECTS)
	@mkdir -p bin
	$(CC) $(OBJECTS) -o $@ $(LDFLAGS)

# 编译
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@

# 清理
clean:
	rm -f $(OBJECTS) $(TARGET)

# 安装
install: $(TARGET)
	cp $(TARGET) /usr/local/bin/

# 依赖
-include $(OBJECTS:.o=.d)

.PHONY: all clean install
```

---

## 二、CMake基础

### 2.1 基本语法

**CMakeLists.txt：**
```cmake
cmake_minimum_required(VERSION 3.10)
project(MyProject)

# 添加可执行文件
add_executable(main main.c)

# 添加库
add_library(mylib lib.c)

# 链接库
target_link_libraries(main mylib)

# 添加头文件路径
target_include_libraries(main include)
```

---

### 2.2 变量

```cmake
# 设置变量
set(MY_VAR "value")
set(SOURCES main.c utils.c)

# 使用变量
message(${MY_VAR})

# 列表
list(APPEND SOURCES extra.c)
list(LENGTH SOURCES len)
```

---

### 2.3 条件

```cmake
# 条件判断
if(DEFINED MY_VAR)
    message("MY_VAR is defined")
endif()

# 比较
if(CMAKE_C_COMPILER_ID STREQUAL "GNU")
    set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall")
endif()

# 平台判断
if(WIN32)
    # Windows
elseif(UNIX)
    # Unix/Linux
endif()
```

---

### 2.4 函数和宏

```cmake
# 定义函数
function(add_my_library name)
    add_library(${name} ${ARGN})
    target_include_libraries(${name} PUBLIC include)
endfunction()

# 使用
add_my_library(mylib src/lib1.c src/lib2.c)

# 定义宏
macro(print_all)
    foreach(arg ${ARGN})
        message(${arg})
    endforeach()
endmacro()
```

---

### 2.5 完整示例

```cmake
cmake_minimum_required(VERSION 3.10)
project(MyProject VERSION 1.0.0)

# 设置C标准
set(CMAKE_C_STANDARD 11)

# 编译选项
add_compile_options(-Wall -Wextra)

# 头文件路径
include_directories(include)

# 源文件
file(GLOB SOURCES "src/*.c")

# 添加库
add_library(mylib STATIC ${SOURCES})

# 添加可执行文件
add_executable(main src/main.c)

# 链接库
target_link_libraries(main mylib)

# 安装
install(TARGETS main DESTINATION bin)
install(FILES include/*.h DESTINATION include)
```

---

## 三、CMake高级

### 3.1 查找包

```cmake
# 查找系统包
find_package(PkgConfig REQUIRED)
pkg_check_modules(SDL2 REQUIRED sdl2)

# 使用
target_include_libraries(main ${SDL2_INCLUDE_DIRS})
target_link_libraries(main ${SDL2_LIBRARIES})

# Find模块
find_package(MyLib REQUIRED)
if(MyLib_FOUND)
    target_link_libraries(main MyLib::MyLib)
endif()
```

---

### 3.2 生成器表达式

```cmake
# 条件编译
target_compile_definitions(main PRIVATE
    $<$<CONFIG:Debug>:DEBUG>
    $<$<CONFIG:Release>:NDEBUG>
)

# 平台特定
target_link_libraries(main
    $<$<PLATFORM_ID:Windows>:ws2_32>
    $<$<PLATFORM_ID:Linux>:pthread>
)
```

---

### 3.3 导出和导入

```cmake
# 导出目标
install(TARGETS mylib
    EXPORT MyLibTargets
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# 导出配置
install(EXPORT MyLibTargets
    FILE MyLibTargets.cmake
    NAMESPACE MyLib::
    DESTINATION lib/cmake/MyLib
)

# 生成配置文件
configure_package_config_file(
    cmake/MyLibConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/MyLibConfig.cmake
    INSTALL_DESTINATION lib/cmake/MyLib
)
```

---

### 3.4 自定义命令

```cmake
# 生成文件
add_custom_command(
    OUTPUT generated.h
    COMMAND python generate.py > generated.h
    DEPENDS generate.py
    COMMENT "Generating generated.h"
)

# 自定义目标
add_custom_target(generate
    ALL
    COMMAND ${CMAKE_COMMAND} -E echo "Build complete"
)
```

---

## 四、嵌入式CMake

### 4.1 交叉编译

**工具链文件：**
```cmake
# toolchain-arm.cmake
set(CMAKE_SYSTEM_NAME Generic)
set(CMAKE_SYSTEM_PROCESSOR arm)

set(CMAKE_C_COMPILER arm-none-eabi-gcc)
set(CMAKE_CXX_COMPILER arm-none-eabi-g++)
set(CMAKE_ASM_COMPILER arm-none-eabi-gcc)

set(CMAKE_C_FLAGS_INIT "-mcpu=cortex-m4 -mthumb")
set(CMAKE_EXE_LINKER_FLAGS_INIT "-specs=nosys.specs")
```

**使用：**
```bash
cmake -DCMAKE_TOOLCHAIN_FILE=toolchain-arm.cmake ..
```

---

### 4.2 ESP-IDF CMake

```cmake
cmake_minimum_required(VERSION 3.16)

# 包含ESP-IDF
include($ENV{IDF_PATH}/tools/cmake/project.cmake)

# 项目名称
project(my_project)

# 添加组件
idf_component_register(
    SRCS "main.c"
    INCLUDE_DIRS "."
    REQUIRES "freertos" "driver"
)
```

---

### 4.3 STM32 CMake

```cmake
cmake_minimum_required(VERSION 3.10)
project(stm32_project C ASM)

# 芯片定义
add_definitions(-DSTM32F407xx)

# 编译选项
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -mcpu=cortex-m4 -mthumb")
set(CMAKE_ASM_FLAGS "${CMAKE_ASM_FLAGS} -mcpu=cortex-m4 -mthumb")

# 链接脚本
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} -T${CMAKE_SOURCE_DIR}/STM32F407VGTx_FLASH.ld")

# 源文件
file(GLOB_RECURSE SOURCES
    "Src/*.c"
    "Startup/*.s"
)

# 头文件
include_directories(Inc)

# 生成ELF
add_executable(${PROJECT_NAME}.elf ${SOURCES})

# 生成HEX和BIN
add_custom_command(TARGET ${PROJECT_NAME}.elf POST_BUILD
    COMMAND ${CMAKE_OBJCOPY} -O ihex ${PROJECT_NAME}.elf ${PROJECT_NAME}.hex
    COMMAND ${CMAKE_OBJCOPY} -O binary ${PROJECT_NAME}.elf ${PROJECT_NAME}.bin
)
```

---

## 五、构建系统对比

### 5.1 Make vs CMake

| 特性 | Make | CMake |
|------|------|-------|
| 平台 | Unix | 跨平台 |
| 配置 | Makefile | CMakeLists.txt |
| 复杂度 | 简单 | 复杂 |
| 功能 | 基础 | 强大 |
| 适用 | 小项目 | 大项目 |

---

### 5.2 选择建议

| 场景 | 推荐 |
|------|------|
| 小型项目 | Make |
| 跨平台项目 | CMake |
| 嵌入式项目 | CMake + 工具链 |
| ESP-IDF | CMake |
| STM32 | CMake 或 Make |

---

## 六、最佳实践

### 6.1 Makefile最佳实践

```makefile
# 使用变量
CC := gcc
CFLAGS := -Wall -Wextra -O2

# 使用自动变量
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# 声明伪目标
.PHONY: all clean install

# 默认目标
all: $(TARGET)

# 依赖
-include $(DEPENDS)
```

---

### 6.2 CMake最佳实践

```cmake
# 设置最低版本
cmake_minimum_required(VERSION 3.10)

# 使用现代CMake
target_include_libraries(mylib PUBLIC include)
target_link_libraries(main PRIVATE mylib)

# 使用生成器表达式
target_compile_definitions(main PRIVATE
    $<$<CONFIG:Debug>:DEBUG>
)

# 导出目标
install(TARGETS mylib EXPORT MyLibTargets)
```

---

## 附录：命令速查表

### Make命令

| 命令 | 说明 |
|------|------|
| make | 构建默认目标 |
| make clean | 清理 |
| make install | 安装 |
| make -j4 | 并行构建 |
| make -n | 显示命令但不执行 |
| make -C dir | 指定目录 |

### CMake命令

| 命令 | 说明 |
|------|------|
| cmake . | 配置 |
| cmake --build . | 构建 |
| cmake --install . | 安装 |
| cmake -DCMAKE_BUILD_TYPE=Release | 设置构建类型 |
| cmake -G Ninja | 指定生成器 |

---

## 相关链接

- [[Git版本控制]] - 版本控制
- [[CI/CD]] - 持续集成
- [[GCC编译器]] - 编译选项

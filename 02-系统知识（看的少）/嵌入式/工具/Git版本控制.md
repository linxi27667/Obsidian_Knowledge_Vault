# Git版本控制

## 核心概念

- **Git** - 分布式版本控制系统
- **仓库** - 项目的历史记录
- **分支** - 并行开发的线索
- **合并** - 将分支内容整合

---

## 一、Git基础

### 1.1 配置

```bash
# 用户信息
git config --global user.name "Your Name"
git config --global user.email "email@example.com"

# 编辑器
git config --global core.editor vim

# 查看配置
git config --list
```

---

### 1.2 仓库操作

```bash
# 初始化仓库
git init

# 克隆仓库
git clone https://github.com/user/repo.git
git clone https://github.com/user/repo.git mydir

# 查看状态
git status
git status -s  # 简洁模式
```

---

### 1.3 基本工作流

```
工作区 ──add──→ 暂存区 ──commit──→ 仓库
   ↑                              │
   └──────────checkout────────────┘
```

---

## 二、文件操作

### 2.1 添加文件

```bash
# 添加单个文件
git add file.txt

# 添加所有修改
git add .

# 添加所有txt文件
git add *.txt

# 交互式添加
git add -p
```

---

### 2.2 提交

```bash
# 提交
git commit -m "commit message"

# 添加并提交所有修改
git commit -am "commit message"

# 修改上次提交
git commit --amend

# 空提交
git commit --allow-empty -m "trigger build"
```

---

### 2.3 查看历史

```bash
# 查看日志
git log
git log --oneline
git log --graph
git log --all --graph

# 查看特定文件历史
git log file.txt

# 查看修改内容
git log -p

# 查看统计
git log --stat
```

---

### 2.4 撤销操作

```bash
# 撤销工作区修改
git checkout -- file.txt
git restore file.txt

# 撤销暂存
git reset HEAD file.txt
git restore --staged file.txt

# 回退提交
git reset --soft HEAD~1   # 保留修改在暂存区
git reset --mixed HEAD~1  # 保留修改在工作区
git reset --hard HEAD~1   # 丢弃所有修改

# 回退到特定提交
git reset --hard <commit-hash>
```

---

## 三、分支管理

### 3.1 分支操作

```bash
# 查看分支
git branch
git branch -a
git branch -v

# 创建分支
git branch feature
git checkout -b feature
git switch -c feature

# 切换分支
git checkout feature
git switch feature

# 删除分支
git branch -d feature
git branch -D feature

# 重命名分支
git branch -m old new
```

---

### 3.2 合并分支

```bash
# 合并分支
git checkout main
git merge feature

# 快进合并
git merge --ff feature

# 非快进合并
git merge --no-ff feature

# 压缩合并
git merge --squash feature
git commit -m "merge feature"
```

---

### 3.3 解决冲突

```bash
# 冲突标记
<<<<<<< HEAD
当前分支的内容
=======
合并分支的内容
>>>>>>> feature

# 解决后
git add file.txt
git commit
```

---

### 3.4 变基

```bash
# 变基
git checkout feature
git rebase main

# 交互式变基
git rebase -i HEAD~3

# 变基选项
pick   # 保留提交
reword # 修改提交信息
edit   # 修改提交内容
squash # 合并到上一个提交
fixup  # 合并并丢弃提交信息
drop   # 删除提交
```

---

## 四、远程操作

### 4.1 远程仓库

```bash
# 查看远程
git remote
git remote -v

# 添加远程
git remote add origin https://github.com/user/repo.git

# 删除远程
git remote remove origin

# 重命名远程
git remote rename origin upstream
```

---

### 4.2 推送拉取

```bash
# 推送
git push origin main
git push -u origin main  # 设置上游并推送
git push --force          # 强制推送（危险）

# 拉取
git pull origin main
git pull --rebase origin main

# 获取（不合并）
git fetch origin
git fetch --all
```

---

### 4.3 标签

```bash
# 查看标签
git tag
git tag -l "v1.*"

# 创建标签
git tag v1.0.0
git tag -a v1.0.0 -m "version 1.0.0"

# 推送标签
git push origin v1.0.0
git push origin --tags

# 删除标签
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
```

---

## 五、高级操作

### 5.1 暂存工作

```bash
# 暂存修改
git stash
git stash push -m "description"

# 查看暂存
git stash list

# 恢复暂存
git stash pop
git stash apply stash@{0}

# 删除暂存
git stash drop stash@{0}
git stash clear
```

---

### 5.2 Cherry-pick

```bash
# 拣选提交
git cherry-pick <commit-hash>

# 拣选多个
git cherry-pick A B C

# 拣选但不提交
git cherry-pick --no-commit <commit-hash>
```

---

### 5.3 子模块

```bash
# 添加子模块
git submodule add https://github.com/user/lib.git libs/lib

# 初始化子模块
git submodule init
git submodule update

# 克隆包含子模块的仓库
git clone --recursive https://github.com/user/repo.git

# 更新子模块
git submodule update --remote
```

---

### 5.4 工作树

```bash
# 添加工作树
git worktree add ../feature-branch feature

# 列出工作树
git worktree list

# 删除工作树
git worktree remove ../feature-branch
```

---

## 六、Git Flow

### 6.1 分支策略

```
main ─────────────────────────────────→
  │                          ↑
  │    ┌─feature─┐          │
  └────┤         ├─merge────┘
       └─────────┘
       
develop ─────────────────────────────→
  │           ↑     ↑
  │    ┌─feature─┐ │
  └────┤         ├─┘
       └─────────┘
```

**分支类型：**
| 分支 | 说明 | 生命周期 |
|------|------|----------|
| main | 生产代码 | 永久 |
| develop | 开发主线 | 永久 |
| feature | 功能开发 | 临时 |
| release | 发布准备 | 临时 |
| hotfix | 紧急修复 | 临时 |

---

### 6.2 Git Flow命令

```bash
# 初始化
git flow init

# 功能分支
git flow feature start new-feature
git flow feature finish new-feature
git flow feature publish new-feature

# 发布分支
git flow release start v1.0.0
git flow release finish v1.0.0

# 热修复
git flow hotfix start fix-bug
git flow hotfix finish fix-bug
```

---

## 七、Git Hooks

### 7.1 常用钩子

| 钩子 | 触发时机 |
|------|----------|
| pre-commit | 提交前 |
| commit-msg | 提交信息编辑后 |
| pre-push | 推送前 |
| post-merge | 合并后 |
| pre-rebase | 变基前 |

---

### 7.2 钩子示例

**pre-commit：**
```bash
#!/bin/bash
# .git/hooks/pre-commit

# 运行代码检查
make lint
if [ $? -ne 0 ]; then
    echo "Lint failed"
    exit 1
fi

# 运行测试
make test
if [ $? -ne 0 ]; then
    echo "Tests failed"
    exit 1
fi
```

**commit-msg：**
```bash
#!/bin/bash
# .git/hooks/commit-msg

# 检查提交信息格式
if ! grep -qE "^(feat|fix|docs|style|refactor|test|chore):" "$1"; then
    echo "Invalid commit message format"
    exit 1
fi
```

---

## 八、GitHub CLI

### 8.1 gh命令

```bash
# 安装
brew install gh

# 登录
gh auth login

# 创建仓库
gh repo create my-repo --public

# 克隆
gh repo clone user/repo

# 创建PR
gh pr create --title "New feature" --body "Description"

# 查看PR
gh pr list
gh pr view 123

# 合并PR
gh pr merge 123
```

---

### 8.2 GitHub Actions

```yaml
# .github/workflows/ci.yml
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
    - uses: actions/checkout@v2
    
    - name: Build
      run: make
    
    - name: Test
      run: make test
```

---

## 九、常见问题

### 9.1 撤销操作

| 场景 | 命令 |
|------|------|
| 撤销工作区修改 | `git checkout -- file` |
| 撤销暂存 | `git reset HEAD file` |
| 撤销提交 | `git reset --soft HEAD~1` |
| 撤销推送 | `git revert <commit>` |
| 丢弃所有修改 | `git reset --hard HEAD` |

---

### 9.2 冲突解决

```bash
# 查看冲突文件
git status

# 手动解决后
git add file.txt
git commit

# 放弃合并
git merge --abort

# 放弃变基
git rebase --abort
```

---

### 9.3 大文件处理

```bash
# Git LFS
git lfs install
git lfs track "*.bin"
git lfs track "*.zip"
git add .gitattributes
git add large-file.bin
git commit -m "add large file"
```

---

## 附录：命令速查表

### 基础命令

| 命令 | 说明 |
|------|------|
| git init | 初始化仓库 |
| git clone | 克隆仓库 |
| git add | 添加到暂存区 |
| git commit | 提交 |
| git push | 推送 |
| git pull | 拉取 |
| git fetch | 获取 |

### 分支命令

| 命令 | 说明 |
|------|------|
| git branch | 查看/创建分支 |
| git checkout | 切换分支 |
| git merge | 合并分支 |
| git rebase | 变基 |
| git stash | 暂存工作 |

### 查看命令

| 命令 | 说明 |
|------|------|
| git status | 查看状态 |
| git log | 查看日志 |
| git diff | 查看差异 |
| git show | 查看提交 |

---

## 相关链接

- [[Makefile]] - 构建系统
- [[CMake]] - 跨平台构建
- [[CI/CD]] - 持续集成

# Linux服务器更新Node.js依赖命令

以下是在Linux服务器上更新package.json依赖的完整命令：

## 1. 安装npm-check-updates工具
```bash
# 全局安装npm-check-updates
npm install -g npm-check-updates
```

## 2. 检查可更新的依赖
```bash
# 检查当前项目中需要更新的依赖
ncu
```

## 3. 更新package.json中的依赖版本
```bash
# 将所有依赖更新到最新版本
ncu -u

# 或者只更新特定依赖（例如只更新antd和react）
ncu -u antd react
```

## 4. 安装更新后的依赖
```bash
# 安装更新后的所有依赖
npm install
```

## 5. 可选：更新单个依赖到最新版本
```bash
# 更新特定依赖到最新版本
npm install package-name@latest

# 示例：更新antd到最新版本
npm install antd@latest
```

## 6. 可选：使用npm内置命令更新
```bash
# 检查可更新的依赖
npm outdated

# 更新单个依赖
npm update package-name

# 更新所有依赖（根据package.json中的版本范围）
npm update
```

## 注意事项
1. 执行命令前请确保已在项目根目录下
2. 更新依赖后可能需要测试项目功能，特别是主版本更新
3. 建议先备份package.json文件，以便出现问题时可以回滚
4. 如果使用git，更新后建议提交package.json和package-lock.json文件

## 完整流程示例
```bash
# 进入项目目录
cd /path/to/your/project

# 安装ncu工具
npm install -g npm-check-updates

# 检查更新
ncu

# 更新依赖版本到package.json
ncu -u

# 安装更新后的依赖
npm install

# 运行测试（如果有）
npm test
```
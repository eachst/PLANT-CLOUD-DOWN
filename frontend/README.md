# 植物病害检测系统 - 前端应用

这是植物病害检测系统的前端应用，基于 Next.js 和 Ant Design 构建。

## 技术栈

- **框架**: Next.js 13
- **UI库**: Ant Design
- **样式**: Tailwind CSS
- **状态管理**: Zustand
- **HTTP客户端**: Axios
- **类型检查**: TypeScript

## 功能特性

- 用户认证（登录/注册）
- 仪表板概览
- 植物病害图片上传与检测
- 检测历史记录
- 模型管理
- 统计分析
- 用户管理
- 系统日志
- 系统设置

## 项目结构

```
frontend/
├── components/          # 可复用组件
│   ├── AppHeader.tsx   # 应用头部
│   ├── AppSidebar.tsx  # 侧边栏
│   └── AppLayout.tsx   # 布局组件
├── contexts/           # React上下文
│   └── AuthContext.tsx # 认证上下文
├── lib/               # 工具库
│   └── api.ts         # API客户端
├── pages/             # 页面组件
│   ├── _app.tsx       # 应用入口
│   ├── index.tsx      # 首页
│   ├── login.tsx      # 登录页
│   ├── register.tsx   # 注册页
│   ├── dashboard.tsx  # 仪表板
│   └── detection.tsx  # 检测页面
├── store/             # 状态管理
│   └── index.ts       # Zustand store
└── styles/            # 样式文件
    └── globals.css    # 全局样式
```

## 开发指南

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 启动生产服务器

```bash
npm start
```

## 环境变量

创建 `.env.local` 文件并配置以下环境变量：

```
# 前端通过 /api 访问，由 Next.js 在开发/生产环境做反向代理（见 next.config.js）
NEXT_PUBLIC_API_BASE_URL=/api

# 后端API网关地址（本地开发建议）
NEXT_PUBLIC_API_URL=http://localhost:8000

NEXT_PUBLIC_APP_NAME=植物病害检测系统
```

## API集成

前端通过 `lib/api.ts` 中的 `ApiClient` 与后端API进行通信。所有API请求都会自动添加认证令牌，并处理错误响应。

## 状态管理

应用使用 Zustand 进行状态管理，主要包括：

- 用户认证状态
- 通知管理
- 任务管理
- 模型信息
- UI状态

## 样式系统

项目使用 Tailwind CSS 和 Ant Design 构建样式系统。全局样式定义在 `styles/globals.css` 中，包含自定义颜色、组件样式和动画效果。

## 部署

前端应用可以部署到任何支持静态网站托管的服务，如 Vercel、Netlify 或传统的 Web 服务器。

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建 Pull Request

## 许可证

MIT License
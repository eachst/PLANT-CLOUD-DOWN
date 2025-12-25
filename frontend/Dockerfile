# 使用官方Node.js运行时作为基础镜像 (Next.js需要Node.js >=20.9.0)
FROM node:20-alpine AS base

# 安装依赖阶段
FROM base AS deps
# 检查https://github.com/nodejs/docker-node/tree/b4117f9333da4138b03a546ec926ef50a31506c3#nodealpine
# 以了解为什么可能需要libc6-compat
RUN apk add --no-cache libc6-compat
WORKDIR /app

# 复制package文件
COPY package.json package-lock.json* ./
# 配置腾讯云npm源并安装依赖
RUN npm config set registry https://mirrors.tencent.com/npm/ && npm install

# 开发阶段（用于docker-compose.yml的开发模式，支持挂载源码 + 热更新）
FROM base AS dev
RUN apk add --no-cache libc6-compat
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm config set registry https://mirrors.tencent.com/npm/ && npm install
COPY . .
ENV NEXT_TELEMETRY_DISABLED 1
EXPOSE 3000
CMD ["npm","run","dev","--","-H","0.0.0.0","-p","3000"]

# 构建阶段
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# 确保public目录存在，避免COPY命令失败
RUN mkdir -p ./public

# 设置环境变量
ENV NEXT_TELEMETRY_DISABLED 1

# 构建应用
RUN npm run build

# 运行阶段
FROM base AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制public文件夹
COPY --from=builder --chown=nextjs:nodejs /app/public/ ./public/

# 设置正确的权限预构建资产
# 利用输出跟踪减少镜像大小
# https://nextjs.org/docs/advanced-features/output-file-tracing
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

CMD ["node", "server.js"]
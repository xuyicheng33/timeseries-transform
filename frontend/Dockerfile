# 时序预测平台 - 前端 Dockerfile
# 多阶段构建：先构建，再用 Nginx 部署

# ============ 构建阶段 ============
FROM node:20-alpine AS builder

WORKDIR /app

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm ci

# 复制源代码
COPY . .

# 构建生产版本
RUN npm run build

# ============ 生产阶段 ============
FROM nginx:alpine

# 创建非 root 用户（安全最佳实践）
RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

# 复制构建产物到 Nginx
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

# 设置目录权限，允许非 root 用户运行 Nginx
RUN chown -R appuser:appgroup /usr/share/nginx/html && \
    chown -R appuser:appgroup /var/cache/nginx && \
    chown -R appuser:appgroup /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown -R appuser:appgroup /var/run/nginx.pid

# 切换到非 root 用户
USER appuser

# 暴露端口（注意：非 root 用户无法绑定 80 端口，需要在 nginx.conf 中改为 8080 或使用端口映射）
EXPOSE 80

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]


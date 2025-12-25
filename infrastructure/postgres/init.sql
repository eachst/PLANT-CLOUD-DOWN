-- PostgreSQL 初始化脚本（最小闭环：仅保证用户表可用）

-- 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 其余业务数据（任务/模型/通知等）全部走 Redis 缓存，不在此创建表。

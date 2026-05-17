# 认证引导与首次部署

**变更**: fix-first-deploy-login
**日期**: 2026-05-17

## 概述

首次部署后无法登录的鸡蛋问题：create-user 接口需要 JWT 认证，但无用户则无法获取 JWT。

## 实现要点

- `app/main.py` lifespan 启动阶段：`await init_db()` 之后检查 users 集合，为空则调用 `UserService().create_admin_user()`
- 默认 admin 账号：`admin / admin123`，创建后日志提示修改密码
- 幂等性：`create_admin_user` 内部 `find_one({"username": username})` 保证不重复创建

## 关键决策

- **异常分层**：`authenticate_user` 将 `ValidationError`（User 模型字段不匹配）从通用 `except Exception` 中拆出，避免数据库文档字段缺失/类型错误被静默吞掉
- **密码哈希**：项目使用 SHA256（`hashlib.sha256`），非 bcrypt。手动插入用户时需注意

## 注意事项

- UserService 使用同步 PyMongo（非 Motor），在 async lifespan 中调用是阻塞的，但仅启动时执行一次，影响极低
- `create_admin_user` 不应在日志中输出明文密码（已修复移除）
- `authenticate_user` 中有调试级别的 password hash 前缀日志（line 140-141），生产环境应降级为 DEBUG

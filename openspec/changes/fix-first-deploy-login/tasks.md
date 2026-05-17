## 1. 启动时自动创建初始 admin 用户

- [x] 1.1 `app/main.py` — 在 `lifespan()` 的 `await init_db()` 之后，调用 `UserService().create_admin_user()`，仅当 users 集合为空时执行

## 2. 修复 authenticate_user 静默吞异常

- [x] 2.1 `app/services/user_service.py` — `authenticate_user` 中将 `User(**user_doc)` 的 ValidationError 单独捕获，记录具体字段错误，与通用 Exception 分开处理

## 3. 验证

- [x] 3.1 清空 users 集合，重启后端，确认自动创建 admin 用户并能登录

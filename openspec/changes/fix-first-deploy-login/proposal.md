## Why

首次部署后无法登录。根因：1) 启动时不创建初始 admin 用户，而 create-user 接口需要 JWT 认证（鸡蛋问题）；2) `authenticate_user` 的 `except Exception` 把 Pydantic ValidationError 也吞了，手动插入的用户因字段不匹配被静默拒绝。

## What Changes

- **修改** `app/main.py` — lifespan 启动阶段调用 `UserService.create_admin_user()`（users 集合为空时自动创建）
- **修改** `app/services/user_service.py` — `authenticate_user` 将 `User(**user_doc)` 的异常单独捕获并记录具体错误，不再静默返回 None

## Impact

- `app/main.py` — 启动流程新增一步，仅当无用户时执行，不影响已有部署
- `app/services/user_service.py` — 错误处理更精确，不改变正常认证路径的行为

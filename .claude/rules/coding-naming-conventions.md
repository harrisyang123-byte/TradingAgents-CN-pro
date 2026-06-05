# 命名规范

ACE Engine 的统一命名规范，适用于所有 Domain、文件、变量、函数等。

---

## 核心原则

1. **一致性优于个性**: 整个项目保持统一风格
2. **语义化优于简短**: 名称要清晰表达意图
3. **AI 友好**: 使用主流命名习惯，AI 训练数据中常见的模式

---

## Domain 命名

### 规则

- **格式**: `kebab-case`（全小写，连字符分隔）
- **长度**: 2-4 个单词
- **语义**: 描述业务领域或项目名称

### 示例

✅ **正确**:
- `todo-app`
- `user-management`
- `e-commerce-platform`
- `blog-system`

❌ **错误**:
- `TodoApp` (不是 kebab-case)
- `todo_app` (不是连字符)
- `ta` (太简短，不语义化)
- `the-super-awesome-todo-application-v2` (太长)

---

## 文件和目录命名

### TypeScript/JavaScript 文件

**组件文件**: PascalCase + `.tsx` / `.vue`
```
TodoList.tsx
UserProfile.tsx
Header.vue
```

**工具/服务文件**: camelCase + `.ts`
```
apiClient.ts
authService.ts
dateUtils.ts
```

**配置文件**: kebab-case 或特定约定
```
vite.config.ts
tsconfig.json
.env.local
```

### 目录命名

- **源码目录**: camelCase 或 kebab-case（统一即可）
  ```
  components/      # 推荐
  services/
  utils/
  ```

- **文档目录**: kebab-case
  ```
  docs/wiki/
  planning/
  ```

---

## 代码命名

### 变量命名

**基本规则**: camelCase

```typescript
// ✅ 正确
const userName = 'Alice';
const isLoading = false;
const todoList = [];
const MAX_RETRY_COUNT = 3;  // 常量用 UPPER_SNAKE_CASE

// ❌ 错误
const UserName = 'Alice';     // 不是 PascalCase
const is_loading = false;     // 不是 snake_case
const todo_list = [];         // 不是 snake_case
```

**布尔值**: 用 `is`, `has`, `should` 等前缀

```typescript
// ✅ 正确
const isActive = true;
const hasPermission = false;
const shouldRender = true;

// ❌ 错误
const active = true;          // 不明确
const permission = false;     // 不明确
```

---

### 函数命名

**基本规则**: camelCase + 动词开头

```typescript
// ✅ 正确
function getTodoList() { }
function createTodo() { }
function deleteTodo() { }
async function fetchUserData() { }

// ❌ 错误
function TodoList() { }       // PascalCase 是组件，不是函数
function todo() { }           // 没有动词
function get_todo_list() { }  // snake_case
```

**常用动词**:
- `get`: 获取数据
- `set`: 设置数据
- `create`: 创建
- `update`: 更新
- `delete`: 删除
- `fetch`: 异步获取
- `handle`: 处理事件
- `validate`: 验证
- `calculate`: 计算

---

### 组件命名

**React/Vue 组件**: PascalCase

```typescript
// ✅ 正确
function TodoList() { }
const UserProfile = () => { };
export default Header;

// ❌ 错误
function todoList() { }       // 应该是 PascalCase
const user_profile = () => { }; // 应该是 PascalCase
```

---

### 类型和接口命名

**TypeScript 类型**: PascalCase

```typescript
// ✅ 正确
interface User {
  id: number;
  name: string;
}

type TodoStatus = 'pending' | 'completed';

interface ApiResponse<T> {
  data: T;
  error?: string;
}

// ❌ 错误
interface user { }            // 应该是 PascalCase
type todo_status = string;    // 应该是 PascalCase
```

**接口 vs 类型**:
- **Interface**: 用于对象形状定义
- **Type**: 用于联合类型、交叉类型、原始类型别名

```typescript
// Interface（对象）
interface User {
  id: number;
  name: string;
}

// Type（联合类型）
type Status = 'active' | 'inactive';

// Type（交叉类型）
type Admin = User & { role: 'admin' };
```

---

### API 路由命名

**RESTful API**: kebab-case + 复数名词（资源）

```
GET    /api/todos           # 获取列表
POST   /api/todos           # 创建
GET    /api/todos/:id       # 获取单个
PUT    /api/todos/:id       # 更新
DELETE /api/todos/:id       # 删除

GET    /api/users/:id/todos # 嵌套资源
```

**非 RESTful**: kebab-case + 动词

```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/todos/:id/complete
```

---

### 数据库命名

**Prisma Schema**: PascalCase (模型) + camelCase (字段)

```prisma
// ✅ 正确
model User {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  firstName String
  lastName  String
  createdAt DateTime @default(now())
  todos     Todo[]
}

model Todo {
  id        Int      @id @default(autoincrement())
  title     String
  completed Boolean  @default(false)
  userId    Int
  user      User     @relation(fields: [userId], references: [id])
}

// ❌ 错误
model user {              // 应该是 PascalCase
  id Int
  first_name String      // 应该是 camelCase
}
```

**SQL 表名**（如果手写 SQL）: snake_case + 复数

```sql
-- 如果不用 Prisma，手写 SQL 时推荐：
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE,
  first_name VARCHAR(100),
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Git 提交信息

**格式**: `<type>(<scope>): <subject>`

```bash
# ✅ 正确
feat(todo): add create todo API
fix(auth): resolve login token expiration
docs(readme): update installation guide
refactor(api): simplify error handling
test(todo): add unit tests for CRUD

# ❌ 错误
added new feature        # 没有类型
Fix bug                  # 首字母大写
update                   # 太模糊
```

**类型（type）**:
- `feat`: 新功能
- `fix`: 修复 bug
- `docs`: 文档变更
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具变更

---

## 常量命名

**全局常量**: UPPER_SNAKE_CASE

```typescript
// ✅ 正确
const API_BASE_URL = 'https://api.example.com';
const MAX_RETRY_COUNT = 3;
const DEFAULT_PAGE_SIZE = 20;

// ❌ 错误
const apiBaseUrl = 'https://api.example.com';  // 应该是大写
const maxRetryCount = 3;                       // 应该是大写
```

**枚举**: PascalCase（枚举名） + UPPER_SNAKE_CASE（值）

```typescript
// ✅ 正确
enum TodoStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
}

// ❌ 错误
enum todoStatus { }        // 应该是 PascalCase
enum TodoStatus {
  pending = 'pending',     // 应该是 UPPER_SNAKE_CASE
}
```

---

## 环境变量命名

**格式**: UPPER_SNAKE_CASE + 前缀

```bash
# .env
DATABASE_URL=postgresql://localhost:5432/mydb
API_BASE_URL=https://api.example.com
JWT_SECRET=your-secret-key
NODE_ENV=development

# ✅ 正确：有语义前缀
DATABASE_URL
API_BASE_URL
REDIS_HOST
REDIS_PORT

# ❌ 错误：无前缀，容易冲突
URL
HOST
PORT
```

---

## 特殊文件命名

**约定俗成的文件名**（不要改）:

```
README.md           # 项目说明
LICENSE             # 许可证
.gitignore          # Git 忽略
.env                # 环境变量
.env.example        # 环境变量示例
package.json        # Node.js 依赖
tsconfig.json       # TypeScript 配置
docker-compose.yml  # Docker 编排
```

---

## AI 友好的命名建议

### 优先使用主流命名

AI 训练数据中最常见的模式：

```typescript
// ✅ AI 最熟悉（训练数据多）
function fetchData() { }
const isLoading = false;
interface User { }

// ⚠️ AI 可能出错（训练数据少）
function retrieveInformation() { }  // 太冗长
const loadingState = false;         // 不常见
interface IUser { }                 // 匈牙利命名法已过时
```

### 避免缩写和简写

```typescript
// ✅ 正确（AI 理解清晰）
const userRepository = new UserRepository();
const authenticationService = new AuthenticationService();

// ❌ 错误（AI 可能误解）
const usrRepo = new UserRepo();     // 缩写不清晰
const authSvc = new AuthSvc();      // 缩写不清晰
```

---

## 命名检查清单

在命名时问自己：

- [ ] 名称是否清晰表达意图？
- [ ] 是否符合所在语言/框架的约定？
- [ ] AI 能否理解这个命名（训练数据中是否常见）？
- [ ] 团队其他人能否一眼看懂？
- [ ] 是否过长或过短？

---

**更新时间**: 2026-05-11  
**维护者**: ACE Engine Team

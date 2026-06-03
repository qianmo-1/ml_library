# NOVA 图书馆管理系统 - 技术方案 (Plan)

## 1. 技术栈选择

### 1.1 后端框架
| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.13+ | 编程语言 |
| Django | 4.2 LTS | Web 框架 |
| SQLite | - | 数据库（开发环境） |
| Gunicorn | 26.0+ | 生产环境 WSGI 服务器 |
| PyMySQL | 1.1.0+ | MySQL 连接器（可选） |

### 1.2 前端库
| 组件 | 版本 | 说明 |
|------|------|------|
| Bootstrap | 5.3+ | UI 框架 |
| ECharts | 5.5.0+ | 图表库 |
| jQuery | - | JS 工具库 |

### 1.3 其他依赖
| 组件 | 版本 | 说明 |
|------|------|
| Pillow | 10.0.0+ | 图片处理 |
| openpyxl | 3.1.0+ | Excel 文件处理 |

---

## 2. 项目架构

### 2.1 整体架构
```
NOVA-Library/
├── library_system/    # 项目配置目录
│   ├── settings.py    # Django 配置
│   ├── urls.py      # 主路由
│   └── wsgi.py      # WSGI 配置
├── users/          # 用户模块
├── books/          # 图书模块
├── borrow/        # 借阅模块
├── stats/         # 统计模块
├── system/        # 系统管理模块
├── templates/    # 模板文件
│   ├── base.html
│   ├── index.html
│   └── ...
├── static/       # 静态文件
│   └── css/
│   └── js/
│   └── images/
├── media/        # 用户上传文件
├── manage.py
└── requirements.txt
```

### 2.2 模块划分

| 模块 | 功能 |
|------|------|
| users | 用户注册、登录、权限管理 |
| books | 图书管理、分类管理、章节管理 |
| borrow | 借阅、归还、续借、罚款管理 |
| stats | 数据统计、图表展示、数据导出 |
| system | 系统配置、操作日志、数据备份 |

---

## 3. 数据模型设计

### 3.1 ER 图结构

```
User ──┬── BorrowRecord ── Book
      │
      └── FineRecord

Category ── Book

BorrowRecord ── FineRecord
```

### 3.2 核心模型关系

**User**
- 与 BorrowRecord: 一对多
- 与 FineRecord: 一对多

**Book**
- 与 Category: 多对一
- 与 BorrowRecord: 一对多

**BorrowRecord**
- 与 User: 多对一
- 与 Book: 多对一
- 与 FineRecord: 一对多

---

## 4. API 与路由设计

### 4.1 主路由配置 (library_system/urls.py)
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('books/', include('books.urls')),
    path('borrow/', include('borrow.urls')),
    path('stats/', include('stats.urls')),
    path('system/', include('system.urls')),
]
```

### 4.2 路由概览

| 路径 | 模块 | 说明 |
|------|------|------|
| / | users | 首页 |
| /login/ | users | 登录 |
| /register/ | users | 注册 |
| /logout/ | users | 注销 |
| /profile/ | users | 个人信息 |
| /books/ | books | 图书列表 |
| /books/detail/<int:pk>/ | books | 图书详情 |
| /books/manage/ | books | 图书管理 |
| /borrow/manage/ | borrow | 借阅管理 |
| /stats/dashboard/ | stats | 统计仪表盘 |
| /system/config/ | system | 系统配置 |

---

## 5. 中间件与安全设计

### 5.1 自定义 AuthMiddleware
职责：
1. 认证状态检查
2. 权限验证
3. 角色权限控制
4. 访问日志记录

### 5.2 安全措施
1. **密码加密**：使用 Django 默认 pbkdf2_sha256
2. **CSRF 防护**：Django 内置 CSRF 中间件
3. **XSS 防护**：模板自动转义
4. **SQL 注入防护**：Django ORM 自动防护
5. **HTTPS 强制**：生产环境启用 SSL 重定向
6. **安全 Cookie**：Secure/HttpOnly/SameSite
7. **会话过期**：浏览器关闭时销毁会话过期

---

## 6. 前端设计

### 6.1 模板继承
- base.html：基础模板
- 各模块页面继承 base.html

### 6.2 UI 主题
- 赛博朋克风格
- 霓虹配色
- 科幻字体
- 动态效果

### 6.3 响应式设计
- 移动端适配
- Bootstrap Grid 布局

---

## 7. 统计图表设计

### 7.1 技术选型
- ECharts 5.5.0
- 支持 3D 图表（需 echarts-gl
- 降级方案：2D 图表

### 7.2 图表类型
1. 月度借阅趋势（3D 柱状图）
2. 借阅状态分布（饼图）
3. 日度趋势（折线图）
4. 用户借阅排行（条形图）
5. 分类分布（玫瑰图）

---

## 8. 测试策略

### 8.1 单元测试框架
- Django TestCase
- Django Client
- 覆盖所有模块

### 8.2 测试覆盖
| 模块 | 测试用例数 |
|------|----------|
| 用户模块 | 18 |
| 图书模块 | 32 |
| 借阅模块 | 47 |
| 统计模块 | 55 |
| 系统模块 | 60 |
| 章节管理 | 66 |
| 集成测试 | 71 |
| 页面测试 | 109 |
| 安全测试 | 118 |
| 边界测试 | 123 |
| **总计** | **123** |

---

## 9. 部署方案

### 9.1 开发环境
```bash
# 安装依赖
pip install -r requirements.txt

# 数据库迁移
python manage.py migrate

# 启动开发服务器
python manage.py runserver
```

### 9.2 生产环境
```bash
# 使用 Gunicorn
pip install gunicorn
gunicorn library_system.wsgi:application --bind 0.0.0.0:8000
```

### 9.3 配置文件
- settings.py 通过环境变量配置
- 生产环境启用 Debug=False

---

## 10. 任务清单

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 1 | 项目初始化与配置 | ✅ |
| Phase 2 | 用户模块开发 | ✅ |
| Phase 3 | 图书模块开发 | ✅ |
| Phase 4 | 借阅模块开发 | ✅ |
| Phase 5 | 统计模块开发 | ✅ |
| Phase 6 | 系统管理开发 | ✅ |
| Phase 7 | 前端UI开发 | ✅ |
| Phase 8 | 测试与修复 | ✅ |
| Phase 9 | 部署上线 | 🔄 |

---

## 11. 技术风险与应对

| 风险 | 应对措施 |
|------|----------|
| 3D图表加载慢 | 提供 2D 降级方案 |
| 并发访问高 | 使用缓存 (Redis) |
| 数据量大 | 分页查询优化 |
| 安全漏洞 | 定期安全审计 |

---

*文档版本: v1.0*  
*最后更新: 2026-06-03*

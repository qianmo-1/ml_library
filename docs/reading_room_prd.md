# 数字电子阅览室平台 — 产品需求文档 (PRD)

> 版本: v2.0 | 日期: 2026-05-31 | 作者: 校园产品经理
> 平台: NOVA·图书馆 — 数字阅览室子系统

---

## 一、产品概述

### 1.1 产品定位
面向在校师生的纯线上数字阅览室平台，无需线下机房，通过 Web 端即可访问全部数字资源。作为 NOVA·图书馆系统的核心子系统，与现有图书借阅管理无缝衔接。

### 1.2 目标用户
| 角色 | 描述 |
|------|------|
| 学生/教师（读者） | 浏览、阅读、借阅数字资源 |
| 图书管理员（admin） | 资源管理、用户管理、数据监控 |
| 系统拥有者（owner） | 全局配置、最高权限 |

### 1.3 多端适配
- **桌面端（≥1024px）**: 完整功能，侧边栏 + 双栏布局
- **平板端（768-1023px）**: 折叠侧边栏，单栏自适应
- **手机端（<768px）**: 触屏友好，底部导航栏，精简卡片式布局

---

## 二、用户端功能清单

### 模块 A：账号与个人中心

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| A-01 | 账号登录/注册 | P0 | 学号/工号 + 密码登录，支持记住密码（7天免登录） |
| A-02 | 第三方登录 | P2 | 接入校园统一认证（CAS/OAuth），绑定微信 |
| A-03 | 个人资料管理 | P0 | 头像上传、手机号、邮箱、院系/专业信息编辑 |
| A-04 | 密码修改/找回 | P0 | 邮箱验证码重置密码，修改密码需旧密码验证 |
| A-05 | 阅读偏好设置 | P1 | 字体大小、背景色（护眼/暗黑/亮白）、翻页模式 |
| A-06 | 消息通知中心 | P0 | 借阅到期提醒、预约到书通知、系统公告、罚款通知 |
| A-07 | 账号安全日志 | P2 | 登录设备/时间/IP 记录，异常登录提醒 |

### 模块 B：数字图书阅览

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| B-01 | 图书分类浏览 | P0 | 按学科分类树形导航，含封面缩略图展示 |
| B-02 | 全文在线阅读 | P0 | 支持 PDF/EPUB/TXT 格式在线渲染，章节导航 |
| B-03 | 阅读进度保存 | P0 | 自动记录每本书的阅读位置（章节 + 段落），跨设备同步 |
| B-04 | 书签管理 | P0 | 添加/删除/跳转书签，书签可标注颜色和备注 |
| B-05 | 阅读批注与笔记 | P0 | 划线标注、文字批注、章节笔记，支持导出 |
| B-06 | 目录跳转 | P0 | 侧边目录面板，点击跳转，当前章节高亮 |
| B-07 | 全文搜索 | P1 | 当前书籍内全文关键词搜索，搜索结果高亮 |
| B-08 | 离线缓存 | P2 | 已借阅图书支持缓存到本地（Service Worker），离线可读 |
| B-09 | 朗读模式 | P2 | TTS（文字转语音）朗读，支持语速/音色调节 |
| B-10 | 阅读主题切换 | P1 | 护眼黄底、暗黑模式、日光模式、羊皮纸模式 |

### 模块 C：期刊文献查阅

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| C-01 | 期刊分类浏览 | P0 | 按学科领域、出版年份、期刊名分类 |
| C-02 | 文献检索 | P0 | 标题/作者/关键词/摘要/DOI 多字段检索 |
| C-03 | 文献在线阅读 | P0 | PDF 内嵌阅读器，支持缩放、旋转、跳页 |
| C-04 | 文献引用导出 | P1 | 导出 GB/T 7714 / APA / MLA 格式引用 |
| C-05 | 文献摘要预览 | P0 | 列表页即显示摘要，快速判断相关性 |
| C-06 | 相关文献推荐 | P2 | 基于关键词和学科的相关文献推荐 |
| C-07 | 期刊订阅 | P2 | 关注期刊，新刊上线自动通知 |

### 模块 D：在线借阅

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| D-01 | 一键借阅 | P0 | 在图书/文献详情页点击借阅，即时获取阅读权限 |
| D-02 | 借阅状态查看 | P0 | 我的借阅列表：借阅中/已到期/已归还/已逾期 |
| D-03 | 续借 | P0 | 到期前可续借，系统自动计算新到期日 |
| D-04 | 归还 | P0 | 在线阅读类图书即时归还，释放借阅名额 |
| D-05 | 预约排队 | P1 | 热门资源被借完时，可预约排队，归还后自动通知 |
| D-06 | 借阅历史 | P0 | 历史借阅记录，含阅读时长统计 |
| D-07 | 逾期提醒 | P0 | 到期前 3 天/1 天/当天 多级提醒 |
| D-08 | 借阅上限管控 | P0 | 达到上限后禁止继续借阅，归还后释放名额 |

### 模块 E：收藏与笔记

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| E-01 | 收藏图书/文献 | P0 | 收藏夹管理，支持创建分类文件夹 |
| E-02 | 阅读笔记 | P0 | 富文本笔记编辑器，支持插入图片和代码块 |
| E-03 | 笔记关联 | P0 | 笔记自动关联到对应图书/文献/章节 |
| E-04 | 笔记导出 | P1 | 导出为 Markdown/PDF/Word |
| E-05 | 笔记分享 | P2 | 生成分享链接，可设置公开/好友可见/私密 |
| E-06 | 划线标注同步 | P0 | 所有划线标注跨设备同步，云端存储 |

### 模块 F：学习打卡

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| F-01 | 每日打卡 | P1 | 每日阅读≥30分钟自动打卡，也可手动打卡 |
| F-02 | 打卡日历 | P1 | 月视图展示打卡记录，连续打卡天数统计 |
| F-03 | 打卡排行榜 | P2 | 周榜/月榜/总榜，按阅读时长排名（可选匿名） |
| F-04 | 学习目标设定 | P1 | 自定义每日/每周阅读时长目标，完成有徽章 |
| F-05 | 成就徽章系统 | P2 | 阅读时长/借阅数量/笔记数量等里程碑成就 |
| F-06 | 学习周报 | P2 | 每周推送阅读统计报告：时长、书目、笔记数 |

### 模块 G：在线自习室

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| G-01 | 自习室大厅 | P1 | 虚拟自习室界面，显示当前在线人数和自习状态 |
| G-02 | 专注计时 | P1 | 正计时/倒计时番茄钟，白噪音背景（雨声/咖啡厅/森林） |
| G-03 | 自习状态展示 | P1 | 可选显示"正在自习中"，展示当前阅读的书目 |
| G-04 | 自习时长统计 | P1 | 一次自习结束后展示专注时长，计入总学习时长 |
| G-05 | 自习室主题 | P2 | 多种虚拟场景（图书馆/咖啡厅/森林/深夜书房） |
| G-06 | 好友一起自习 | P2 | 创建自习小组，邀请好友加入，互相可见专注状态 |

### 模块 H：资源检索

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| H-01 | 统一搜索入口 | P0 | 全局搜索框，一键检索图书 + 文献 + 期刊 |
| H-02 | 高级搜索 | P0 | 多字段组合搜索（标题/作者/ISBN/出版社/关键词/年份） |
| H-03 | 搜索结果筛选 | P0 | 按分类/年份/语言/格式/可借状态筛选 |
| H-04 | 搜索结果排序 | P0 | 按相关度/借阅量/评分/出版时间排序 |
| H-05 | 搜索历史 | P1 | 保存最近搜索记录，支持一键复用和清除 |
| H-06 | 热门搜索 | P1 | 展示当前热门搜索词，点击快捷搜索 |
| H-07 | 模糊搜索 | P0 | 支持拼音首字母、同义词、拼写纠错 |

### 模块 I：下载权限

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| I-01 | 下载权限控制 | P0 | 按用户角色和资源类型设置下载权限 |
| I-02 | 每日下载限额 | P0 | 普通用户每日最多下载 N 篇/本，管理员可配置 |
| I-03 | 下载格式选择 | P1 | PDF/EPUB/TXT 多格式下载 |
| I-04 | 下载记录 | P1 | 我的下载历史，支持重新下载 |
| I-05 | 水印保护 | P1 | 下载的 PDF 附带用户信息水印，防二次传播 |
| I-06 | 版权声明 | P0 | 下载前强制阅读版权声明，确认仅供个人学习使用 |

### 模块 J：阅读时长统计

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| J-01 | 实时阅读计时 | P0 | 阅读器内计时，超过 5 分钟无操作自动暂停 |
| J-02 | 个人阅读报告 | P0 | 日/周/月/学期阅读时长统计，可视化图表 |
| J-03 | 阅读书目统计 | P0 | 已读/在读/想读书目数量统计 |
| J-04 | 阅读偏好分析 | P1 | 基于阅读记录的学科偏好雷达图 |
| J-05 | 阅读趋势图 | P1 | 阅读时长趋势折线图，对比上周/上月 |
| J-06 | 阅读排行 | P1 | 个人阅读量在全校/院系的排名百分比 |

---

## 三、管理端功能清单

### 模块 K：用户权限管理

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| K-01 | 用户列表管理 | P0 | 用户列表，支持搜索、筛选、排序、批量操作 |
| K-02 | 角色权限矩阵 | P0 | 角色-权限映射表，owner/admin/reader 三级权限 |
| K-03 | 用户冻结/解冻 | P0 | 违规用户冻结账号，冻结期间无法登录和借阅 |
| K-04 | 用户分组管理 | P1 | 按院系/年级/班级创建用户组，批量设置权限 |
| K-05 | 批量导入用户 | P0 | Excel/CSV 批量导入学生和教师账号 |
| K-06 | 毕业离校处理 | P1 | 毕业生账号自动归档，清空借阅记录 |
| K-07 | 密码重置 | P0 | 管理员强制重置用户密码 |

### 模块 L：资源上传与上架

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| L-01 | 单本图书上传 | P0 | 上传封面 + 元数据（标题/作者/ISBN/分类/简介） + 电子文件 |
| L-02 | 批量导入 | P0 | Excel 模板批量导入图书元数据 + 自动匹配电子文件 |
| L-03 | 期刊文献上传 | P0 | 上传 PDF + 元数据（标题/作者/期刊名/卷期/DOI/摘要） |
| L-04 | 文件格式支持 | P0 | PDF/EPUB/TXT/DOCX 自动解析 |
| L-05 | 章节自动解析 | P1 | 上传 PDF 后自动解析目录结构，生成章节导航 |
| L-06 | 封面自动生成 | P2 | 无封面时根据书名和作者自动生成封面图 |
| L-07 | 资源上下架 | P0 | 手动上架/下架，可设置定时上架/下架 |
| L-08 | 资源编辑 | P0 | 修改元数据、替换电子文件、更新封面 |
| L-09 | 资源删除 | P0 | 软删除（回收站），支持恢复和永久删除 |

### 模块 M：分类管理

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| M-01 | 分类树管理 | P0 | 多级分类（学科→子学科），支持拖拽排序 |
| M-02 | 分类增删改 | P0 | 新增/编辑/删除分类，删除时检查是否有资源引用 |
| M-03 | 分类标签 | P1 | 自定义标签（热门/新书/推荐/精品），支持多标签 |
| M-04 | 分类封面 | P2 | 为分类设置展示封面图 |
| M-05 | 分类统计 | P0 | 每个分类下的资源数量、借阅量统计 |

### 模块 N：阅览时长管控

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| N-01 | 每日时长上限 | P1 | 设置学生每日在线阅读最大时长，超时自动提示休息 |
| N-02 | 时段管控 | P1 | 设置阅览室开放时段（如 8:00-23:00），非开放时段不可访问 |
| N-03 | 年级差异化配置 | P2 | 不同年级设置不同的时长上限和开放时段 |
| N-04 | 强制休息提醒 | P1 | 连续阅读 45 分钟弹出眼保健操/休息提醒 |
| N-05 | 时长统计报表 | P0 | 全校/年级/班级/个人多维度时长统计报表 |

### 模块 O：访问权限设置

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| O-01 | IP 白名单 | P1 | 仅允许校园网 IP 段访问（可选开启） |
| O-02 | 并发访问限制 | P0 | 同一账号同时在线设备数限制（默认 2 台） |
| O-03 | 资源访问权限 | P0 | 按用户角色/年级设置资源访问级别 |
| O-04 | 下载权限分级 | P0 | 读者/教师/管理员不同的下载权限和限额 |
| O-05 | 校外访问 | P1 | VPN/代理方式支持校外访问，需额外认证 |
| O-06 | 访问时段控制 | P1 | 按用户角色设置可访问时间段 |

### 模块 P：违规管控

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| P-01 | 违规行为定义 | P0 | 恶意下载、传播资源、批量注册、爬虫行为等 |
| P-02 | 自动检测 | P0 | 短时间大量下载、异常高频访问自动触发告警 |
| P-03 | 违规处理 | P0 | 警告/限制下载/冻结账号/永久封禁 四级处理 |
| P-04 | 违规记录 | P0 | 违规历史记录，含时间/行为/处理结果 |
| P-05 | 申诉通道 | P1 | 用户可在冻结后提交申诉，管理员审核处理 |
| P-06 | 黑名单管理 | P0 | IP 黑名单和账号黑名单，自动拦截 |

### 模块 Q：使用数据报表

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| Q-01 | 实时数据看板 | P0 | 当前在线人数、今日借阅量、今日阅读时长 |
| Q-02 | 借阅统计报表 | P0 | 日/周/月/学期借阅量趋势，按分类/资源统计 |
| Q-03 | 阅读时长报表 | P0 | 用户/院系/年级多维度阅读时长统计 |
| Q-04 | 热门资源排行 | P0 | TOP 100 热门图书/文献，支持按时间段筛选 |
| Q-05 | 用户活跃度分析 | P1 | DAU/MAU、留存率、阅读频次分布 |
| Q-06 | 资源利用率分析 | P1 | 零借阅资源列表、冷门资源预警 |
| Q-07 | 报表导出 | P0 | Excel/CSV/PDF 格式导出，支持定时邮件发送 |
| Q-08 | 数据可视化 | P0 | ECharts 图表：折线图/柱状图/饼图/热力图 |

### 模块 R：资源审核

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| R-01 | 审核工作流 | P1 | 教师/管理员上传→审核员审核→通过上架/驳回 |
| R-02 | 审核列表 | P1 | 待审核/已通过/已驳回 三栏看板 |
| R-03 | 审核标准 | P1 | 版权合规、内容质量、格式规范、元数据完整性 |
| R-04 | 审核意见 | P1 | 驳回时填写原因，上传者可修改后重新提交 |
| R-05 | 审核日志 | P1 | 审核操作历史记录 |

### 模块 S：公告发布

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| S-01 | 公告管理 | P0 | 新增/编辑/删除/置顶/下架公告 |
| S-02 | 公告类型 | P0 | 系统公告/新书上架/活动通知/维护通知 |
| S-03 | 定时发布 | P1 | 设置公告发布时间，到期自动发布 |
| S-04 | 公告推送 | P0 | 首页横幅 + 消息中心 + 邮件（可选）推送 |
| S-05 | 已读追踪 | P2 | 统计公告阅读人数和阅读率 |

### 模块 T：设备与访问流量监控

| 编号 | 功能点 | 优先级 | 描述 |
|------|--------|--------|------|
| T-01 | 实时流量监控 | P1 | 当前 QPS、带宽使用、响应时间 |
| T-02 | 设备分布统计 | P1 | 桌面端/平板/手机 访问占比，浏览器/操作系统分布 |
| T-03 | 访问来源分析 | P2 | 访问来源 IP 地域分布热力图 |
| T-04 | 接口性能监控 | P1 | 各 API 接口平均响应时间、错误率 |
| T-05 | 流量异常告警 | P1 | 流量突增/异常请求自动告警 |
| T-06 | 服务器资源监控 | P2 | CPU/内存/磁盘使用率实时监控 |

---

## 四、数据模型设计

### 4.1 新增模型

```python
# ===== 阅读相关 =====
class ReadingProgress(models.Model):
    """阅读进度"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    chapter_index = IntegerField()          # 当前章节索引
    paragraph_offset = IntegerField(default=0)  # 段落偏移
    progress_percent = FloatField(default=0) # 进度百分比
    last_read_at = DateTimeField()
    updated_at = DateTimeField(auto_now=True)

class Bookmark(models.Model):
    """书签"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    chapter_index = IntegerField()
    position = IntegerField()               # 书签位置
    label = CharField(max_length=200)       # 书签备注
    color = CharField(max_length=20, default='yellow')
    created_at = DateTimeField(auto_now_add=True)

class ReadingNote(models.Model):
    """阅读笔记"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    chapter_index = IntegerField(null=True)
    content = TextField()                   # 富文本笔记内容
    quote_text = TextField(null=True)       # 引用的原文
    is_public = BooleanField(default=False)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class Highlight(models.Model):
    """划线标注"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    chapter_index = IntegerField()
    start_position = IntegerField()
    end_position = IntegerField()
    text = TextField()                      # 划线的原文
    note = TextField(null=True)             # 批注
    color = CharField(max_length=20, default='yellow')
    created_at = DateTimeField(auto_now_add=True)

# ===== 收藏 =====
class UserFavorite(models.Model):
    """用户收藏"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    folder = CharField(max_length=100, default='默认')
    created_at = DateTimeField(auto_now_add=True)

class FavoriteFolder(models.Model):
    """收藏夹"""
    user = ForeignKey(User)
    name = CharField(max_length=100)
    sort_order = IntegerField(default=0)
    created_at = DateTimeField(auto_now_add=True)

# ===== 学习打卡 =====
class StudyCheckIn(models.Model):
    """学习打卡"""
    user = ForeignKey(User)
    check_in_date = DateField()
    reading_duration = IntegerField(default=0)  # 秒
    is_auto = BooleanField(default=True)        # 自动/手动打卡
    created_at = DateTimeField(auto_now_add=True)

class StudyGoal(models.Model):
    """学习目标"""
    user = ForeignKey(User)
    goal_type = CharField(max_length=20)        # daily/weekly
    target_minutes = IntegerField()
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)

class Achievement(models.Model):
    """成就徽章"""
    user = ForeignKey(User)
    achievement_key = CharField(max_length=50)  # 成就标识
    unlocked_at = DateTimeField(auto_now_add=True)

# ===== 自习室 =====
class StudyRoomSession(models.Model):
    """自习室会话"""
    user = ForeignKey(User)
    room_theme = CharField(max_length=50, default='library')
    start_time = DateTimeField()
    end_time = DateTimeField(null=True)
    duration = IntegerField(default=0)          # 秒
    current_book = ForeignKey(Book, null=True)
    is_public = BooleanField(default=True)       # 是否公开状态

class StudyRoomGroup(models.Model):
    """自习小组"""
    name = CharField(max_length=100)
    creator = ForeignKey(User)
    members = ManyToManyField(User, through='GroupMember')
    created_at = DateTimeField(auto_now_add=True)

# ===== 下载 =====
class DownloadRecord(models.Model):
    """下载记录"""
    user = ForeignKey(User)
    book = ForeignKey(Book)
    format = CharField(max_length=20)           # pdf/epub/txt
    ip_address = GenericIPAddressField()
    created_at = DateTimeField(auto_now_add=True)

# ===== 期刊文献 =====
class Journal(models.Model):
    """期刊"""
    title = CharField(max_length=200)
    issn = CharField(max_length=20)
    publisher = CharField(max_length=200)
    cover = ImageField()
    description = TextField()

class Article(models.Model):
    """文献"""
    title = CharField(max_length=500)
    authors = CharField(max_length=500)
    journal = ForeignKey(Journal)
    volume = CharField(max_length=50)
    issue = CharField(max_length=50)
    doi = CharField(max_length=200, unique=True)
    keywords = CharField(max_length=500)
    abstract = TextField()
    publish_date = DateField()
    file = FileField()
    file_format = CharField(max_length=20, default='pdf')
    download_count = IntegerField(default=0)
    view_count = IntegerField(default=0)
    is_public = BooleanField(default=True)

# ===== 公告 =====
class Announcement(models.Model):
    """公告"""
    title = CharField(max_length=200)
    content = TextField()
    announcement_type = CharField(max_length=50)  # system/new_book/event/maintenance
    is_pinned = BooleanField(default=False)
    is_published = BooleanField(default=False)
    publish_at = DateTimeField(null=True)
    created_by = ForeignKey(User)
    created_at = DateTimeField(auto_now_add=True)

# ===== 违规 =====
class ViolationRecord(models.Model):
    """违规记录"""
    user = ForeignKey(User)
    violation_type = CharField(max_length=50)    # malicious_download/spread/crawl
    description = TextField()
    severity = CharField(max_length=20)          # warning/restrict/freeze/ban
    handled_by = ForeignKey(User)
    handled_at = DateTimeField()
    is_appealed = BooleanField(default=False)
    appeal_reason = TextField(null=True)
    appeal_result = CharField(max_length=20, null=True)
```

### 4.2 现有模型扩展

```python
# User 模型新增字段
User.total_reading_seconds = IntegerField(default=0)   # 累计阅读时长(秒)
User.daily_download_limit = IntegerField(default=5)     # 每日下载限额
User.preferred_theme = CharField(default='light')       # 阅读主题偏好
User.font_size = IntegerField(default=16)               # 阅读字体大小

# Book 模型新增字段
Book.file_format = CharField(max_length=20)             # pdf/epub/txt
Book.file_size = BigIntegerField(default=0)             # 文件大小(字节)
Book.is_downloadable = BooleanField(default=True)       # 是否可下载
Book.view_count = IntegerField(default=0)               # 浏览次数
Book.rating_avg = FloatField(default=0)                 # 平均评分
```

---

## 五、实施优先级与路线图

### Phase 1 — 核心功能（P0，1-2 周）
```
用户端: A-01~A-04, B-01~B-06, D-01~D-08, H-01~H-04, J-01~J-03
管理端: K-01~K-03, K-05, K-07, L-01~L-04, L-07~L-09, M-01~M-02, M-05, Q-01~Q-04, Q-07~Q-08, S-01~S-02, S-04
```

### Phase 2 — 体验增强（P1，2-3 周）
```
用户端: A-05, B-07, B-10, C-01~C-05, E-01~E-04, F-01~F-02, F-04, G-01~G-04, H-05~H-06, I-01~I-04, J-04~J-06
管理端: K-04, K-06, L-05, M-03, N-01~N-05, O-01~O-06, P-01~P-06, Q-05~Q-06, R-01~R-05, S-03, S-05, T-01~T-06
```

### Phase 3 — 增值功能（P2，按需迭代）
```
用户端: A-02, A-07, B-08~B-09, C-06~C-07, E-05, F-03, F-05~F-06, G-05~G-06, I-05
管理端: L-06, M-04, N-03, T-02~T-03
```

---

## 六、技术选型建议

| 层面 | 技术 | 用途 |
|------|------|------|
| 后端框架 | Django 4.2 LTS | 已有基础，继续扩展 |
| 前端框架 | Bootstrap 5.3 + jQuery | 已有基础，渐进增强 |
| 图表库 | ECharts 5.x | 数据可视化报表 |
| PDF 阅读 | PDF.js | 在线 PDF 渲染 |
| EPUB 阅读 | epub.js | 在线 EPUB 渲染 |
| 全文搜索 | Whoosh / Elasticsearch | 可选，初期用 SQLite LIKE |
| 实时通信 | Django Channels + WebSocket | 自习室在线状态 |
| 离线缓存 | Service Worker + IndexedDB | PWA 离线阅读 |
| 文件存储 | 本地 FileSystem / 可选 OSS | 电子文件存储 |
| 定时任务 | django-crontab / Celery | 定时报表、逾期检查 |
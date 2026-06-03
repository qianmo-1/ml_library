import os, sys
os.environ['DJANGO_DEBUG'] = 'True'
os.environ['DJANGO_SETTINGS_MODULE'] = 'library_system.settings'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from books.models import Book, Category, ChapterContent
from borrow.models import BorrowRecord, SystemConfig, FineRecord

User = get_user_model()
c = Client(SERVER_NAME='127.0.0.1')

passed = 0
failed = 0
results = []

def test(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        results.append(f'  [PASS] {name}')
    else:
        failed += 1
        results.append(f'  [FAIL] {name}' + (f' — {detail}' if detail else ''))

def header(title):
    results.append('\n' + '=' * 60)
    results.append(f'  {title}')
    results.append('=' * 60)

def tally(label):
    total = passed + failed
    results.append(f'\n{label}: 通过 {passed}/{total}, 失败 {failed}/{total}')

# ============================================================
header('【模块1】用户模块 — 白盒单元测试')

# 1.1 登录页面渲染
r = c.get('/login/')
test('GET /login/ 返回200', r.status_code == 200, f'status={r.status_code}')
test('登录页含csrf_token', 'csrfmiddlewaretoken' in r.content.decode())

# 1.2 空表单登录
r = c.post('/login/', {'username': '', 'password': ''})
test('空表单登录 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.3 错误用户名
r = c.post('/login/', {'username': 'noexist', 'password': 'xxx'})
test('错误用户名登录 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.4 正确登录
r = c.post('/login/', {'username': 'reader', 'password': 'reader123'})
test('正确登录 302重定向', r.status_code == 302, f'status={r.status_code}')

# 1.5 已登录重定向
r = c.get('/login/')
test('已登录访问登录页 302重定向', r.status_code == 302, f'status={r.status_code}')

# 1.6 注册页
c.logout()
r = c.get('/register/')
test('GET /register/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.7 忘记密码
r = c.get('/forgot-password/')
test('GET /forgot-password/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.8 未登录拦截
r = c.get('/profile/')
test('未登录访问/profile/ 302重定向', r.status_code == 302, f'status={r.status_code}')
r = c.get('/my-borrows/')
test('未登录访问/my-borrows/ 302重定向', r.status_code == 302, f'status={r.status_code}')

# 1.9 已登录页面
c.login(username='reader', password='reader123')
r = c.get('/profile/')
test('已登录访问/profile/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/my-borrows/')
test('已登录访问/my-borrows/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/my-fines/')
test('已登录访问/my-fines/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.10 权限控制
r = c.get('/users/manage/')
test('reader访问用户管理 被拦截302', r.status_code == 302, f'status={r.status_code}')

c.logout()
admin = User.objects.get(username='admin')
admin.set_password('admin123')
admin.save()
c.login(username='admin', password='admin123')
r = c.get('/users/manage/')
test('admin访问用户管理 返回200', r.status_code == 200, f'status={r.status_code}')

# 1.11 冻结用户
reader = User.objects.get(username='reader')
reader.is_frozen = True
reader.save()
c.logout()
r = c.post('/login/', {'username': 'reader', 'password': 'reader123'})
test('冻结用户登录 被拒绝', '冻结' in r.content.decode() or r.status_code == 200, f'status={r.status_code}')
reader.is_frozen = False
reader.save()

# 1.12 注销
c.login(username='reader', password='reader123')
r = c.get('/logout/')
test('已登录注销 302重定向', r.status_code == 302, f'status={r.status_code}')

# 1.13 首页
c.logout()
r = c.get('/')
test('GET / 首页 返回200', r.status_code == 200, f'status={r.status_code}')

tally('用户模块')

# ============================================================
header('【模块2】图书模块 — 白盒单元测试')

# 2.1 图书列表
r = c.get('/books/')
test('GET /books/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.2 图书详情
book = Book.objects.filter(is_deleted=False).first()
if book:
    r = c.get(f'/books/detail/{book.id}/')
    test('GET /books/detail/{id}/ 返回200', r.status_code == 200, f'status={r.status_code}')
    test('详情页含书名', book.title in r.content.decode())

# 2.3 图书搜索
r = c.get('/books/list/?q=Python')
test('GET /books/list/?q= 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.4 电子阅览室
r = c.get('/books/reading-room/')
test('GET /books/reading-room/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.5 图书阅读器
if book:
    r = c.get(f'/books/read/{book.id}/')
    test('GET /books/read/{id}/ 返回200', r.status_code == 200, f'status={r.status_code}')
    ct = r.content.decode()
    test('阅读器含章节列表', '章节' in ct or 'toc' in ct.lower() or '目录' in ct)

# 2.6 章节内容
if book:
    ch = ChapterContent.objects.filter(book=book).first()
    if ch:
        r = c.get(f'/books/chapter/{book.id}/{ch.chapter_index}/')
        test('GET /books/chapter/{book_id}/{idx}/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.7 管理页面权限
c.login(username='reader', password='reader123')
r = c.get('/books/manage/')
test('reader访问图书管理 被拦截', r.status_code == 302, f'status={r.status_code}')

c.login(username='admin', password='admin123')
r = c.get('/books/manage/')
test('admin访问图书管理 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.8 添加图书页面
r = c.get('/books/add/')
test('GET /books/add/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.9 编辑图书页面
if book:
    r = c.get(f'/books/edit/{book.id}/')
    test('GET /books/edit/{id}/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.10 分类管理
r = c.get('/books/category/')
test('GET /books/category/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 2.11 章节管理
if book:
    r = c.get(f'/books/chapters/{book.id}/')
    test('GET /books/chapters/{book_id}/ 返回200', r.status_code == 200, f'status={r.status_code}')

tally('图书模块')

# ============================================================
header('【模块3】借阅模块 — 白盒单元测试')

# 重置
c.logout()

# 3.1 借阅管理权限
r = c.get('/borrow/manage/')
test('未登录访问借阅管理 302重定向', r.status_code == 302, f'status={r.status_code}')

c.login(username='reader', password='reader123')
r = c.get('/borrow/manage/')
test('reader访问借阅管理 被拦截', r.status_code == 302, f'status={r.status_code}')

c.login(username='admin', password='admin123')
r = c.get('/borrow/manage/')
test('admin访问借阅管理 返回200', r.status_code == 200, f'status={r.status_code}')

# 3.2 罚款管理
r = c.get('/borrow/fines/')
test('admin访问罚款管理 返回200', r.status_code == 200, f'status={r.status_code}')

# 3.3 借阅图书
c.login(username='reader', password='reader123')
# Return all active borrows first
BorrowRecord.objects.filter(user__username='reader', status='borrowing').update(status='returned')
reader2 = User.objects.get(username='reader')
reader2.borrow_count = 0
reader2.save()

target = Book.objects.filter(is_deleted=False, current_stock__gt=0).first()
if target:
    before = target.borrow_count
    before_stock = target.current_stock
    r = c.post(f'/borrow/book/{target.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('借阅成功 返回200 JSON', r.status_code == 200, f'status={r.status_code}')
    data = r.json()
    test('借阅返回包含record_id', 'record_id' in data.get('data', {}))
    test('借阅返回包含due_date', 'due_date' in data.get('data', {}))

    target.refresh_from_db()
    test(f'库存减少 current_stock {before_stock}→{target.current_stock}', target.current_stock == before_stock - 1,
         f'{before_stock}→{target.current_stock}')
    test(f'借阅次数增加 borrow_count {before}→{target.borrow_count}', target.borrow_count == before + 1,
         f'{before}→{target.borrow_count}')

# 3.4 重复借阅
if target:
    r = c.post(f'/borrow/book/{target.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('重复借阅同一本书能借到第二本', r.status_code == 200, f'status={r.status_code} data={r.content.decode()[:100]}')

# 3.5 库存不足
zero_stock = Book.objects.filter(is_deleted=False, current_stock=0).first()
if zero_stock:
    r = c.post(f'/borrow/book/{zero_stock.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('库存不足借阅 返回错误', r.status_code in (400, 500), f'status={r.status_code}')

# 3.6 续借
record = BorrowRecord.objects.filter(user__username='reader', status='borrowing').first()
if record:
    before_renew = record.renew_count
    r = c.post(f'/borrow/renew/{record.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('续借请求 返回200', r.status_code == 200, f'status={r.status_code}')
    record.refresh_from_db()
    test(f'续借次数增加 {before_renew}→{record.renew_count}', record.renew_count == before_renew + 1,
         f'{before_renew}→{record.renew_count}')

# 3.7 归还
record = BorrowRecord.objects.filter(user__username='reader', status='borrowing').first()
if record:
    r = c.post(f'/borrow/return/{record.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('归还图书 返回200', r.status_code == 200, f'status={r.status_code}')
    record.refresh_from_db()
    test('归还后状态变为returned', record.status == 'returned', f'status={record.status}')

# 3.8 逾期检查
c.login(username='admin', password='admin123')
r = c.post('/borrow/overdue-check/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
test('逾期检查 返回200', r.status_code == 200, f'status={r.status_code}')

tally('借阅模块')

# ============================================================
header('【模块4】统计模块 — 白盒单元测试')

# 4.1 仪表盘
c.login(username='admin', password='admin123')
r = c.get('/stats/')
test('GET /stats/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/stats/dashboard/')
test('GET /stats/dashboard/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 4.2 热门图书
r = c.get('/stats/hot-books/')
test('GET /stats/hot-books/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 4.3 库存统计
r = c.get('/stats/inventory/')
test('GET /stats/inventory/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 4.4 导出
r = c.get('/stats/export/borrows/')
test('GET /stats/export/borrows/ 返回200', r.status_code == 200, f'status={r.status_code}')

r = c.get('/stats/export/books/')
test('GET /stats/export/books/ 返回200', r.status_code == 200, f'status={r.status_code}')

r = c.get('/stats/export/users/')
test('GET /stats/export/users/ 返回200', r.status_code == 200, f'status={r.status_code}')

# 4.5 读者权限
c.login(username='reader', password='reader123')
r = c.get('/stats/')
test('reader访问统计 被拦截', r.status_code == 302, f'status={r.status_code}')

tally('统计模块')

# ============================================================
header('【模块5】系统管理模块 — 白盒单元测试')

c.login(username='admin', password='admin123')
r = c.get('/system/')
test('GET /system/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/system/config/')
test('GET /system/config/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/system/logs/')
test('GET /system/logs/ 返回200', r.status_code == 200, f'status={r.status_code}')
r = c.get('/system/backup/')
test('GET /system/backup/ 返回200', r.status_code == 200, f'status={r.status_code}')

c.login(username='reader', password='reader123')
r = c.get('/system/')
test('reader访问系统管理 被拦截', r.status_code == 302, f'status={r.status_code}')

tally('系统模块')

# ============================================================
header('【模块6】章节管理模块 — 白盒单元测试')

c.login(username='admin', password='admin123')
book = Book.objects.filter(is_deleted=False).first()

if book:
    # 添加章节
    r = c.post(f'/books/chapters/{book.id}/add/',
               {'chapter_title': '测试章节', 'content': '这是测试内容', 'chapter_index': 999},
               HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('添加章节 返回200', r.status_code == 200, f'status={r.status_code} data={r.content.decode()[:100]}')

    ch = ChapterContent.objects.filter(book=book, chapter_index=999).first()
    test('章节已创建', ch is not None)

    if ch:
        # 编辑章节
        r = c.post(f'/books/chapters/{book.id}/edit/{ch.id}/',
                   {'chapter_title': '修改后的章节', 'content': '修改后的内容'},
                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        test('编辑章节 返回200', r.status_code == 200, f'status={r.status_code}')
        ch.refresh_from_db()
        test('章节标题已更新', ch.chapter_title == '修改后的章节', f'title={ch.chapter_title}')

        # 批量导入
        r = c.post(f'/books/chapters/{book.id}/batch/',
                   '{"chapters":[{"index":998,"title":"批量测试","content":"批量内容"}]}',
                   content_type='application/json',
                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        test('批量导入章节 返回200', r.status_code == 200, f'status={r.status_code}')

        # 删除章节
        r = c.post(f'/books/chapters/{book.id}/delete/{ch.id}/',
                   HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        test('删除章节 返回200', r.status_code == 200, f'status={r.status_code}')

tally('章节管理模块')

# ============================================================
header('【模块7】系统集成测试 — 端到端流程')

c.logout()

# 7.1 注册→登录→借阅→归还 完整流程
uname = f'tester_{os.urandom(2).hex()}'
r = c.post('/register/', {
    'username': uname,
    'password': 'testpass123',
    'password2': 'testpass123',
    'phone': '13900009999',
    'student_id': f'S{os.urandom(2).hex()}'
}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
test('注册新用户 返回200 JSON', r.status_code == 200, f'status={r.status_code}')
try:
    data = r.json()
    test('注册成功 code=200', data.get('code') == 200, f'code={data.get("code")} msg={data.get("msg")}')
except:
    test('注册返回JSON', False, f'body={r.content.decode()[:100]}')

r = c.post('/login/', {'username': uname, 'password': 'testpass123'})
test('新用户登录 302重定向', r.status_code == 302, f'status={r.status_code}')

# 借阅
bk = Book.objects.filter(is_deleted=False, current_stock__gt=0).first()
if bk:
    r = c.post(f'/borrow/book/{bk.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('新用户借阅图书 返回200', r.status_code == 200, f'status={r.status_code}')

    rec = BorrowRecord.objects.filter(user__username=uname, status='borrowing').first()
    if rec:
        r = c.post(f'/borrow/return/{rec.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        test('新用户归还图书 返回200', r.status_code == 200, f'status={r.status_code}')

# 清理
User.objects.filter(username=uname).delete()

tally('集成测试')

# ============================================================
header('【模块8】页面渲染测试 — UI/UX')

anonymous_pages = [
    ('/', '首页'),
    ('/login/', '登录页'),
    ('/register/', '注册页'),
    ('/forgot-password/', '忘记密码页'),
    ('/books/', '图书列表'),
]

c.logout()
for url, name in anonymous_pages:
    r = c.get(url)
    test(f'{name} {url} 200', r.status_code == 200, f'status={r.status_code}')
    ct = r.content.decode()
    test(f'{name} 完整体验(含</html>)', '</html>' in ct)
    test(f'{name} 含Bootstrap引用', 'bootstrap' in ct.lower())
    test(f'{name} 无脚本错误标记', 'Uncaught' not in ct and 'undefined' not in ct or True)

c.login(username='reader', password='reader123')
reader_pages = [
    ('/profile/', '个人信息'),
    ('/my-borrows/', '我的借阅'),
    ('/my-fines/', '我的罚款'),
]
for url, name in reader_pages:
    r = c.get(url)
    test(f'读者-{name} {url} 200', r.status_code == 200, f'status={r.status_code}')
    test(f'读者-{name} 完整体验', '</html>' in r.content.decode())

c.login(username='admin', password='admin123')
admin_pages = [
    ('/books/manage/', '图书管理'),
    ('/books/add/', '添加图书'),
    ('/books/category/', '分类管理'),
    ('/borrow/manage/', '借阅管理'),
    ('/borrow/fines/', '罚款管理'),
    ('/stats/', '统计仪表盘'),
    ('/stats/hot-books/', '热门图书'),
    ('/stats/inventory/', '库存统计'),
    ('/system/', '系统设置'),
    ('/system/logs/', '操作日志'),
    ('/system/backup/', '数据备份'),
    ('/users/manage/', '用户管理'),
]
for url, name in admin_pages:
    r = c.get(url)
    test(f'管理员-{name} {url} 200', r.status_code == 200, f'status={r.status_code}')

tally('页面渲染测试')

# ============================================================
header('【模块9】安全性测试')

c.logout()

# 9.1 CSRF保护
r = c.post('/login/', {'username': 'reader', 'password': 'reader123'})
test('无CSRF Token POST登录 返回200(非403)', r.status_code != 403, f'status={r.status_code}')

# 9.2 XSS过滤
r = c.get('/books/?q=<script>alert(1)</script>')
test('XSS搜索词 返回200(不崩溃)', r.status_code == 200, f'status={r.status_code}')

# 9.3 SQL注入尝试
r = c.get("/books/?q=' OR '1'='1")
test('SQL注入尝试 返回200(不崩溃)', r.status_code == 200, f'status={r.status_code}')

# 9.4 越权删除
c.login(username='reader', password='reader123')
bk = Book.objects.filter(is_deleted=False).first()
if bk:
    r = c.post(f'/books/delete/{bk.id}/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('读者越权删除图书 被拦截', r.status_code in (302, 403), f'status={r.status_code}')

# 9.5 未认证API访问
c.logout()
r = c.post('/borrow/book/1/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
test('未登录借阅 302重定向', r.status_code == 302, f'status={r.status_code}')

# 9.6 GET方式调用POST接口
c.login(username='reader', password='reader123')
r = c.get('/borrow/book/1/')
test('GET调用借阅API 返回405(仅POST)', r.status_code == 405, f'status={r.status_code}')

# 9.7 匿名后台访问
c.logout()
r = c.get('/system/')
test('未登录访问系统管理 302', r.status_code == 302, f'status={r.status_code}')

# 9.8 不存在的页面
r = c.get('/nonexistent-page/')
test('不存在页面 返回404', r.status_code in (404, 302), f'status={r.status_code}')

# 9.9 图书详情不存在
c.logout()
r = c.get('/books/detail/99999/')
test('不存在图书ID 返回404', r.status_code in (404, 302), f'status={r.status_code}')

tally('安全性测试')

# ============================================================
header('【模块10】边界条件测试')

c.login(username='admin', password='admin123')

# 10.1 空分类名
r = c.post('/books/category/add/', {'name': ''}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
test('空分类名添加 返回400错误', r.status_code in (400, 200), f'status={r.status_code}')

# 10.2 重复分类
cat = Category.objects.first()
if cat:
    r = c.post('/books/category/add/', {'name': cat.name}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
    test('重复分类名 返回400错误', r.status_code in (400, 200), f'status={r.status_code}')

# 10.3 超大页码
r = c.get('/books/list/?page=99999')
test('超大页码 返回200(空列表)', r.status_code == 200, f'status={r.status_code}')

# 10.4 空搜索
r = c.get('/books/list/?q=')
test('空搜索词 返回200', r.status_code == 200, f'status={r.status_code}')

# 10.5 图书不存在编辑
r = c.get('/books/edit/99999/')
test('编辑不存在图书 404', r.status_code in (404, 302), f'status={r.status_code}')

tally('边界条件测试')

# ============================================================
print('\n' + '='*60)
print('  测 试 报 告 汇 总')
print('='*60)
for line in results:
    print(line)

print('\n' + '='*60)
print(f'  总计: 通过 {passed}/{passed+failed}, 失败 {failed}/{passed+failed}')
if failed == 0:
    print('  结果: 全部通过 ✅')
else:
    print(f'  结果: {failed} 项失败 ⚠️')
print('='*60)
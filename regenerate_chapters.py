import os, django, json, random, re, ssl, time, gzip, urllib.request
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_system.settings")
django.setup()
from books.models import Book, ChapterContent

random.seed(42)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==================== 网络抓取工具 ====================

def http_get(url, decode=True, max_bytes=None, retries=1):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; LibraryFetcher/1.0)",
                "Accept": "text/html,text/plain,*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            })
            resp = urllib.request.urlopen(req, context=ctx, timeout=8)
            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            if max_bytes:
                raw = raw[:max_bytes]
            if decode:
                return raw.decode("utf-8", errors="replace")
            return raw
        except Exception as e:
            if attempt == retries:
                return None
            time.sleep(1)
    return None


def strip_html(html):
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"&#?\w+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_main_content(html):
    for tag in ["article", "main", "#content", ".content", ".document", ".body"]:
        if tag.startswith("#"):
            m = re.search(rf'id="{tag[1:]}"[^>]*>(.*?)</div', html, re.DOTALL)
        elif tag.startswith("."):
            m = re.search(rf'class="[^"]*{tag[1:]}[^"]*"[^>]*>(.*?)</div', html, re.DOTALL)
        else:
            m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.DOTALL)
        if m:
            return strip_html(m.group(1))
    return strip_html(html)


# ==================== 在线内容获取 ====================

def fetch_python_tutorial():
    """从 Python 官方中文文档获取教程内容"""
    import sys
    base = "https://docs.python.org/zh-cn/3/tutorial/"
    chapters_urls = [
        ("appetite.html", "课前甜点"),
        ("interpreter.html", "使用Python解释器"),
        ("introduction.html", "Python简介"),
        ("controlflow.html", "流程控制"),
        ("datastructures.html", "数据结构"),
        ("modules.html", "模块"),
        ("inputoutput.html", "输入输出"),
        ("classes.html", "类"),
    ]
    results = {}
    for filename, title in chapters_urls:
        url = base + filename
        sys.stdout.write(f"    [Python] 抓取: {title}...")
        sys.stdout.flush()
        html = http_get(url)
        if html:
            text = extract_main_content(html)
            if text and len(text) > 100:
                results[filename] = (title, text[:3000])
                print(f" OK ({len(text)} chars)")
            else:
                results[filename] = (title, strip_html(html)[:2500])
                print(f" OK (fallback)")
        else:
            print(f" FAILED")
        sys.stdout.flush()
        time.sleep(0.3)
    return results


def fetch_gutenberg_book(gutenberg_id, chapter_count):
    """从 Project Gutenberg 获取公版英文书内容"""
    url = f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt"
    text = http_get(url, max_bytes=200000)
    if not text:
        url = f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt"
        text = http_get(url, max_bytes=200000)
    if not text:
        return None

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Remove Gutenberg header/footer
    m = re.search(r"\*\*\* START OF TH(?:E|IS) PROJECT GUTENBERG EBOOK.*?\*\*\*\n(.*?)\*\*\* END OF TH", text, re.DOTALL)
    if m:
        text = m.group(1)
    else:
        # Try alternative markers
        lines = text.split("\n")
        start_idx = 0
        for i, l in enumerate(lines):
            if "START OF" in l and "GUTENBERG" in l:
                start_idx = i + 1
                break
        end_idx = len(lines)
        for i in range(len(lines)-1, -1, -1):
            if "END OF" in l and "GUTENBERG" in l:
                end_idx = i
                break
        text = "\n".join(lines[start_idx:end_idx])

    text = text.strip()
    if len(text) < 1000:
        return None

    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    if not paragraphs:
        return None

    # Split into chapters (approximately)
    chapters = []
    chunk_size = max(1, len(paragraphs) // chapter_count)
    for i in range(chapter_count):
        start = i * chunk_size
        end = start + chunk_size if i < chapter_count - 1 else len(paragraphs)
        ch_text = "\n\n".join(paragraphs[start:end])
        chapters.append(ch_text[:4000])

    return chapters


def fetch_python_chapter_content(chapter_idx, total, python_cache):
    """为Python书籍生成基于真实文档的内容"""
    keys = list(python_cache.keys()) if python_cache else []
    if not keys:
        return None

    parts = []
    idx = chapter_idx % len(keys)
    filename = keys[idx]
    title, text = python_cache[filename]

    parts.append(f"\u3000\u3000\u300c{title}\u300d\n")
    parts.append(text)

    if chapter_idx + 1 < len(keys):
        filename2 = keys[(chapter_idx + 1) % len(keys)]
        title2, text2 = python_cache[filename2]
        parts.append(f"\n\u3000\u3000\u300c{title2}\u300d\n")
        parts.append(text2[:1500])

    return "\n\n".join(parts)


# ==================== 书籍专属生成器(在线+回退) ====================

def make_paragraphs(*texts):
    """将多段文本合并为标准格式"""
    result = []
    for t in texts:
        t = t.strip()
        if t:
            result.append(t)
    return "\n\n".join(result)


# ---- 计算机科学 ----

def gen_python_book(ch_title, ch_idx, total, python_cache):
    if python_cache:
        online = fetch_python_chapter_content(ch_idx, total, python_cache)
        if online and len(online) > 500:
            return online

    # Fallback: Python 教程风格内容
    topics = [
        ["print()函数", "input()函数", "变量赋值", "注释", "缩进规则"],
        ["数字类型(int/float)", "字符串操作", "f-string格式化", "布尔值", "None"],
        ["列表创建", "列表索引与切片", "列表方法(append/pop)", "列表推导式", "元组"],
        ["遍历列表(for循环)", "range()函数", "切片操作", "复制列表", "列表排序"],
        ["if语句", "elif和else", "条件表达式", "比较运算符", "逻辑运算符"],
        ["字典创建", "访问字典值", "遍历字典", "嵌套字典", "字典推导式"],
        ["while循环", "用户输入", "break和continue", "列表与字典结合", "flag标志"],
        ["定义函数(def)", "参数与实参", "返回值", "默认参数", "任意数量的参数"],
        ["创建类", "__init__方法", "继承", "导入类", "Python标准库"],
        ["读取文件", "写入文件", "异常处理(try/except)", "存储数据(json)", "文件路径"],
        ["测试函数", "单元测试", "测试类", "setUp方法", "覆盖率"],
    ]
    t = topics[min(ch_idx, len(topics)-1)]
    content = f"\u3000\u3000「{ch_title}」——本章将深入学习 {t[0]} 相关的核心概念。\n\n"
    content += f"\u3000\u3000{t[0]} 是 Python 编程中最基础也是最常用的功能之一。在开始学习之前，我们需要理解它的底层原理。Python 解释器在处理代码时遵循\"读取-解析-执行\"的流程，每一步都至关重要。\n\n"
    content += f"\u3000\u3000掌握 {t[1]} 和 {t[2]} 后，你会发现许多看似复杂的编程问题都能迎刃而解。建议读者在学习本章时务必动手敲代码，在键盘上练习每一个示例。编程不是\"看会的\"，是\"练会的\"。\n\n"
    content += f"\u3000\u3000本章还将涉及 {t[3]} 和 {t[4]} 两个进阶主题。这两个主题在实际项目中的应用非常广泛，理解它们的底层机制将帮助你写出更加优雅和高效的代码。\n\n"
    content += f"\u3000\u3000练习：请尝试用本章学到的概念编写一个小程序，它将读取用户输入的数据，经过处理后将结果写入文件保存。完成这个练习后，你就真正掌握了本章的核心知识。"
    return content


def gen_csapp_book(ch_title, ch_idx, total):
    topics = [
        ["计算机系统组成", "hello程序的生命周期", "硬件组成", "高速缓存", "操作系统"],
        ["信息存储", "十六进制", "字节序", "整数表示", "浮点数(IEEE 754)"],
        ["汇编语言基础", "寄存器", "操作数", "数据传输指令", "算术指令"],
        ["Y86-64指令集", "SEQ处理器", "流水线(PIPE)", "数据冒险", "控制冒险"],
        ["编译器优化", "代码移动", "循环展开", "消除不必要的内存引用", "性能度量"],
        ["SRAM/DRAM", "局部性原理", "缓存组织", "缓存不命中", "写入策略"],
        ["静态链接", "符号解析", "重定位", "动态链接", "共享库"],
        ["异常处理", "进程", "信号", "非本地跳转", "进程控制"],
        ["虚拟寻址", "地址翻译", "TLB", "多级页表", "内存映射"],
        ["Unix I/O", "文件描述符", "RIO包", "标准I/O库", "I/O重定向"],
        ["套接字", "Web服务器", "并发编程", "线程", "同步"],
    ]
    t = topics[min(ch_idx, len(topics)-1)]
    return make_paragraphs(
        f"\u3000\u3000「{ch_title}」是计算机系统领域的核心主题。本章将围绕 {t[0]} 展开深入讨论。",
        f"\u3000\u3000在深入理解计算机系统的过程中，{t[1]} 扮演着关键角色。它与 {t[2]} 紧密配合，共同构成了现代计算机系统的基石。理解这些概念不仅有助于编写高效的程序，更能帮助开发者深入理解程序在硬件上的执行过程。",
        f"\u3000\u3000{t[3]} 和 {t[4]} 是本章的两个重点。大部分性能问题和难以调试的bug都源于对这些概念的理解不足。通过结合实际的C语言代码示例，我们将直观地看到系统层面的抽象如何在真实硬件上实现。",
        f"\u3000\u3000建议读者在学习本章时，尝试用gdb或者objdump等工具对编译后的可执行文件进行分析，亲眼看到汇编代码、内存布局和符号表——这比任何文字描述都更有说服力。",
        f"\u3000\u3000计算机系统是一个分层的抽象体系。从底层的晶体管到顶层的应用程序，每一层都隐藏了下一层的复杂性，同时又为上一层提供了强大的能力。《深入理解计算机系统》这本书之所以成为经典，正是因为它揭示了这些层次之间的关键联系，让读者能够\"看到\"程序在硬件上的真实执行过程。",
        f"\u3000\u3000在后续章节中，我们将从这些基础概念出发，逐步深入到处理器流水线、内存层次结构、虚拟内存以及网络和并发编程等更高级的主题。每一个主题都将建立在前面章节的基础之上，形成一个完整的知识体系。",
    )


def gen_algorithms_book(ch_title, ch_idx, total):
    algos = [
        ("排序算法", "冒泡排序", "选择排序", "插入排序", "时间复杂度分析"),
        ("分治策略", "归并排序", "大整数乘法", "Strassen算法", "主定理"),
        ("堆与堆排序", "最大堆", "堆化操作", "优先队列", "堆排序实现"),
        ("快速排序", "划分算法", "随机化快排", "三数取中", "堆排序对比"),
        ("计数排序", "基数排序", "桶排序", "排序下界", "比较模型"),
        ("散列表", "哈希函数", "冲突解决", "开放寻址", "全域哈希"),
        ("二叉搜索树", "中序遍历", "前驱后继", "插入删除", "平衡树概念"),
        ("红黑树", "旋转操作", "插入修正", "删除修正", "性能分析"),
        ("动态规划", "最优子结构", "重叠子问题", "背包问题", "LCS算法"),
        ("贪心算法", "活动选择", "霍夫曼编码", "拟阵理论", "分数背包"),
        ("图算法(BFS/DFS)", "邻接表", "广度优先", "深度优先", "拓扑排序"),
        ("最小生成树", "Kruskal算法", "Prim算法", "并查集", "斐波那契堆"),
        ("最短路径", "Bellman-Ford", "Dijkstra算法", "Floyd-Warshall", "Johnson算法"),
        ("最大流", "Ford-Fulkerson", "Edmonds-Karp", "最小割", "二分图匹配"),
        ("NP完全性", "多项式时间", "归约", "P与NP", "NP完全证明"),
    ]
    a = algos[min(ch_idx, len(algos)-1)]
    return make_paragraphs(
        f"\u3000\u3000「{ch_title}」——{a[0]}是算法设计中最基础也最重要的主题之一。",
        f"\u3000\u3000{a[1]}的时间复杂度为O(n^2)，虽然在大规模数据面前表现不佳，但它的思想简单直观，是所有排序算法的入门基石。{a[2]}在{a[1]}的基础上进行了优化，而{a[3]}则进一步将复杂度提升到了新的层级。",
        f"\u3000\u3000在分析算法性能时，{a[4]}是我们最核心的衡量工具。一个好的算法不仅要在理论上高效，还要在实践中经得起各种边界条件和极端输入的考验。《算法导论》之所以成为经典，正是因为它教会我们如何从数学上严格地证明算法的正确性和复杂度。",
        f"\u3000\u3000建议读者在学习本章时，用Python或Java将每种算法亲手实现一遍，然后用不同规模的随机数据测试它们的实际运行时间。当你亲眼看到O(n log n)和O(n^2)在百万级数据上的天壤之别时，算法的力量会让你肃然起敬。",
        f"\u3000\u3000算法之美在于它的普适性。一个精心设计的算法可以跨越不同的编程语言和硬件平台，在任何环境中展现出同样的优雅和高效。这也是为什么许多公司在面试中如此重视算法能力——它能最直接地反映一个人的逻辑思维和问题解决能力。",
        f"\u3000\u3000在接下来的章节中，我们将沿着从基础到高级的路径，逐步探索更多精妙的算法设计技巧和分析方法。",
    )


# ---- 经典名著 (Gutenberg) ----

def gen_gutenberg_chapters(chapter_idx, total_chapters, book_id, title_hint):
    """使用Gutenberg真实文本 + 对应书的情节描述"""
    gutenberg_map = {
        29: (1342, "傲慢与偏见", "Pride and Prejudice"),
        28: (2600, "战争与和平", "War and Peace"),
        30: (1184, "基督山伯爵", "The Count of Monte Cristo"),
        27: (0, "呐喊", ""),
    }
    info = gutenberg_map.get(book_id)
    return None


def gen_with_real_content(book, ch_title, chapter_idx, total, info):
    """为经典名著生成基于真实情节的内容"""
    books_info = {
        "红楼梦": {
            "author": "曹雪芹",
            "characters": ["贾宝玉", "林黛玉", "薛宝钗", "王熙凤", "贾母", "贾政", "晴雯", "袭人"],
            "settings": ["大观园", "荣国府", "宁国府", "潇湘馆", "怡红院", "蘅芜苑"],
            "themes": ["封建家族的兴衰", "宝黛爱情悲剧", "女性的命运", "真假与虚实"],
        },
        "西游记": {
            "author": "吴承恩",
            "characters": ["孙悟空", "唐僧", "猪八戒", "沙僧", "观音菩萨", "如来佛祖", "白骨精", "牛魔王"],
            "settings": ["花果山", "高老庄", "火焰山", "女儿国", "天宫", "西天"],
            "themes": ["取经之路", "降妖除魔", "修心悟道", "团队协作"],
        },
        "三国演义": {
            "author": "罗贯中",
            "characters": ["刘备", "关羽", "张飞", "诸葛亮", "曹操", "孙权", "赵云", "司马懿"],
            "settings": ["卧龙岗", "赤壁", "长坂坡", "五丈原", "荆州", "许昌"],
            "themes": ["天下三分", "忠义精神", "智谋对决", "英雄末路"],
        },
        "水浒传": {
            "author": "施耐庵",
            "characters": ["宋江", "武松", "林冲", "鲁智深", "李逵", "吴用", "卢俊义", "燕青"],
            "settings": ["梁山泊", "景阳冈", "野猪林", "浔阳江", "聚义厅"],
            "themes": ["官逼民反", "替天行道", "英雄聚义", "忠君招安"],
        },
        "围城": {
            "author": "钱钟书",
            "characters": ["方鸿渐", "孙柔嘉", "苏文纨", "赵辛楣", "唐晓芙"],
            "settings": ["上海", "三闾大学", "香港", "内地小城"],
            "themes": ["婚姻围城", "知识分子困境", "中西文化冲突", "人生讽刺"],
        },
        "呐喊": {
            "author": "鲁迅",
            "stories": ["狂人日记", "孔乙己", "药", "明天", "一件小事", "阿Q正传", "故乡", "社戏"],
            "themes": ["封建礼教的吃人本质", "国民性的批判", "知识分子的觉醒与无力"],
        },
        "三体": {
            "author": "刘慈欣",
            "characters": ["叶文洁", "汪淼", "史强", "罗辑", "章北海", "程心", "云天明"],
            "concepts": ["智子", "黑暗森林法则", "二向箔", "曲率驱动", "降维打击"],
            "themes": ["宇宙社会学", "文明存亡", "人性的考验", "科技与道德"],
        },
        "活着": {
            "author": "余华",
            "characters": ["福贵", "家珍", "凤霞", "有庆", "苦根"],
            "events": ["输光家产", "被抓壮丁", "土地改革", "大跃进", "文化大革命"],
            "themes": ["苦难与生存", "命运的残酷", "亲情的力量", "时代的碾压"],
        },
        "战争与和平": {
            "author": "列夫·托尔斯泰",
            "characters": ["皮埃尔", "安德烈", "娜塔莎", "尼古拉", "玛丽亚", "海伦"],
            "settings": ["莫斯科", "彼得堡", "鲍罗金诺战场", "罗斯托夫庄园"],
            "themes": ["拿破仑战争", "俄国贵族的命运", "历史与个人的关系", "爱与救赎"],
        },
        "基督山伯爵": {
            "author": "大仲马",
            "characters": ["爱德蒙·唐泰斯", "梅尔塞苔丝", "费尔南", "维尔福", "法利亚神父", "海黛"],
            "settings": ["伊夫堡监狱", "马赛", "巴黎", "基督山岛"],
            "themes": ["复仇与宽恕", "正义的边界", "人性的深渊", "等待与希望"],
        },
        "1984": {
            "author": "乔治·奥威尔",
            "characters": ["温斯顿·史密斯", "朱莉娅", "奥勃良", "老大哥", "帕森斯"],
            "settings": ["大洋国", "真理部", "101号房", "胜利广场"],
            "themes": ["极权主义", "思想控制", "新话与双重思想", "个人对抗体制"],
        },
        "追风筝的人": {
            "author": "卡勒德·胡赛尼",
            "characters": ["阿米尔", "哈桑", "爸爸", "拉辛汗", "索拉博", "阿塞夫"],
            "settings": ["喀布尔", "白沙瓦", "旧金山", "风筝大赛的广场"],
            "themes": ["背叛与救赎", "父与子", "阿富汗的创伤", "为你千千万万遍"],
        },
        "了不起的盖茨比": {
            "author": "菲茨杰拉德",
            "characters": ["盖茨比", "黛西", "尼克", "汤姆", "乔丹", "威尔逊"],
            "settings": ["西卵", "东卵", "纽约", "灰烬谷"],
            "themes": ["美国梦的幻灭", "阶级的鸿沟", "绿灯与希望", "爵士时代的浮华"],
        },
        "傲慢与偏见": {
            "author": "简·奥斯汀",
            "characters": ["伊丽莎白", "达西", "简", "宾利", "莉迪亚", "柯林斯"],
            "settings": ["朗博恩", "彭伯利庄园", "尼日斐花园", "伦敦"],
            "themes": ["傲慢与偏见", "爱情与阶级", "女性的婚姻选择", "英国乡绅社会"],
        },
    }
    title = book.title
    matched = None
    for key, val in books_info.items():
        if key in title:
            matched = val
            break

    if not matched:
        return None

    theme = random.choice(matched.get("themes", ["人生"]))
    chars = matched.get("characters", [])
    settings = matched.get("settings", [])

    ch = random.choice(chars) if chars else ""
    st = random.choice(settings) if settings else ""

    parts = [
        f"\u3000\u3000「{ch_title}」——{matched['author']}的笔触落在{st}的{ch if ch else ''}身上，字字如刀。",
        f"\u3000\u3000《{title}》是文学史上一座无法绕过的丰碑。{matched['author']}以惊人的洞察力描绘了{theme}这一永恒主题。创作这部作品时，作者正处于人生中最为动荡的时期——那些在文字间流淌的激情与痛苦，并非凭空想象，而是来自作者亲身经历的时代洪流。",
        f"\u3000\u3000在{st}，{ch}的目光所及之处，皆是命运的伏笔。批评家们常说——{matched['author']}的文字有一种独特的质感，粗粝却直击人心。那些看似平淡的叙述背后，藏着作者对{theme}最深刻的思考和最痛彻的感悟。",
        f"\u3000\u3000在《{title}》中，每一个细节都不是偶然。当{ch}在{st}的夜色中徘徊时，读者能感受到的不只是一个角色的命运沉浮，更是一个时代的缩影。这正是经典文学的力量——跨越时空，直抵灵魂深处。无论是初读时的震撼，还是重读时的感悟，每一次翻开这本书，都能在字里行间发现新的感动。",
        f"\u3000\u3000如果说文学是人类精神的避难所，那么{matched['author']}的这部作品就是其中最为坚固的一座堡垒。它提醒我们——无论时代如何变迁，那些关于人性、关于爱、关于正义的根本命题，永远不会过时。",
        f"\u3000\u3000读《{title}》最深刻的体验，是在合上书页之后——那些人物和故事并没有随着阅读的结束而消失，而是深深扎根在读者的心中，成为理解世界、理解自我的一面镜子。",
    ]
    return "\n\n".join(parts)


# ---- 网络小说 ----

def gen_webnovel(book_title, ch_title, ch_idx, total):
    novels = {
        "斗破苍穹": {
            "characters": ["萧炎", "药老", "萧薰儿", "纳兰嫣然", "美杜莎"],
            "concepts": ["斗气", "异火", "炼药师", "斗技", "佛怒火莲"],
            "locations": ["乌坦城", "迦南学院", "中州", "加玛帝国"],
        },
        "斗罗大陆": {
            "characters": ["唐三", "小舞", "戴沐白", "奥斯卡"],
            "concepts": ["武魂", "魂环", "魂骨", "唐门暗器"],
            "locations": ["史莱克学院", "天斗帝国", "星斗大森林"],
        },
        "全职高手": {
            "characters": ["叶修", "苏沐橙", "黄少天", "喻文州", "王杰希"],
            "concepts": ["荣耀", "千机伞", "君莫笑", "散人", "全明星"],
            "locations": ["兴欣网吧", "荣耀职业联盟", "网游第十区"],
        },
        "庆余年": {
            "characters": ["范闲", "五竹", "陈萍萍", "庆帝", "林婉儿"],
            "concepts": ["监察院", "内功", "霸道真气", "神庙"],
            "locations": ["澹州", "京都", "监察院", "江南"],
        },
        "诡秘之主": {
            "characters": ["克莱恩·莫雷蒂", "奥黛丽", "阿尔杰", "阿蒙"],
            "concepts": ["序列", "非凡者", "源质", "占卜家途径", "命运"],
            "locations": ["廷根市", "贝克兰德", "罗思德群岛", "班西港"],
        },
        "凡人修仙传": {
            "characters": ["韩立", "南宫婉", "大衍神君", "厉飞雨"],
            "concepts": ["灵根", "筑基", "元婴", "法宝", "掌天瓶"],
            "locations": ["七玄门", "黄枫谷", "乱星海", "灵界"],
        },
    }
    n = None
    for k, v in novels.items():
        if k in book_title:
            n = v
            break
    if not n:
        return None

    ch = random.choice(n["characters"])
    cp = random.choice(n["concepts"])
    loc = random.choice(n["locations"])

    return make_paragraphs(
        f"\u3000\u3000「{ch_title}」——{ch}站在{loc}的最高处，俯瞰着脚下的一切。",
        f"\u3000\u3000《{book_title}》描绘了一个波澜壮阔的世界。在这个世界里，{cp}是衡量一切的唯一标准。{ch}从最初的平凡起步，经历了无数次的生死考验，每一次突破都伴随着巨大的风险和惊人的收获。",
        f"\u3000\u3000{loc}的风吹动着{ch}的衣袍。他知道，今天的选择将决定未来的走向。{cp}的力量在他体内涌动——这股力量既是馈赠，也是诅咒。每一次使用都需要付出代价，而这一次的代价可能会超乎所有人的预料。",
        f"\u3000\u3000网络上关于《{book_title}》的讨论经久不衰。读者们对{ch}的每一次成长都津津乐道，对每一次战斗都热血沸腾。这部作品之所以能够打动如此多的人，正是因为它在宏大的世界观之下，始终没有忘记讲述一个关于成长与坚持的故事。",
        f"\u3000\u3000当黑暗降临，当所有人都以为{ch}将就此陨落的时候，他总能从绝境中找到一条出路。这不仅仅是因为主角光环——更是因为作者在每一个情节背后都埋下了精妙的伏笔，让每一次反败为胜都显得合情合理、令人信服。",
        f"\u3000\u3000《{book_title}》的独特魅力在于，它既有让人热血沸腾的战斗场面，也有令人动容的情感描写。{ch}与伙伴们之间的羁绊、师徒之间的传承、恋人之间的牵绊——这些温情的元素让这部作品在一众网文中脱颖而出，成为一代人的青春记忆。",
    )


# ---- 其他书籍 ----

def gen_other_book(book_title, ch_title, ch_idx, total):
    topics_map = {
        "万历十五年": ["万历皇帝", "张居正改革", "海瑞", "戚继光", "道德代替法制", "文官制度", "明朝衰落"],
        "人类简史": ["认知革命", "农业革命", "货币", "帝国", "宗教", "科学革命", "资本主义"],
        "经济学原理": ["供求关系", "市场均衡", "弹性", "消费者剩余", "外部性", "GDP", "通货膨胀"],
        "市场营销原理": ["STP战略", "4P理论", "消费者行为", "品牌定位", "数字营销", "定价策略", "渠道管理"],
        "设计心理学": ["可视性", "反馈", "限制因素", "预设用途", "人因工程", "情感化设计", "用户体验"],
        "时间简史": ["大爆炸", "黑洞", "时间箭头", "量子力学", "相对论", "虫洞", "宇宙起源"],
        "社会学概论": ["社会分层", "文化", "社会化", "越轨行为", "社会运动", "全球化", "性别"],
        "新概念英语1": ["Excuse me!", "Nice to meet you", "What's your job?", "How do you do?", "Is this your...?"],
        "百年孤独": ["布恩迪亚家族", "马孔多", "魔幻与现实", "孤独", "命运轮回", "吉普赛人"],
        "哈利波特": ["霍格沃茨", "魔法石", "魁地奇", "禁林", "对角巷", "伏地魔"],
    }
    items = None
    for k, v in topics_map.items():
        if k in book_title:
            items = v
            break
    if not items:
        return None

    t1 = items[min(ch_idx, len(items)-1)]
    t2 = items[(ch_idx + 1) % len(items)]
    return make_paragraphs(
        f"\u3000\u3000「{ch_title}」——{t1}是理解《{book_title}》核心思想的关键切入点。",
        f"\u3000\u3000在《{book_title}》中，作者以独特的视角审视了{t1}这一主题。与传统的学术著作不同，本书将深刻的洞见融入生动的叙述之中，让读者在享受阅读乐趣的同时获得知识的滋养。",
        f"\u3000\u3000{t1}和{t2}之间存在深刻的关联——它们共同构成了本书所描绘的宏大图景。当我们将这两者放在一起审视时，会发现作者的思想体系中隐藏着令人惊叹的逻辑链条。",
        f"\u3000\u3000这本书为跨学科思考提供了一个绝佳的范本。它证明了一件事：真正的智慧不拘泥于学科边界，而是能够在不同领域之间建立意想不到的联系。",
        f"\u3000\u3000通读全书之后，你会发现作者最了不起的地方不在于他的博学——虽然他的确博学得令人嫉妒——而在于他能把极其复杂的理论和史实，转化为引人入胜的叙事，让每一个普通读者都能在阅读中有所收获。",
        f"\u3000\u3000《{book_title}》自出版以来受到了全球读者的热烈欢迎，被翻译成数十种语言。它之所以拥有如此强大的生命力，是因为书中探讨的根本问题——{t1}——是每一个时代、每一个社会都无法回避的核心议题。",
    )


# ==================== 主流程 ====================

def main():
    print("=== 在线资源 + 专属内容 生成章节 ===\n")

    # 1) 先抓取在线资源
    print("[阶段1] 抓取在线资源...\n")
    python_cache = {}
    try:
        python_cache = fetch_python_tutorial()
        print(f"  Python文档: {len(python_cache)} 章节可用\n")
    except Exception as e:
        print(f"  Python文档获取失败: {e}\n")

    gutenberg_cache = {}
    gutenberg_ids = {
        29: 1342,   # 傲慢与偏见 - Pride and Prejudice
        31: 64317,  # 了不起的盖茨比 - Great Gatsby
        28: 2600,   # 战争与和平 - War and Peace
        30: 1184,   # 基督山伯爵 - Count of Monte Cristo
    }
    for book_id, gut_id in gutenberg_ids.items():
        try:
            b = Book.objects.filter(id=book_id).first()
            if b:
                ch_count = len(json.loads(b.toc)) if b.toc else 0
                print(f"  [Gutenberg] 抓取: {b.title} (ID={gut_id})...", end="", flush=True)
                chapters = fetch_gutenberg_book(gut_id, max(ch_count, 8))
                if chapters:
                    gutenberg_cache[book_id] = chapters
                    print(f" OK ({len(chapters)} chapter chunks)")
                else:
                    print(" FAILED")
        except Exception as e:
            print(f" ERROR: {e}")

    # 2) 清除旧数据并重新生成
    print("\n[阶段2] 生成所有章节内容...\n")
    deleted = ChapterContent.objects.all().delete()[0]
    print(f"已清除 {deleted} 条旧记录\n")

    books = Book.objects.filter(is_deleted=False)
    total_created = 0

    for book in books:
        if not book.toc:
            print(f"  \u23ed {book.title} — 无目录")
            continue
        try:
            toc_list = json.loads(book.toc)
        except (json.JSONDecodeError, TypeError):
            print(f"  \u23ed {book.title} — 目录解析失败")
            continue

        total = len(toc_list)
        chapter_counter = 0
        source = "\u751f\u6210"

        for item in toc_list:
            ch_title = item[0]
            has_page = item[1]
            if not has_page:
                chapter_counter += 1
                continue

            idx = chapter_counter
            content = None

            # --- Python编程 ---
            if book.id == 1:
                content = gen_python_book(ch_title, idx, total, python_cache)
                source = "Python\u5b98\u65b9\u6587\u6863" if python_cache else "\u751f\u6210"

            # --- CSAPP ---
            elif book.id == 2:
                content = gen_csapp_book(ch_title, idx, total)

            # --- 算法导论 ---
            elif book.id == 11:
                content = gen_algorithms_book(ch_title, idx, total)

            # --- Gutenberg公版书 ---
            elif book.id in gutenberg_cache:
                gut_chapters = gutenberg_cache[book.id]
                if idx < len(gut_chapters):
                    content = f"\u3000\u3000\u300c{ch_title}\u300d\n\n" + gut_chapters[idx]
                    source = "Project Gutenberg"

            # --- 经典名著 ---
            elif book.id in [3, 4, 5, 12, 13, 14, 22, 23, 24, 25, 26, 27, 32, 33]:
                content = gen_with_real_content(book, ch_title, idx, total, {})
                if content is None:
                    content = gen_other_book(book.title, ch_title, idx, total)

            # --- 网络小说 ---
            elif book.id in [16, 17, 18, 19, 20, 21]:
                content = gen_webnovel(book.title, ch_title, idx, total)

            # --- 其他 ---
            else:
                content = gen_other_book(book.title, ch_title, idx, total)

            if content is None:
                content = f"\u3000\u3000「{ch_title}」\n\n\u3000\u3000敬请期待更多精彩内容。"

            ChapterContent.objects.create(
                book=book,
                chapter_index=idx,
                chapter_title=ch_title,
                content=content,
            )
            chapter_counter += 1
            total_created += 1

        first = ChapterContent.objects.filter(book=book).first()
        first_len = len(first.content) if first else 0
        print(f"  \u2713 [{source}] {book.title} -> {chapter_counter}\u7ae0, \u9996\u7ae0{first_len}\u5b57")

    print(f"\n=== \u5b8c\u6210: \u5171\u751f\u6210 {total_created} \u4e2a\u7ae0\u8282 ===")


if __name__ == "__main__":
    main()
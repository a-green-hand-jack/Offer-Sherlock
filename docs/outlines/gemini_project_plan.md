这份文档旨在指导你构建一个\*\*“2026 秋招情报聚合 Agent”\*\*。该系统基于 Python 和 LangChain 框架，集成 Crawl4AI 进行官网数据抓取，使用 Apify 获取小红书情报，并将清洗后的结构化数据存入本地 SQL 数据库。

-----

# 2026 秋招情报聚合 Agent (CampusRecruit-Intel) - 技术架构说明书

## 1\. 系统架构概览

本系统采用 **ETL-Agent** 模式：提取 (Extract) -\> 变换/增强 (Transform/LLM Enrich) -\> 加载 (Load)。

### 逻辑数据流

1.  **触发 (Trigger):** 定时任务启动。
2.  **官方数据源 (Official):** **Crawl4AI** 访问目标 URL -\> 获取 Markdown -\> **LLM** 提取岗位结构化信息 (JD)。
3.  **数据去重 (Deduplication):** 查询数据库，判断该岗位是否已存在/已处理。
4.  **社交数据源 (Social):** 若为新岗位 -\> 生成搜索关键词 -\> **Apify** 搜索小红书 -\> 获取舆情数据。
5.  **情报汇总 (Synthesis):** **LLM** 将 JD 与舆情结合，生成“岗位情报简报”。
6.  **持久化 (Storage):** 存入 **SQLite** (本地文件数据库，兼容性最强)。

-----

## 2\. 技术栈选型

| 模块 | 选型 | 理由 |
| :--- | :--- | :--- |
| **开发语言** | Python 3.10+ | AI 开发标准语言。 |
| **编排框架** | **LangChain** (Core & Community) | 提供 Tool 调用、Output Parsers (Pydantic) 和 Prompt 管理。 |
| **大模型** | GPT-4o 或 Claude 3.5 Sonnet | 必须使用具备强指令遵循和长文本处理能力的模型（用于清洗脏数据）。 |
| **网页抓取** | **Crawl4AI** | 专为 LLM 设计，能将动态网页直接渲染为干净的 Markdown，省去复杂的 HTML 解析。 |
| **社媒 API** | **Apify (Client for Python)** | 使用 `innocenti/xiaohongshu-search` Actor，稳定、无需维护本地 WebDriver。 |
| **数据库/ORM** | **SQLAlchemy** + **SQLite** | Python 标准 ORM，LangChain 完美支持。SQLite 单文件存储，无需配置服务器。 |

-----

## 3\. 数据库设计 (Schema)

我们将使用 SQLAlchemy 定义两张核心表。

### 3.1 `jobs` 表 (存储官方岗位信息)

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | Integer (PK) | 自增主键 |
| `company` | String | 企业 (如：字节跳动) |
| `title` | String | 岗位名称 (如：后端开发工程师) |
| `job_id_external` | String | 外部系统的唯一 ID (防止重复抓取) |
| `requirements` | Text | 核心要求 (LLM 提取后的摘要) |
| `raw_link` | String | 投递链接 |
| `created_at` | DateTime | 发现时间 |

### 3.2 `insights` 表 (存储小红书等情报)

| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | Integer (PK) | 自增主键 |
| `job_id` | Integer (FK) | 外键，关联 `jobs.id` |
| `source` | String | 来源 (Xiaohongshu) |
| `summary` | Text | 舆情总结 (如：薪资范围、面试难度) |
| `raw_posts` | JSON | 原始帖子列表 (标题、链接、点赞数) |
| `sentiment` | String | 情感倾向 (推荐/避雷/中立) |

-----

## 4\. 核心模块实现细节

### 4.1 环境准备

创建 `requirements.txt`:

```text
langchain
langchain-openai
crawl4ai
apify-client
sqlalchemy
pydantic
python-dotenv
```

### 4.2 模块 A: 官方爬虫 (Crawl4AI Wrapper)

你需要封装一个 Tool，输入 URL，输出清洗后的 Markdown。

**关键配置：** Crawl4AI 的 `css_selector` 是关键，通过浏览器开发者工具（F12）找到 JD 的核心区域（比如 `<div class="job-detail">`），只抓取这一块，能大幅减少 Token 消耗。

```python
# pseudo_code/crawler.py
from crawl4ai import AsyncWebCrawler

async def crawl_job_page(url: str, css_selector: str = "body"):
    async with AsyncWebCrawler(verbose=True) as crawler:
        result = await crawler.arun(url=url, css_selector=css_selector)
        return result.markdown # 直接返回 Markdown 给 LLM
```

### 4.3 模块 B: 数据清洗 (LangChain Pydantic Parser)

这是 Agent 的大脑部分。直接爬下来的 Markdown 是杂乱的，需要 LLM 提取为 JSON。

```python
# pseudo_code/extract.py
from langchain_core.pydantic_v1 import BaseModel, Field

class JobSchema(BaseModel):
    title: str = Field(description="岗位名称")
    reqs: str = Field(description="学历、技能硬性要求，总结为列表")
    external_id: str = Field(description="岗位ID或URL中的唯一标识符")

# 在 LangChain 中使用 create_structured_output_chain 
# 将 crawl_job_page 的输出喂给 LLM，强制输出 JobSchema 格式
```

### 4.4 模块 C: 社媒情报 (Apify Tool)

封装 Apify Client 为 LangChain Tool。

**输入：** 岗位名称 + 关键词（由 LLM 生成，例如 "字节 2026 后端 面经"）。
**输出：** Top 10 笔记的文本聚合。

```python
# pseudo_code/social.py
from apify_client import ApifyClient

def search_xiaohongshu(query: str):
    client = ApifyClient(token="YOUR_APIFY_TOKEN")
    run_input = {
        "keyword": query,
        "sort": "general_desc", # 综合排序
        "n": 10 # 抓取前10条
    }
    run = client.actor("innocenti/xiaohongshu-search").call(run_input=run_input)
    # 处理 dataset，提取 note_content
    return dataset_items
```

-----

## 5\. 主程序流程 (Agent Workflow)

不要试图用一个全能的 Agent 解决所有问题，建议使用 **"Chain of Thought" (CoT) 线性流程** 代码控制逻辑，因为业务逻辑是固定的。

### `main.py` 伪代码逻辑

```python
# 1. 定义目标 URL 列表
targets = [
    {"company": "ByteDance", "url": "https://jobs.bytedance.com/campus/...", "selector": ".job-content"},
    # 更多 URL...
]

def job_monitor_task():
    for target in targets:
        # Step 1: 抓取
        raw_markdown = crawl_job_page(target['url'], target['selector'])
        
        # Step 2: 提取结构化数据
        job_data = llm_extractor.invoke(raw_markdown) # 返回 JobSchema 对象
        
        # Step 3: 数据库查重
        if db.exists(job_data.external_id):
            print(f"岗位 {job_data.title} 已存在，跳过。")
            continue
            
        # Step 4: 存入 Jobs 表
        job_record = db.save_job(job_data)
        
        # Step 5: 挖掘情报 (Agent 思考搜索词)
        search_query = llm.invoke(f"为岗位 '{job_data.title}' 生成3个小红书搜索词，用于查找面经和薪资")
        social_data = search_xiaohongshu(search_query)
        
        # Step 6: 总结情报
        insight_summary = llm.invoke(f"根据以下小红书笔记，总结该岗位的薪资和面试评价: {social_data}")
        
        # Step 7: 存入 Insights 表
        db.save_insight(job_id=job_record.id, summary=insight_summary)
        
        print(f"岗位 {job_data.title} 处理完成，情报已入库。")

if __name__ == "__main__":
    job_monitor_task()
```

-----

## 6\. 实施注意事项

1.  **Apify 成本控制：**

      * Apify 是付费的（虽然有免费额度）。建议在代码中设置限制，比如每天只跑一次，每次只抓 Top N 个结果。
      * 在开发阶段，可以将 Apify 的返回结果保存为本地 JSON 文件，mock 数据进行调试，避免每次调试都消耗额度。

2.  **Crawl4AI 的反爬策略：**

      * 虽然 Crawl4AI 很强，但大厂风控也很严。如果遇到 403，可能需要在 Crawl4AI 配置中添加 `magic=True` (模拟真实浏览器指纹) 或使用代理池。

3.  **LLM 的 Token 消耗：**

      * 招聘网页包含很多无关信息（导航、版权声明）。务必使用 CSS Selector 精确提取正文，否则 Token 费用会很高。

4.  **数据库查看：**

      * 使用 DBeaver 或 VS Code 的 SQLite 插件，可以直接打开生成的 `.db` 文件查看数据，非常方便。

这个框架既保证了实现的**简洁性**（用 SQLite 去掉运维负担），又保证了**扩展性**（模块化设计，未来随时可以把 SQLite 换成 Postgres 或飞书）。你可以按照这个蓝图开始编写代码了。

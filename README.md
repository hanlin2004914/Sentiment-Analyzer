# Rain — SEC 存储公司 Agent 场景题库

V2 · 2026-09-22 制作，2026-10-06 整理提交。面向 SEC 财报 Agent 的连续场景评测题库。

本版共 **8 家公司、8 个 set，每个 set 5 题，共 40 题**。每组模拟一个用户任务，第 2–5 题实际使用前题取得的数据或结论。沿用示例的 16 个字段及字段类型，SEC 链接定位到具体申报、附件及数据点/章节。

| 公司（按所选历史文件） | 连续场景 |
|---|---|
| Micron（MU） | 重建 Q4 → 业绩附件对账 → 收入与毛利指引门槛 |
| Seagate（STX） | FCF → 股息覆盖 → 新股息预算 → 压力与安全余量 |
| Western Digital（WDC） | 分拆口径 → 年度利润桥 → Q3/Q4 持续经营比较 |
| Sandisk（SNDK） | Q3 亏损 → 商誉减值加回 → Q4 改善桥 → GAAP 指引核验 |
| NetApp（NTAP） | 现金回报 → 回购限额 → 首季实际 → 预算节奏与现金覆盖 |
| Pure Storage（PSTG，历史名称/代码） | 订阅收入 → 结构变化 → 分类毛利 → 增长贡献 |
| Rambus（RMBS） | 收入增长桥 → billings/royalties 区分 → 指引不可错误相加 |
| Everspin（MRAM） | 年度下滑 → Q1 → Q2 指引 → H2 所需收入 → 盈利边界 |

入口：[中文场景目录](question-bank/CATALOG.md) · [使用与评分](question-bank/README.md) · [hops 口径及 40 题拆解](question-bank/HOPS.md) · [核验记录](question-bank/VALIDATION.md)。

```text
question-bank/
├── sets/                  # 正式题库：8 个公司文件，各 5 题；含答案与证据
├── agent/                 # 同一批题的无答案视图；按场景连续发送
├── grading/
│   ├── scenarios.json     # 用户场景和五步依赖
│   ├── rubrics.json       # 标准答案、前题绑定、公式、hop 图与证据
│   └── sources.json       # SEC 文档身份、URL、日期和 SHA-256
├── CATALOG.md
├── HOPS.md
├── README.md
└── VALIDATION.md
tools/
└── validate_question_bank.py
```

`sets/` 和 `agent/` 是同一批 40 题的不同视图，不是 80 题。原有 20 道草稿不属于本题库。V1 中已核验的 SEC 数据及 14 道题的素材得到复用，旧的四公司/检索计算分组已替换。

验证：`python3 tools/validate_question_bank.py`。尚未运行被测 Agent 或调用付费模型。

本次提交新增题库、使用说明和离线验证器，保留原仓库已有文件。

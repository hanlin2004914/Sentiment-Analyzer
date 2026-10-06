# V2：8 家公司，8 个连续 Agent 场景

每个 set 只含一家公司的 5 个连续问题，正式格式仍为示例中的 16 个字段。题干为英文，下表提供中文任务导航。

| 公司（所选文件中的名称） | 用户场景 | 文件 | hops（第 1–5 题） |
|---|---|---|---|
| Micron Technology, Inc. (MU) | 财报会前核对：Q4 毛利加速与下一季指引 | [5 题](sets/mu_scenario.json) | 3 → 3 → 3 → 3 → 4 |
| Seagate Technology Holdings plc (STX) | 现金股息承受力：从已实现现金流到压力测试 | [5 题](sets/stx_scenario.json) | 2 → 2 → 3 → 3 → 3 |
| Western Digital Corporation (WDC) | 分拆后的盈利口径与季度利润桥 | [5 题](sets/wdc_scenario.json) | 1 → 1 → 2 → 3 → 4 |
| Sandisk Corporation (SNDK) | 扭亏核验：减值消退还是经营改善 | [5 题](sets/sndk_scenario.json) | 1 → 2 → 2 → 4 → 3 |
| NetApp, Inc. (NTAP) | 资本回报预算：回购节奏与现金自给分开看 | [5 题](sets/ntap_scenario.json) | 2 → 3 → 1 → 3 → 1 |
| Pure Storage, Inc. (name and ticker in the pinned filing) (PSTG) | 订阅转型复盘：收入结构是否转化为毛利增长 | [5 题](sets/pstg_scenario.json) | 1 → 1 → 3 → 4 → 5 |
| Rambus Inc. (RMBS) | 收入质量复核：GAAP royalties 与 licensing billings | [5 题](sets/rmbs_scenario.json) | 1 → 3 → 3 → 2 → 3 |
| Everspin Technologies, Inc. (MRAM) | 收入修复路线：年度下滑、季度表现与指引边界 | [5 题](sets/mram_scenario.json) | 3 → 4 → 3 → 3 → 3 |

## MU — 财报会前核对：Q4 毛利加速与下一季指引

I am preparing a Micron earnings briefing. Reconstruct Q4 from the annual and nine-month filings, reconcile it to the earnings release, then test whether the next-quarter guidance meets my stated revenue and gross-margin hurdles.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 建立年度毛利基线 | 场景起点 | 3 |
| 002 | 年度减累计反推 Q4 | 001 | 3 |
| 003 | 与业绩附件对账 | 002 | 3 |
| 004 | 指引区间相对实际季度的增长 | 003 | 3 |
| 005 | 按用户双门槛形成简报结论 | 003, 004 | 4 |

## STX — 现金股息承受力：从已实现现金流到压力测试

I want a Seagate dividend-coverage workpaper. Establish annual cash generation, compare actual dividends, estimate the newly declared dividend run rate, and stress-test it without treating my assumptions as company guidance.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 取得现金流输入并计算 FCF | 场景起点 | 2 |
| 002 | 检验已支付股息覆盖 | 001 | 2 |
| 003 | 估算新股息的全年现金负担 | 002 | 3 |
| 004 | 现金流下降 15% 的覆盖压力 | 001, 003 | 3 |
| 005 | 求最大可承受回撤并核对压力结果 | 003, 004 | 3 |

## WDC — 分拆后的盈利口径与季度利润桥

I am reconciling Western Digital earnings after the Sandisk separation. Establish the correct continuing-operations boundary, bridge total and continuing profit, then check whether Q4 continuing net margin improved from Q3.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 先确定分拆后的口径 | 场景起点 | 1 |
| 002 | 按上一步口径取年度财务基线 | 001 | 1 |
| 003 | 年度总利润桥接到持续经营 | 002 | 2 |
| 004 | 把 Q3 与年度持续经营基线对齐 | 003 | 3 |
| 005 | 用 Q4 业绩附件完成季度趋势判断 | 004 | 4 |

## SNDK — 扭亏核验：减值消退还是经营改善

I am checking whether Sandisk's apparent Q4 recovery reflects underlying operating improvement or a disappearing goodwill charge, and whether the next-quarter release actually confirms a GAAP EPS turnaround.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 建立 Q3 亏损基线 | 场景起点 | 1 |
| 002 | 只加回商誉减值 | 001 | 2 |
| 003 | 将 Q4 与原始及调整后 Q3 对比 | 002 | 2 |
| 004 | 验证全年减值并量化利润桥 | 002, 003 | 4 |
| 005 | 缺失 GAAP 指引时不宣称确认扭亏 | 004 | 3 |

## NTAP — 资本回报预算：回购节奏与现金自给分开看

I am reviewing NetApp's capital-return budget. Determine whether dividends and buybacks were funded by simple FCF, set a no-external-funding buyback limit, then distinguish quarterly budget pacing from actual cash coverage.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 年度现金生成基线 | 场景起点 | 2 |
| 002 | 对账年度分红与回购 | 001 | 3 |
| 003 | 在现金自给规则下反推回购额度 | 002 | 1 |
| 004 | 将年度预算与首季实际现金流对照 | 003 | 3 |
| 005 | 形成双重约束下的资本回报结论 | 004 | 1 |

## PSTG — 订阅转型复盘：收入结构是否转化为毛利增长

I am preparing a Pure Storage subscription-transition review using its FY2025 filing. Trace revenue mix, category growth and category gross profit, then determine which business actually supplied the increase in total gross profit.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 从维度数据取得产品与订阅营收 | 场景起点 | 1 |
| 002 | 对账收入结构并计算订阅占比 | 001 | 1 |
| 003 | 把占比变化拆成两类收入增长 | 001, 002 | 3 |
| 004 | 检查增长更快的业务是否毛利更高 | 001, 003 | 4 |
| 005 | 完成毛利增长贡献桥 | 003, 004 | 5 |

## RMBS — 收入质量复核：GAAP royalties 与 licensing billings

I am reviewing Rambus's Q1 2025 growth and a proposed Q2 revenue estimate. Check the GAAP revenue bridge, test whether licensing billings are interchangeable with royalties, and decide if adding the outlook components produces valid GAAP revenue guidance.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 建立 GAAP 收入桥输入 | 场景起点 | 1 |
| 002 | 将总收入增长拆到组成项目 | 001 | 3 |
| 003 | 检验 billings 是否跟随 royalties | 002 | 3 |
| 004 | 用披露定义解释不可互换的指标 | 003 | 2 |
| 005 | 避免把指引组成项错误相加为 GAAP 收入 | 004 | 3 |

## MRAM — 收入修复路线：年度下滑、季度表现与指引边界

I am checking Everspin's revenue-recovery path. Establish the prior annual decline, compare Q1, translate Q2 guidance into a first-half scenario, and determine what second-half revenue would be needed to regain the prior annual level without claiming earnings are guaranteed.

| 步骤 | 题目 | 消费前题 | hops |
|---|---|---|---:|
| 001 | 建立上年收入与毛利基线 | 场景起点 | 3 |
| 002 | 检查 Q1 是否改善及利润率方向 | 001 | 4 |
| 003 | 将 Q2 收入指引映射为环比区间 | 002 | 3 |
| 004 | 反推回到上年收入所需的 H2 | 001, 002, 003 | 3 |
| 005 | 收入情景通过不等于保证 GAAP 盈利 | 003, 004 | 3 |

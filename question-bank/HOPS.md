# V2 hops 的统一计数与逐题拆解

本题库使用自定义协议 `conditional_evidence_depth_v2`：hops 是在前题结果可用条件下，本题规范证据与推导图的最长有向依赖路径长度。它不是难度等级、事实数量、HTTP 请求数，也不是最少工具调用次数。

这是本题库明确约定的计数方法，不声称为金融问答领域通行标准或数学上不可再压缩的最短解法。所有题目均按同一已保存的规范图计算。

## 计数单位

- 一次 `retrieve`：从一个具体 SEC 文档的同一张表或同一正文位置取得本题需要的新证据，权重 1。并列的多行、多列、比较期间可在同一读取节点中完成；不同表、不同位置分别建节点。
- 一次 `calculate`：产生一个明确的派生财务量，权重 1。百分比的乘 100、单位缩放属于该公式，不另外虚增 hops；后续再使用新算出的毛利、差额或区间中点时必须显式连接节点。
- 一次 `judge`：基于已取得事实或算出的量做明确比较/门槛判断，权重 1。
- `prior`：直接使用前题保留的输出，权重 0；不把前题已经完成的检索再计一遍。
- `assumption`：题面明确给定的用户假设，权重 0；不能伪装为公司披露。
- `alias`：原值改名或搬运，不产生新信息，权重 0。

节点深度 = 自身权重 + 所有父节点深度的最大值；无父节点视为 0。题目 hops = 所有要求输出所对应节点深度的最大值。并行读取取最大深度，不把数量相加。检索节点包含筛选正确日期、单位及上下文的工作，不另外按浏览器点击数计数。

例如：读年度和累计报表（并行深度 1）→ 相减得到 Q4（深度 2）→ 计算 Q4 毛利率（深度 3），就是 3 hops。若年度值来自前题，则它是深度 0 的 prior，但累计报表仍需读取，最长路径仍为 3。

## 如何检查

`grading/rubrics.json` 的每题都有 `input_bindings`、`hop_plan`、`output_nodes` 和 `depends_on`。验证器重新计算节点深度，并检查前题引用、输出覆盖、运算顺序和公式输入关系，不能仅靠人工填写一个整数通过。

规范图采用有名中间量来解释依赖；把多步运算合并成一行代码不会改变保存的基准 hops。Agent 实际工具调用和实际耗时需要另外记录。

## 40 题逐项拆解

### RAIN-V2-MU-001 — 建立年度毛利基线

`hops = 3`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve MU-10-K:income_statement | — | rev25, gp25, rev24, gp24 | 1 |
| derive_gm25 | calculate `gp25 / rev25 * 100` | read_1 | gm25 | 2 |
| derive_gm24 | calculate `gp24 / rev24 * 100` | read_1 | gm24 | 2 |
| derive_gm_change | calculate `gm25 - gm24` | derive_gm24, derive_gm25 | gm_change | 3 |

### RAIN-V2-MU-002 — 年度减累计反推 Q4

`hops = 3`；前题：RAIN-V2-MU-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_annual_rev | prior RAIN-V2-MU-001.rev25 | — | annual_rev | 0 |
| input_annual_gp | prior RAIN-V2-MU-001.gp25 | — | annual_gp | 0 |
| read_1 | retrieve MU-10-Q:income_statement | — | ytd_rev, ytd_gp | 1 |
| derive_q4_rev | calculate `annual_rev - ytd_rev` | input_annual_rev, read_1 | q4_rev | 2 |
| derive_q4_gp | calculate `annual_gp - ytd_gp` | input_annual_gp, read_1 | q4_gp | 2 |
| derive_q4_gm | calculate `q4_gp / q4_rev * 100` | derive_q4_gp, derive_q4_rev | q4_gm | 3 |

### RAIN-V2-MU-003 — 与业绩附件对账

`hops = 3`；前题：RAIN-V2-MU-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_derived_rev | prior RAIN-V2-MU-002.q4_rev | — | derived_rev | 0 |
| input_derived_gp | prior RAIN-V2-MU-002.q4_gp | — | derived_gp | 0 |
| read_1 | retrieve MU-8-K-ex0:Quarterly Financial Results | — | actual_rev, actual_gp | 1 |
| derive_revenue_difference | calculate `actual_rev - derived_rev` | read_1, input_derived_rev | revenue_difference | 2 |
| derive_gross_profit_difference | calculate `actual_gp - derived_gp` | read_1, input_derived_gp | gross_profit_difference | 2 |
| derive_actual_gm | calculate `actual_gp / actual_rev * 100` | read_1 | actual_gm | 2 |
| derive_reconciles | judge `revenue_difference == 0 and gross_profit_difference == 0` | derive_gross_profit_difference, derive_revenue_difference | reconciles | 3 |

### RAIN-V2-MU-004 — 指引区间相对实际季度的增长

`hops = 3`；前题：RAIN-V2-MU-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q4_rev | prior RAIN-V2-MU-003.actual_rev | — | q4_rev | 0 |
| read_1 | retrieve MU-8-K-ex0:Business Outlook | — | midpoint | 1 |
| read_2 | retrieve MU-8-K-ex0:Same guidance row | — | half_range | 1 |
| derive_low | calculate `midpoint - half_range` | read_2, read_1 | low | 2 |
| derive_high | calculate `midpoint + half_range` | read_2, read_1 | high | 2 |
| derive_low_growth | calculate `(low / q4_rev - 1) * 100` | derive_low, input_q4_rev | low_growth | 3 |
| derive_high_growth | calculate `(high / q4_rev - 1) * 100` | derive_high, input_q4_rev | high_growth | 3 |

### RAIN-V2-MU-005 — 按用户双门槛形成简报结论

`hops = 4`；前题：RAIN-V2-MU-003, RAIN-V2-MU-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_low_growth | prior RAIN-V2-MU-004.low_growth | — | low_growth | 0 |
| input_q4_margin | prior RAIN-V2-MU-003.actual_gm | — | q4_margin | 0 |
| read_1 | retrieve MU-8-K-ex0:Business Outlook | — | gm_mid, gm_half | 1 |
| input_growth_hurdle | assumption | — | growth_hurdle | 0 |
| input_gm_hurdle | assumption | — | gm_hurdle | 0 |
| derive_gm_low | calculate `gm_mid - gm_half` | read_1 | gm_low | 2 |
| derive_uplift | calculate `gm_low - q4_margin` | derive_gm_low, input_q4_margin | uplift | 3 |
| derive_both_pass | judge `low_growth >= growth_hurdle and uplift >= gm_hurdle` | input_gm_hurdle, input_growth_hurdle, input_low_growth, derive_uplift | both_pass | 4 |

### RAIN-V2-STX-001 — 取得现金流输入并计算 FCF

`hops = 2`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve STX-10-K:income_statement | — | ocf, capex | 1 |
| derive_fcf | calculate `ocf - capex` | read_1 | fcf | 2 |

### RAIN-V2-STX-002 — 检验已支付股息覆盖

`hops = 2`；前题：RAIN-V2-STX-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_fcf | prior RAIN-V2-STX-001.fcf | — | fcf | 0 |
| read_1 | retrieve STX-10-K:cash_flow_statement | — | dividends | 1 |
| derive_coverage | calculate `fcf / dividends` | read_1, input_fcf | coverage | 2 |
| derive_residual | calculate `fcf - dividends` | read_1, input_fcf | residual | 2 |

### RAIN-V2-STX-003 — 估算新股息的全年现金负担

`hops = 3`；前题：RAIN-V2-STX-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_old_dividends | prior RAIN-V2-STX-002.dividends | — | old_dividends | 0 |
| read_1 | retrieve STX-8-K:Item 7.01 | — | rate | 1 |
| read_2 | retrieve STX-8-K-ex0:Cash flow and capital allocation discussion | — | shares | 1 |
| input_quarters | assumption | — | quarters | 0 |
| derive_annual_dividend_budget | calculate `rate * shares * quarters` | input_quarters, read_1, read_2 | annual_dividend_budget | 2 |
| derive_increase | calculate `annual_dividend_budget - old_dividends` | derive_annual_dividend_budget, input_old_dividends | increase | 3 |

### RAIN-V2-STX-004 — 现金流下降 15% 的覆盖压力

`hops = 3`；前题：RAIN-V2-STX-001, RAIN-V2-STX-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_dividend_budget | prior RAIN-V2-STX-003.annual_dividend_budget | — | dividend_budget | 0 |
| input_fcf | prior RAIN-V2-STX-001.fcf | — | fcf | 0 |
| input_decline | assumption | — | decline | 0 |
| input_minimum_coverage | assumption | — | minimum_coverage | 0 |
| derive_stressed_fcf | calculate `fcf * (1 - decline)` | input_decline, input_fcf | stressed_fcf | 1 |
| derive_stressed_coverage | calculate `stressed_fcf / dividend_budget` | input_dividend_budget, derive_stressed_fcf | stressed_coverage | 2 |
| derive_residual | calculate `stressed_fcf - dividend_budget` | input_dividend_budget, derive_stressed_fcf | residual | 2 |
| derive_passes | judge `stressed_coverage >= minimum_coverage` | input_minimum_coverage, derive_stressed_coverage | passes | 3 |

### RAIN-V2-STX-005 — 求最大可承受回撤并核对压力结果

`hops = 3`；前题：RAIN-V2-STX-003, RAIN-V2-STX-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_stressed_fcf | prior RAIN-V2-STX-004.stressed_fcf | — | stressed_fcf | 0 |
| input_dividend_budget | prior RAIN-V2-STX-003.annual_dividend_budget | — | dividend_budget | 0 |
| input_tested_decline | assumption | — | tested_decline | 0 |
| input_minimum_coverage | assumption | — | minimum_coverage | 0 |
| derive_baseline | calculate `stressed_fcf / (1 - tested_decline)` | input_stressed_fcf, input_tested_decline | baseline | 1 |
| derive_required_fcf | calculate `dividend_budget * minimum_coverage` | input_dividend_budget, input_minimum_coverage | required_fcf | 1 |
| derive_max_decline_pct | calculate `(1 - required_fcf / baseline) * 100` | derive_baseline, derive_required_fcf | max_decline_pct | 2 |
| derive_tested_decline_exceeds_limit | judge `tested_decline * 100 > max_decline_pct` | derive_max_decline_pct, input_tested_decline | tested_decline_exceeds_limit | 3 |

### RAIN-V2-WDC-001 — 先确定分拆后的口径

`hops = 1`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve WDC-10-Q:Note 3 | — | separation_date | 1 |
| read_2 | retrieve WDC-10-Q:Note 3 and segment discussion | — | presentation | 1 |
| read_3 | retrieve WDC-10-Q:Note 1 / segment reporting discussion | — | remaining_segment | 1 |

### RAIN-V2-WDC-002 — 按上一步口径取年度财务基线

`hops = 1`；前题：RAIN-V2-WDC-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_segment | prior RAIN-V2-WDC-001.remaining_segment | — | segment | 0 |
| input_presentation | prior RAIN-V2-WDC-001.presentation | — | presentation | 0 |
| read_1 | retrieve WDC-10-K:income_statement | — | revenue, continuing_income, total_net_income | 1 |
| derive_scope_confirmed | judge `segment == 'HDD' and presentation == 'discontinued operations'` | input_presentation, input_segment | scope_confirmed | 1 |

### RAIN-V2-WDC-003 — 年度总利润桥接到持续经营

`hops = 2`；前题：RAIN-V2-WDC-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_revenue | prior RAIN-V2-WDC-002.revenue | — | revenue | 0 |
| input_continuing_income | prior RAIN-V2-WDC-002.continuing_income | — | continuing_income | 0 |
| input_total_net_income | prior RAIN-V2-WDC-002.total_net_income | — | total_net_income | 0 |
| derive_discontinued_income | calculate `total_net_income - continuing_income` | input_continuing_income, input_total_net_income | discontinued_income | 1 |
| derive_discontinued_share_pct | calculate `discontinued_income / total_net_income * 100` | derive_discontinued_income, input_total_net_income | discontinued_share_pct | 2 |
| derive_annual_continuing_margin | calculate `continuing_income / revenue * 100` | input_continuing_income, input_revenue | annual_continuing_margin | 1 |

### RAIN-V2-WDC-004 — 把 Q3 与年度持续经营基线对齐

`hops = 3`；前题：RAIN-V2-WDC-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_annual_margin | prior RAIN-V2-WDC-003.annual_continuing_margin | — | annual_margin | 0 |
| read_1 | retrieve WDC-10-Q:income_statement | — | q3_revenue, q3_continuing_income | 1 |
| derive_q3_margin | calculate `q3_continuing_income / q3_revenue * 100` | read_1 | q3_margin | 2 |
| derive_vs_annual_pp | calculate `q3_margin - annual_margin` | input_annual_margin, derive_q3_margin | vs_annual_pp | 3 |

### RAIN-V2-WDC-005 — 用 Q4 业绩附件完成季度趋势判断

`hops = 4`；前题：RAIN-V2-WDC-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q3_margin | prior RAIN-V2-WDC-004.q3_margin | — | q3_margin | 0 |
| read_1 | retrieve WDC-8-K-ex0:Q4FY25 Financial Highlights | — | q4_revenue | 1 |
| read_2 | retrieve WDC-8-K-ex0:Condensed Consolidated Statements of Operations | — | q4_income | 1 |
| derive_q4_margin | calculate `q4_income / q4_revenue * 100` | read_2, read_1 | q4_margin | 2 |
| derive_change_pp | calculate `q4_margin - q3_margin` | input_q3_margin, derive_q4_margin | change_pp | 3 |
| derive_improved | judge `change_pp > 0` | derive_change_pp | improved | 4 |

### RAIN-V2-SNDK-001 — 建立 Q3 亏损基线

`hops = 1`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve SNDK-10-Q:income_statement | — | operating_income, net_income | 1 |

### RAIN-V2-SNDK-002 — 只加回商誉减值

`hops = 2`；前题：RAIN-V2-SNDK-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q3_operating | prior RAIN-V2-SNDK-001.operating_income | — | q3_operating | 0 |
| read_1 | retrieve SNDK-10-Q:income_statement | — | q3_impairment | 1 |
| derive_q3_excluding_only_goodwill | calculate `q3_operating + q3_impairment` | read_1, input_q3_operating | q3_excluding_only_goodwill | 2 |

### RAIN-V2-SNDK-003 — 将 Q4 与原始及调整后 Q3 对比

`hops = 2`；前题：RAIN-V2-SNDK-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q3_reported | prior RAIN-V2-SNDK-002.q3_operating | — | q3_reported | 0 |
| input_q3_adjusted | prior RAIN-V2-SNDK-002.q3_excluding_only_goodwill | — | q3_adjusted | 0 |
| read_1 | retrieve SNDK-8-K-ex0:Q4 2025 Financial Highlights | — | q4_operating | 1 |
| derive_reported_improvement | calculate `q4_operating - q3_reported` | input_q3_reported, read_1 | reported_improvement | 2 |
| derive_vs_q3_single_charge_adjusted | calculate `q4_operating - q3_adjusted` | input_q3_adjusted, read_1 | vs_q3_single_charge_adjusted | 2 |

### RAIN-V2-SNDK-004 — 验证全年减值并量化利润桥

`hops = 4`；前题：RAIN-V2-SNDK-002, RAIN-V2-SNDK-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_reported_improvement | prior RAIN-V2-SNDK-003.reported_improvement | — | reported_improvement | 0 |
| input_q3_impairment | prior RAIN-V2-SNDK-002.q3_impairment | — | q3_impairment | 0 |
| read_1 | retrieve SNDK-10-K:income_statement | — | annual_impairment | 1 |
| read_2 | retrieve SNDK-10-Q:income_statement | — | ytd_impairment | 1 |
| derive_q4_impairment | calculate `annual_impairment - ytd_impairment` | read_1, read_2 | q4_impairment | 2 |
| derive_charge_reduction | calculate `q3_impairment - q4_impairment` | input_q3_impairment, derive_q4_impairment | charge_reduction | 3 |
| derive_charge_reduction_share | calculate `charge_reduction / reported_improvement * 100` | derive_charge_reduction, input_reported_improvement | charge_reduction_share | 4 |

### RAIN-V2-SNDK-005 — 缺失 GAAP 指引时不宣称确认扭亏

`hops = 3`；前题：RAIN-V2-SNDK-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_share | prior RAIN-V2-SNDK-004.charge_reduction_share | — | share | 0 |
| input_threshold | assumption | — | threshold | 0 |
| read_1 | retrieve SNDK-8-K-ex0:Business Outlook | — | gaap_guidance | 1 |
| read_2 | retrieve SNDK-8-K-ex0:Same table | — | non_gaap_low, non_gaap_high | 1 |
| derive_adjustment_condition | judge `share > threshold` | input_share, input_threshold | adjustment_condition | 1 |
| derive_numeric_gaap_available | judge `gaap_guidance != None and gaap_guidance > 0` | read_1 | numeric_gaap_available | 2 |
| derive_required_confirmation_available | judge `adjustment_condition and numeric_gaap_available` | derive_adjustment_condition, derive_numeric_gaap_available | required_confirmation_available | 3 |

### RAIN-V2-NTAP-001 — 年度现金生成基线

`hops = 2`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve NTAP-10-K:cash_flow_statement | — | ocf, capex | 1 |
| derive_fcf | calculate `ocf - capex` | read_1 | fcf | 2 |

### RAIN-V2-NTAP-002 — 对账年度分红与回购

`hops = 3`；前题：RAIN-V2-NTAP-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_fcf | prior RAIN-V2-NTAP-001.fcf | — | fcf | 0 |
| read_1 | retrieve NTAP-10-K:cash_flow_statement | — | dividends, buybacks | 1 |
| derive_cash_returns | calculate `dividends + buybacks` | read_1 | cash_returns | 2 |
| derive_funding_gap | calculate `cash_returns - fcf` | derive_cash_returns, input_fcf | funding_gap | 3 |

### RAIN-V2-NTAP-003 — 在现金自给规则下反推回购额度

`hops = 1`；前题：RAIN-V2-NTAP-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_actual_buybacks | prior RAIN-V2-NTAP-002.buybacks | — | actual_buybacks | 0 |
| input_required_cut | prior RAIN-V2-NTAP-002.funding_gap | — | required_cut | 0 |
| derive_max_buybacks | calculate `actual_buybacks - required_cut` | input_actual_buybacks, input_required_cut | max_buybacks | 1 |
| derive_cut_pct | calculate `required_cut / actual_buybacks * 100` | input_actual_buybacks, input_required_cut | cut_pct | 1 |

### RAIN-V2-NTAP-004 — 将年度预算与首季实际现金流对照

`hops = 3`；前题：RAIN-V2-NTAP-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_annual_budget | prior RAIN-V2-NTAP-003.max_buybacks | — | annual_budget | 0 |
| read_1 | retrieve NTAP-10-Q:cash_flow_statement | — | ocf, capex, dividends, buybacks | 1 |
| input_quarters | assumption | — | quarters | 0 |
| derive_quarter_fcf | calculate `ocf - capex` | read_1 | quarter_fcf | 2 |
| derive_cash_surplus | calculate `quarter_fcf - dividends - buybacks` | read_1, derive_quarter_fcf | cash_surplus | 3 |
| derive_pacing_excess | calculate `buybacks - annual_budget / quarters` | input_annual_budget, read_1, input_quarters | pacing_excess | 2 |

### RAIN-V2-NTAP-005 — 形成双重约束下的资本回报结论

`hops = 1`；前题：RAIN-V2-NTAP-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_surplus | prior RAIN-V2-NTAP-004.cash_surplus | — | surplus | 0 |
| input_pacing_excess | prior RAIN-V2-NTAP-004.pacing_excess | — | pacing_excess | 0 |
| derive_over_pacing_benchmark | judge `pacing_excess > 0` | input_pacing_excess | over_pacing_benchmark | 1 |
| derive_cash_funding_shortfall | judge `surplus < 0` | input_surplus | cash_funding_shortfall | 1 |
| derive_cash_only_headroom | alias `surplus` | input_surplus | cash_only_headroom | 0 |

### RAIN-V2-PSTG-001 — 从维度数据取得产品与订阅营收

`hops = 1`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve PSTG-10-K:income_statement | — | product, subscription, total | 1 |

### RAIN-V2-PSTG-002 — 对账收入结构并计算订阅占比

`hops = 1`；前题：RAIN-V2-PSTG-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_product | prior RAIN-V2-PSTG-001.product | — | product | 0 |
| input_subscription | prior RAIN-V2-PSTG-001.subscription | — | subscription | 0 |
| input_total | prior RAIN-V2-PSTG-001.total | — | total | 0 |
| derive_subscription_share | calculate `subscription / total * 100` | input_subscription, input_total | subscription_share | 1 |
| derive_reconciliation_difference | calculate `product + subscription - total` | input_product, input_subscription, input_total | reconciliation_difference | 1 |

### RAIN-V2-PSTG-003 — 把占比变化拆成两类收入增长

`hops = 3`；前题：RAIN-V2-PSTG-001, RAIN-V2-PSTG-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_current_share | prior RAIN-V2-PSTG-002.subscription_share | — | current_share | 0 |
| input_product | prior RAIN-V2-PSTG-001.product | — | product | 0 |
| input_subscription | prior RAIN-V2-PSTG-001.subscription | — | subscription | 0 |
| read_1 | retrieve PSTG-10-K:income_statement | — | prior_product, prior_subscription, prior_total | 1 |
| derive_product_growth | calculate `(product / prior_product - 1) * 100` | read_1, input_product | product_growth | 2 |
| derive_subscription_growth | calculate `(subscription / prior_subscription - 1) * 100` | read_1, input_subscription | subscription_growth | 2 |
| derive_prior_share | calculate `prior_subscription / prior_total * 100` | read_1 | prior_share | 2 |
| derive_mix_change | calculate `current_share - prior_share` | input_current_share, derive_prior_share | mix_change | 3 |
| derive_subscription_faster | judge `subscription_growth > product_growth` | derive_product_growth, derive_subscription_growth | subscription_faster | 3 |

### RAIN-V2-PSTG-004 — 检查增长更快的业务是否毛利更高

`hops = 4`；前题：RAIN-V2-PSTG-001, RAIN-V2-PSTG-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_subscription_faster | prior RAIN-V2-PSTG-003.subscription_faster | — | subscription_faster | 0 |
| input_product | prior RAIN-V2-PSTG-001.product | — | product | 0 |
| input_subscription | prior RAIN-V2-PSTG-001.subscription | — | subscription | 0 |
| read_1 | retrieve PSTG-10-K:income_statement | — | product_cost, subscription_cost | 1 |
| derive_product_gp | calculate `product - product_cost` | input_product, read_1 | product_gp | 2 |
| derive_subscription_gp | calculate `subscription - subscription_cost` | input_subscription, read_1 | subscription_gp | 2 |
| derive_product_margin | calculate `product_gp / product * 100` | input_product, derive_product_gp | product_margin | 3 |
| derive_subscription_margin | calculate `subscription_gp / subscription * 100` | input_subscription, derive_subscription_gp | subscription_margin | 3 |
| derive_faster_and_higher_margin | judge `subscription_faster and subscription_margin > product_margin` | derive_product_margin, input_subscription_faster, derive_subscription_margin | faster_and_higher_margin | 4 |

### RAIN-V2-PSTG-005 — 完成毛利增长贡献桥

`hops = 5`；前题：RAIN-V2-PSTG-003, RAIN-V2-PSTG-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_current_product_gp | prior RAIN-V2-PSTG-004.product_gp | — | current_product_gp | 0 |
| input_current_subscription_gp | prior RAIN-V2-PSTG-004.subscription_gp | — | current_subscription_gp | 0 |
| input_prior_product | prior RAIN-V2-PSTG-003.prior_product | — | prior_product | 0 |
| input_prior_subscription | prior RAIN-V2-PSTG-003.prior_subscription | — | prior_subscription | 0 |
| read_1 | retrieve PSTG-10-K:income_statement | — | prior_product_cost, prior_subscription_cost | 1 |
| derive_prior_product_gp | calculate `prior_product - prior_product_cost` | input_prior_product, read_1 | prior_product_gp | 2 |
| derive_prior_subscription_gp | calculate `prior_subscription - prior_subscription_cost` | input_prior_subscription, read_1 | prior_subscription_gp | 2 |
| derive_product_gp_change | calculate `current_product_gp - prior_product_gp` | input_current_product_gp, derive_prior_product_gp | product_gp_change | 3 |
| derive_subscription_gp_change | calculate `current_subscription_gp - prior_subscription_gp` | input_current_subscription_gp, derive_prior_subscription_gp | subscription_gp_change | 3 |
| derive_total_gp_change | calculate `product_gp_change + subscription_gp_change` | derive_product_gp_change, derive_subscription_gp_change | total_gp_change | 4 |
| derive_subscription_contribution | calculate `subscription_gp_change / total_gp_change * 100` | derive_subscription_gp_change, derive_total_gp_change | subscription_contribution | 5 |
| derive_offset_product_decline | judge `product_gp_change < 0 and total_gp_change > 0` | derive_product_gp_change, derive_total_gp_change | offset_product_decline | 5 |

### RAIN-V2-RMBS-001 — 建立 GAAP 收入桥输入

`hops = 1`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve RMBS-10-Q:income_statement | — | product25, royalties25, contract25, total25, product24, royalties24, contract24, total24 | 1 |

### RAIN-V2-RMBS-002 — 将总收入增长拆到组成项目

`hops = 3`；前题：RAIN-V2-RMBS-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_product25 | prior RAIN-V2-RMBS-001.product25 | — | product25 | 0 |
| input_royalties25 | prior RAIN-V2-RMBS-001.royalties25 | — | royalties25 | 0 |
| input_contract25 | prior RAIN-V2-RMBS-001.contract25 | — | contract25 | 0 |
| input_total25 | prior RAIN-V2-RMBS-001.total25 | — | total25 | 0 |
| input_product24 | prior RAIN-V2-RMBS-001.product24 | — | product24 | 0 |
| input_royalties24 | prior RAIN-V2-RMBS-001.royalties24 | — | royalties24 | 0 |
| input_contract24 | prior RAIN-V2-RMBS-001.contract24 | — | contract24 | 0 |
| input_total24 | prior RAIN-V2-RMBS-001.total24 | — | total24 | 0 |
| derive_product_change | calculate `product25 - product24` | input_product24, input_product25 | product_change | 1 |
| derive_royalty_change | calculate `royalties25 - royalties24` | input_royalties24, input_royalties25 | royalty_change | 1 |
| derive_contract_change | calculate `contract25 - contract24` | input_contract24, input_contract25 | contract_change | 1 |
| derive_total_change | calculate `total25 - total24` | input_total24, input_total25 | total_change | 1 |
| derive_component_change | calculate `product_change + royalty_change + contract_change` | derive_contract_change, derive_product_change, derive_royalty_change | component_change | 2 |
| derive_bridge_difference | calculate `component_change - total_change` | derive_component_change, derive_total_change | bridge_difference | 3 |
| derive_total_growth | calculate `(total25 / total24 - 1) * 100` | input_total24, input_total25 | total_growth | 1 |
| derive_royalty_growth | calculate `(royalties25 / royalties24 - 1) * 100` | input_royalties24, input_royalties25 | royalty_growth | 1 |

### RAIN-V2-RMBS-003 — 检验 billings 是否跟随 royalties

`hops = 3`；前题：RAIN-V2-RMBS-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_royalty_growth | prior RAIN-V2-RMBS-002.royalty_growth | — | royalty_growth | 0 |
| read_1 | retrieve RMBS-8-K-ex0:Quarterly Financial Review - Supplemental Information | — | billings25, billings24 | 1 |
| derive_billings_growth | calculate `(billings25 / billings24 - 1) * 100` | read_1 | billings_growth | 2 |
| derive_growth_gap | calculate `royalty_growth - billings_growth` | derive_billings_growth, input_royalty_growth | growth_gap | 3 |

### RAIN-V2-RMBS-004 — 用披露定义解释不可互换的指标

`hops = 2`；前题：RAIN-V2-RMBS-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_growth_gap | prior RAIN-V2-RMBS-003.growth_gap | — | growth_gap | 0 |
| read_1 | retrieve RMBS-8-K-ex0:Supplemental Information | — | metric_basis | 1 |
| derive_different_growth | judge `growth_gap != 0` | input_growth_gap | different_growth | 1 |
| derive_substitution_supported | judge `metric_basis == 'GAAP revenue metric' and growth_gap == 0` | input_growth_gap, read_1 | substitution_supported | 2 |

### RAIN-V2-RMBS-005 — 避免把指引组成项错误相加为 GAAP 收入

`hops = 3`；前题：RAIN-V2-RMBS-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_substitution_supported | prior RAIN-V2-RMBS-004.substitution_supported | — | substitution_supported | 0 |
| read_1 | retrieve RMBS-8-K-ex0:2025 Second Quarter Outlook | — | billing_low, billing_high, product_low, product_high, contract_low, contract_high, gaap_total_guidance | 1 |
| derive_billing_mid | calculate `(billing_low + billing_high) / 2` | read_1 | billing_mid | 2 |
| derive_product_mid | calculate `(product_low + product_high) / 2` | read_1 | product_mid | 2 |
| derive_contract_mid | calculate `(contract_low + contract_high) / 2` | read_1 | contract_mid | 2 |
| derive_component_sum | calculate `billing_mid + product_mid + contract_mid` | derive_billing_mid, derive_contract_mid, derive_product_mid | component_sum | 3 |
| derive_valid_gaap_total | judge `substitution_supported and gaap_total_guidance != None` | read_1, input_substitution_supported | valid_gaap_total | 2 |

### RAIN-V2-MRAM-001 — 建立上年收入与毛利基线

`hops = 3`；前题：无。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| read_1 | retrieve MRAM-10-K:income_statement | — | revenue24, revenue23, cogs24 | 1 |
| derive_annual_growth | calculate `(revenue24 / revenue23 - 1) * 100` | read_1 | annual_growth | 2 |
| derive_annual_gp | calculate `revenue24 - cogs24` | read_1 | annual_gp | 2 |
| derive_annual_gm | calculate `annual_gp / revenue24 * 100` | derive_annual_gp, read_1 | annual_gm | 3 |

### RAIN-V2-MRAM-002 — 检查 Q1 是否改善及利润率方向

`hops = 4`；前题：RAIN-V2-MRAM-001。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_annual_growth | prior RAIN-V2-MRAM-001.annual_growth | — | annual_growth | 0 |
| input_annual_gm | prior RAIN-V2-MRAM-001.annual_gm | — | annual_gm | 0 |
| read_1 | retrieve MRAM-10-Q:income_statement | — | q1_revenue, prior_q1_revenue, q1_cogs | 1 |
| derive_q1_growth | calculate `(q1_revenue / prior_q1_revenue - 1) * 100` | read_1 | q1_growth | 2 |
| derive_q1_gp | calculate `q1_revenue - q1_cogs` | read_1 | q1_gp | 2 |
| derive_q1_gm | calculate `q1_gp / q1_revenue * 100` | derive_q1_gp, read_1 | q1_gm | 3 |
| derive_growth_rate_improved | judge `q1_growth > annual_growth` | input_annual_growth, derive_q1_growth | growth_rate_improved | 3 |
| derive_margin_change | calculate `q1_gm - annual_gm` | input_annual_gm, derive_q1_gm | margin_change | 4 |

### RAIN-V2-MRAM-003 — 将 Q2 收入指引映射为环比区间

`hops = 3`；前题：RAIN-V2-MRAM-002。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q1_revenue | prior RAIN-V2-MRAM-002.q1_revenue | — | q1_revenue | 0 |
| read_1 | retrieve MRAM-8-K-ex0:Business Outlook | — | q2_low, q2_high | 1 |
| derive_q2_mid | calculate `(q2_low + q2_high) / 2` | read_1 | q2_mid | 2 |
| derive_growth_low | calculate `(q2_low / q1_revenue - 1) * 100` | input_q1_revenue, read_1 | growth_low | 2 |
| derive_growth_mid | calculate `(q2_mid / q1_revenue - 1) * 100` | input_q1_revenue, derive_q2_mid | growth_mid | 3 |
| derive_growth_high | calculate `(q2_high / q1_revenue - 1) * 100` | input_q1_revenue, read_1 | growth_high | 2 |

### RAIN-V2-MRAM-004 — 反推回到上年收入所需的 H2

`hops = 3`；前题：RAIN-V2-MRAM-001, RAIN-V2-MRAM-002, RAIN-V2-MRAM-003。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_q2_mid | prior RAIN-V2-MRAM-003.q2_mid | — | q2_mid | 0 |
| input_q1_revenue | prior RAIN-V2-MRAM-002.q1_revenue | — | q1_revenue | 0 |
| input_target | prior RAIN-V2-MRAM-001.revenue24 | — | target | 0 |
| input_h2_quarters | assumption | — | h2_quarters | 0 |
| derive_h1_scenario | calculate `q1_revenue + q2_mid` | input_q1_revenue, input_q2_mid | h1_scenario | 1 |
| derive_required_h2 | calculate `target - h1_scenario` | derive_h1_scenario, input_target | required_h2 | 2 |
| derive_required_quarter_average | calculate `required_h2 / h2_quarters` | input_h2_quarters, derive_required_h2 | required_quarter_average | 3 |

### RAIN-V2-MRAM-005 — 收入情景通过不等于保证 GAAP 盈利

`hops = 3`；前题：RAIN-V2-MRAM-003, RAIN-V2-MRAM-004。

| 节点 | 操作 | 父节点 | 产出 | 深度 |
|---|---|---|---|---:|
| input_required_h2 | prior RAIN-V2-MRAM-004.required_h2 | — | required_h2 | 0 |
| input_q2_low | prior RAIN-V2-MRAM-003.q2_low | — | q2_low | 0 |
| input_h2_quarters | assumption | — | h2_quarters | 0 |
| read_1 | retrieve MRAM-8-K-ex0:Business Outlook | — | gaap_eps_low, gaap_eps_high | 1 |
| derive_h2_scenario | calculate `q2_low * h2_quarters` | input_h2_quarters, input_q2_low | h2_scenario | 1 |
| derive_revenue_surplus | calculate `h2_scenario - required_h2` | derive_h2_scenario, input_required_h2 | revenue_surplus | 2 |
| derive_revenue_target_met | judge `revenue_surplus >= 0` | derive_revenue_surplus | revenue_target_met | 3 |
| derive_gaap_range_strictly_positive | judge `gaap_eps_low > 0 and gaap_eps_high > 0` | read_1 | gaap_range_strictly_positive | 2 |

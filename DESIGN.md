<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->

---
name: 日报 · Daily Report
description: 一份温暖的每日金融与科技资讯晨报
---

# Design System: 日报 · Daily Report

## 1. Overview

**Creative North Star: "The Morning Briefing"**

一份精心编排的晨间简报 — 像在温暖的灯光下翻开一份懂你的报纸。信息密集但不压迫，数据权威但不冷漠，排版讲究但不做作。这是金融信息与人文温度的交汇点：Bloomberg 的数据权威，WSJ 的版面节奏，FT 的编辑克制，但走出自己的路 — 温暖、愉悦、亲近。

这个系统明确拒绝「冷淡数据墙」：冷硬的表格堆砌、灰蓝工业仪表板、无视觉节奏的数据罗列。数字背后是故事，版面背后是关怀，色彩背后是温度。

**Key Characteristics:**
- Editorial rhythm — 信息板块有主有次，像报纸版面而非均匀网格
- Warm authority — 金融数据可以温暖；色彩和排版传递关怀，而非冷漠
- Full palette voice — 涨跌、趋势、分类各有专属色彩角色，不靠灰蓝说事
- Serif elegance — 标题层用衬线字体传递编辑感和权威感
- Responsive motion — 平滑过渡和滚动反馈，像翻页而非跳转

## 2. Colors

**The Full Palette Rule.** 这是一个信息密集的品牌页，需要 3-4 个命名的色彩角色各司其职：品牌色、辅助色、涨色、跌色。每个角色都有明确的使用场景，不是装饰，是信息。

品牌种子锚定在暖珊瑚 / 编排橙色调（oklch hue ≈ 39°），由其延展出整个色盘。

### Primary
- **Editorial Ochre** `[to be resolved during implementation]`: 品牌 primary，锚定 hue ≈ 39° 的深沉暖色。用于页头标识、板块分隔线、关键数据高亮、CTA 元素。是版面的「签名笔」 — 不大面积铺满，但在关键位置标记身份。源自种子 oklch(0.673 0.217 38.6)，向深沉方向调整以获得编辑权威感。

### Accent
- **Deep Data Blue** `[to be resolved during implementation]`: 辅助品牌色，hue 远离 primary（≈ 240-260°），更深的明度。用于链接、状态标签、次要强调元素、辅助图表色。与 primary 在 hue 和 lightness 上都明显不同（contrast ≥ 1.7），确保视觉区分。

### Rise / Fall
- **涨色 (Rise)** `[to be resolved during implementation]`: 中文金融惯例 — 红色系表达上涨。不是刺眼的纯红，而是 warm confident tone，向 primary 的暖色调靠拢但 hue 更偏红（≈ 20-30°）。用于涨幅数字、上涨箭头、正向指标。
- **跌色 (Fall)** `[to be resolved during implementation]`: 中文金融惯例 — 绿色系表达下跌。不是荧光绿，而是 calm grounded teal（hue ≈ 160-180°），沉稳可信。用于跌幅数字、下跌箭头、负向指标。色弱安全：涨跌不只靠色，辅以 ▲▼ 箭头和 +/− 符号。

### Neutral
- **Pure White** `[bg]`: oklch(1.000 0.000 0) — 纯白背景，不添加隐含暖色。温度来自品牌色和排版，不来自背景染色。参考 Stripe / Notion / Apple 的白。
- **Warm Surface** `[surface]`: `[to be resolved]` — bg 向 ink 方向微拉（10-15% mix），hue 微偏品牌暖色（chroma ≈ 0.005-0.015），用于卡片面板、板块容器。
- **Warm Ink** `[ink / body text]`: `[to be resolved]` — 深近黑色，hue 微偏品牌暖色（chroma ≈ 0.02），≥7:1 contrast vs bg。承载品牌温度而不牺牲可读性。
- **Warm Muted** `[secondary text]`: `[to be resolved]` — ink 向 bg 拉 40%，保持 ink 的 hue，≥3.5:1 contrast vs bg。用于辅助说明、日期、次要数据标签。

**The No-Cream Rule.** 背景 oklch L 0.84-0.97 / C < 0.06 / hue 40-100 是 2026 的 AI 奶油色默认。本项目的温度来自品牌色（Editorial Ochre）和排版（Serif display），不来自背景染色。bg 是纯白；surface 只带 0.005-0.015 chroma 微偏品牌暖色，不是奶油色。

## 3. Typography

**Display Font:** Serif `[font pairing to be chosen at implementation]`
**Body Font:** Sans-serif `[font pairing to be chosen at implementation]`

**Character:** 衬线标题传递编辑权威感和阅读仪式感 — 像翻开一份讲究的报纸。无衬线正文保证数据可读性和信息密度 — 干净、温暖、不冷漠。两族在性格上互补（editorial authority + humanist warmth），不在风格上撞车。

方向：Serif display + sans body。衬线用于页头标题、板块标题、数据标题层级；无衬线用于正文数据、标签、导航、辅助说明。中文字体需 CJK 全覆盖，英文 display 字体需避开 reflex-reject 列表（Fraunces, Newsreader, Cormorant, Playfair 等）。

### Hierarchy
- **Display** (serif, weight 400-700, clamp ≈ 2.5rem–4.5rem, line-height ≈ 1): 页头主标题，一天的核心叙事。
- **Headline** (serif, weight 600, size ≈ 1.5-2rem, line-height ≈ 1.2): 板块标题 — "AI 热榜"、"金价动态"。
- **Title** (sans, weight 600, size ≈ 1.25rem, line-height ≈ 1.3): 板块内数据标题、子板块标题。
- **Body** (sans, weight 400, size ≈ 1rem, line-height ≈ 1.6, max-width 65-75ch): 正文数据、描述、市场评论。
- **Label** (sans, weight 500, size ≈ 0.75-0.875rem, letter-spacing ≈ 0.02em, uppercase optional): 数据标签、日期、涨跌符号、来源标注。

**The Scale Commitment Rule.** 模数化字阶，≥1.25 ratio 递进。扁平字阶（1.1× 间距）是未决断的标志 — 本项目的标题层要有明确的视觉权重落差。

## 4. Elevation

默认平面。Responsive 效能量意味着版面是稳定的报纸感，不是浮动的卡片海洋。板块之间用间距和排版节奏区分，不是阴影堆叠。偶尔 hover 状态有微妙的 tonal lift（surface 明度微调），但 rest 状态是平的。

**The Flat-By-Default Rule.** Rest 状态 = 平面。深度通过排版层级（大小、粗细、颜色）传递，不通过阴影。Hover / focus 时 tonal surface lift 作为状态反馈，不是常态装饰。

## 5. Components

`[to be documented once components are built]`

## 6. Do's and Don'ts

### Do:
- **Do** 用排版节奏（大小、粗细、间距落差）建立信息层级，而非阴影和边框。
- **Do** 用 Full palette 的命名色彩角色（primary / accent / rise / fall）标记信息的语义含义。
- **Do** 在涨跌指示中同时使用色彩 + ▲▼ 算号 + ± 符号，确保色弱用户可读。
- **Do** 让板块有主有次、有快有慢，像报纸版面而非均匀网格。
- **Do** 用衬线标题传递编辑权威感，无衬线正文保证数据可读性。
- **Do** 使用 `text-wrap: balance` 于板块标题，`text-wrap: pretty` 于长文本。
- **Do** 纯白背景 + 品牌色传递温度，而非背景染色。

### Don't:
- **Don't** 创建冷淡数据墙 — 灰蓝工业仪表板、无视觉节奏的表格堆砌、冷硬的数据罗列。参考 PRODUCT.md 的反参考："冷淡工业感"。
- **Don't** 使用奶油色 / 米色背景（oklch L 0.84-0.97, C < 0.06, hue 40-100）— 这是 2026 AI 默认模板，不是品牌表达。
- **Don't** 使用 reflex-reject 字体族（Fraunces, Newsreader, Cormorant, Playfair, Inter, DM Sans 等）— 这些是训练数据默认值。
- **Don't** 给每个板块加侧边彩色条纹（border-left > 1px）— absolute ban。
- **Don't** 用渐变文字（background-clip: text + gradient）— absolute ban。
- **Don't** 嵌套卡片 — absolute ban。
- **Don't** 在每个板块标题上方加 tiny uppercase tracked eyebrow — 这是 AI 搭架 reflex，不是品牌节奏。
- **Don't** 让标题文字溢出容器 — 大 clamp + 窄网格 = 移动端溢出灾难。
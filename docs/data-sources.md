# 日报数据爬取流程

> 每个板块的数据源、接口地址、参数、输出格式、更新时间获取方式汇总。

## 概览

| 板块 | 数据源 | 接口类型 | 认证 | 每次条数 |
|------|--------|----------|------|----------|
| 加密货币 | CoinGecko API | REST JSON | 无 | 5 条 |
| 股市新闻 | 今日头条财经热榜 | REST JSON | 无 | 10 |
| AI 热榜 | aihot.virxact.com | REST JSON | 无（需 UA） | 10 |
| 金价动态 | 东方财富 push2 | REST JSON | 无 | 实时 |
| A股指数 | 东方财富 push2 | REST JSON | 无 | 4 条 |
| 美股指数 | 东方财富 push2 | REST JSON | 无 | 3 条 |
| 重金属价格 | 东方财富 push2 (期货 m:113) | REST JSON | 无 | 4 条 |
| 时事热榜 | 今日头条热榜 | REST JSON | 无 | 10 |
| A股热榜 | 东方财富 push2 (成交额排行) | REST JSON | 无 | 10 |
| 股市热榜 | 东方财富 push2 (行业板块 m:90+t:1) | REST JSON | 无 | 10 |
| 热门题材 | 东方财富 push2 (概念板块 m:90+t:3) | REST JSON | 无 | 10 |

---

## 1. AI 热榜

**数据源**: aihot.virxact.com 公开 API（通过 aihot skill）

### 接口

```bash
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 aihot-skill/0.2.0"

# 默认：精选条目 + 最近24小时
since=$(date -u -v-24H +%Y-%m-%dT%H:%M:%SZ)
curl -sH "User-Agent: $UA" \
  "https://aihot.virxact.com/api/public/items?mode=selected&since=$since&take=10"
```

### 输出字段

| 字段 | 说明 |
|------|------|
| `title` | 中文标题 |
| `title_en` | 英文标题（可选） |
| `url` | 来源链接 |
| `source` | 来源名称 |
| `publishedAt` | 发布时间（ISO 8601 UTC） |
| `summary` | 中文摘要 |
| `category` | 分类（ai-models / ai-products / industry / paper / tip） |
| `selected` | 是否精选（boolean） |

### 更新时间

`publishedAt` 字段即为条目发布时间，转换为北京时间（UTC+8）显示。

### 分类标签映射

| category slug | 中文标签 |
|---------------|----------|
| `ai-models` | 模型 |
| `ai-products` | 产品 |
| `industry` | 行业 |
| `paper` | 论文 |
| `tip` | 观点 |

---

## 2. 金价动态

**数据源**: 东方财富 push2 API（沪金/沪银期货主连）

### 接口

```bash
# 获取沪金主连(aum)和沪银主连(agm)实时行情
curl -s "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=113.aum,113.agm&fields=f2,f3,f4,f6,f12,f14,f58"
```

### 输出字段

| 字段代码 | 说明 |
|----------|------|
| `f2` | 最新价（沪金：元/克，沪银：元/千克） |
| `f3` | 涨跌幅（%） |
| `f4` | 涨跌额 |
| `f6` | 成交额 |
| `f12` | 代码（aum = 沪金主连，agm = 沪银主连） |
| `f14` | 名称 |

### 昨日对比

从 `f3`（涨跌幅%）和 `f2`（当前价）计算昨日价：

```python
yesterday_price = current_price / (1 + change_pct / 100)
```

或通过 K 线接口获取前一日收盘价：

```bash
# 获取最近2日K线
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=113.aum&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=2"
```

K 线格式：`日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率`

### 更新时间

通过实时行情接口的时间戳字段，或取 `f58`（时间戳）转换为北京时间。

### 单位说明

- **黄金**: 沪金主连价格单位为 **元/克**（直接展示）
- **白银**: 沪银主连价格单位为 **元/千克**，需 **÷1000** 转换为 **元/克**

---

## 3. A股指数

**数据源**: 东方财富 push2 API

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001,0.399006,1.000300&fields=f2,f3,f4,f6,f12,f14,f104,f105,f106"
```

### secid 映射

| secid | 指数 |
|-------|------|
| `1.000001` | 上证综指 |
| `0.399001` | 深证成指 |
| `0.399006` | 创业板指 |
| `1.000300` | 沪深300 |

### 输出字段

| 字段代码 | 说明 |
|----------|------|
| `f2` | 最新点位 |
| `f3` | 涨跌幅（%） |
| `f4` | 涨跌额 |
| `f6` | 成交额 |
| `f12` | 代码 |
| `f14` | 名称 |
| `f104` | 上涨家数 |
| `f105` | 下跌家数 |

### 昨日对比

使用 `f3`（涨跌幅%）反推昨日收盘：`yesterday = today / (1 + f3/100)`

### 更新时间

交易日 9:30-15:00 实时更新。非交易时段显示上一交易日收盘数据。通过接口时间戳获取更新时刻。

---

## 4. 美股指数

**数据源**: 东方财富 push2 API

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=100.SPX,100.NDX,100.DJIA&fields=f2,f3,f4,f6,f12,f14"
```

### secid 映射

| secid | 指数 |
|-------|------|
| `100.SPX` | 标普500 |
| `100.NDX` | 纳斯达克 |
| `100.DJIA` | 道琼斯 |

### 输出字段

同 A股指数字段格式。注意：美股 f104/f105（上涨/下跌家数）为 0，东方财富不提供该数据。

### 昨日对比

同 A股方法。

### 更新时间

美股交易时段（北京时间 21:30-次日4:00）实时更新。非交易时段显示最近收盘数据。

---

## 5. 重金属价格

**数据源**: 东方财富 push2 API（上海期货交易所期货主连，市场代码 m:113）

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=4&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:113&fields=f2,f3,f4,f6,f12,f14&ut=bd1d9ddb0ed86000b97a016bf453f5e"
```

筛选品种代码：

| f12 | 名称 | 单位 |
|-----|------|------|
| `cum` | 沪铜主连 | 元/吨 |
| `alm` | 沪铝主连 | 元/吨 |
| `znm` | 沪锌主连 | 元/吨 |
| `nim` | 沪镍主连 | 元/吨 |

### 昨日对比

使用 K 线接口获取前一日收盘价：

```bash
# 沪铜主连最近2日K线
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=113.cum&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=2"
```

K 线每行格式：`日期,开盘,收盘,最高,最低,成交量,...,涨跌幅,涨跌额,...`

前一行的 `收盘` 即为昨日价格，与今日 `f2`（最新价）对比计算涨跌额和涨跌幅。

### 更新时间

交易时段实时更新。通过行情接口时间戳获取。

---

## 6. 时事热榜

**数据源**: 今日头条热榜 API（首选） + 百度热搜 API（备选）

### 首选：今日头条热榜

```bash
curl -s "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
```

#### 输出字段

| 字段 | 说明 |
|------|------|
| `Title` | 话题标题 |
| `Url` | 链接（直接可点击） |
| `HotValue` | 热度值 |
| `ClusterIdStr` | 事件ID |
| `Label` | 标签（"热"、"新"、"沸"） |
| `Image.url` | 缩略图 |

取前 10 条，按 `HotValue` 降序排列。

### 备选：百度热搜

```bash
curl -s "https://top.baidu.com/api/board?tab=realtime" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
```

输出 JSON，`data.cards[].content[]` 中每条含 `word`（关键词）、`desc`（描述）、`url`（链接）、`hotScore`（热度）。

### 更新时间

接口返回的数据为实时滚动更新。无明确的 `updatedAt` 字段，取当前请求时间作为数据更新时间。

### 链接展示

头条热榜的 `Url` 字段即为可点击链接，直接展示。百度热搜的 `url` 字段同理。

---

## 7. A股热榜（今日成交额排行前10）

**数据源**: 东方财富 push2 API（按成交额排序取前10）

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f6&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2&fields=f2,f3,f4,f6,f12,f14,f62,f66,f69,f184"
```

### 输出字段

| 字段代码 | 说明 |
|----------|------|
| `f2` | 最新价 |
| `f3` | 涨跌幅（%） |
| `f4` | 涨跌额 |
| `f6` | 成交额（排序依据） |
| `f12` | 代码 |
| `f14` | 名称 |
| `f62` | 主力净流入 |
| `f184` | 涨跌原因标签 |

### 昨日对比

`f3` 即为今日涨跌幅，展示涨跌即可。

### 板块标签

每只股票所属板块需二次查询（通过股票代码查所属行业板块）。简化方案：仅展示涨跌率和名称，不附加板块标签。若需标签，可用东方财富个股详情接口：

```bash
curl -s "https://push2.eastmoney.com/api/qt/stock/get?secid=1.{f12}&fields=f12,f14,f100"
```

`f100` 为行业名称。

### 更新时间

交易时段实时更新。

---

## 8. 股市热榜（行业板块涨跌幅排行前10）

**数据源**: 东方财富 push2 API

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:1&fields=f2,f3,f4,f6,f12,f14,f104,f105,f22,f62,f184"
```

### 输出字段

| 字段代码 | 说明 |
|----------|------|
| `f2` | 板块指数点位 |
| `f3` | 涨跌幅（%） |
| `f4` | 涨跌额 |
| `f6` | 成交额 |
| `f12` | 板块代码（如 BK0428） |
| `f14` | 板块名称（如 "白酒"） |
| `f104` | 上涨家数 |
| `f105` | 下跌家数 |
| `f22` | 涨跌家数比 |

### 方向判断

- `f3 > 0` → 强势（绿色badge，中文金融惯例）
- `f3 < -1` → 承压（红色badge）
- `f3` 在 `-1~0` 之间 → 分化（中性badge）

### 更新时间

交易时段实时更新。

---

## 9. 热门题材（概念板块涨跌幅排行前10）

**数据源**: 东方财富 push2 API

### 接口

```bash
curl -s "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:90+t:3&fields=f2,f3,f4,f6,f12,f14,f62,f184"
```

### 输出字段

同股市热榜字段。`f14` 为概念名称（如 "车联网"、"AI芯片"）。

### 描述补充

每条题材的描述信息需通过概念板块详情接口获取：

```bash
# 获取概念板块成分股（用于提取简短描述）
curl -s "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=3&po=1&np=1&fltt=2&invt=2&fid=f3&fs=b:{f12}+f:!50&fields=f2,f3,f12,f14"
```

取前3只成分股名称作为题材描述（如 "AI芯片 → 中芯国际、寒武纪、海光信息"）。

### 更新时间

交易时段实时更新。

---

## 10. 加密货币价格

**数据源**: CoinGecko 免费 API（无需认证）

### 接口

```bash
# 获取 BTC/ETH/SOL/BNB/DOGE 的 CNY 价格 + 24h涨跌幅
curl -s "https://api.coingecko.com/api/v3/coins/markets?vs_currency=cny&ids=bitcoin,ethereum,solana,binancecoin,dogecoin&order=market_cap_desc&per_page=5&page=1&sparkline=false&price_change_percentage=24h"
```

### 输出字段

| 字段 | 说明 |
|------|------|
| `symbol` | 币种代号（btc, eth, sol, bnb, doge） |
| `name` | 全名（Bitcoin, Ethereum...） |
| `current_price` | 当前价格（CNY） |
| `price_change_percentage_24h` | 24h涨跌幅（%） |
| `market_cap` | 市值（CNY） |
| `high_24h` | 24h最高价 |
| `low_24h` | 24h最低价 |
| `last_updated` | 最后更新时间（ISO 8601 UTC） |

### 价格显示

- BTC: ¥426,753（直接显示）
- ETH: ¥11,221（直接显示）
- SOL: ¥449.5
- BNB: ¥4,050
- DOGE: ¥0.58

### 更新时间

`last_updated` 字段转为北京时间显示。CoinGecko 数据每分钟更新。

### 限流

免费 API 无需 key，但限流约 10-30 req/min。串行调用即可。

---

## 11. 股市新闻

**数据源**: 今日头条财经热榜

### 接口

```bash
curl -s "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc&category_name=finance" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
```

### 输出字段

同时事热榜接口。额外有 `InterestCategory` 字段，含 `finance`、`stock`、`international` 等分类。

可进一步过滤只取 `finance`/`stock` 类别条目，确保与股市相关。

### 更新时间

实时滚动。取当前请求时间。

### 链接展示

每条 `Url` 为可点击链接。

---

## 通用注意事项

### 昨日对比通用方法

所有有 `f3`（涨跌幅）的数据，可用公式反推昨日价格：

```
yesterday_price = today_price / (1 + f3 / 100)
change_amount = today_price - yesterday_price
```

对需要精确昨日收盘价的板块（金价、重金属），使用 K 线接口：

```bash
# 通用K线接口：secid={品种}, lmt=2取最近2日
curl -s "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20500101&lmt=2"
```

K 线每行：`日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率`

第1行 = 昨日数据（`收盘` 列为昨日价）
第2行 = 今日数据

### 更新时间获取通用方法

- **有 f58 字段的接口**: `f58` 为时间戳，需转换（毫秒级Unix timestamp → 北京时间）
- **无时间字段的接口**: 取当前请求时刻作为更新时间
- **交易时段数据**: 标注 "交易时段实时更新，非交易时段显示最近收盘"

### 中文金融涨跌惯例

- **涨** = 红色（`f3 > 0`）
- **跌** = 绿色（`f3 < 0`）
- 色弱安全：涨跌标识同时使用 ▲▼ 符号 + ± 数字

### 请求频率

- 东方财富 API：无需认证，但建议串行请求，间隔 ≥ 0.5s
- 今日头条 API：需浏览器 UA，间隔 ≥ 1s
- aihot API：600 req/min/IP 限制，串行调用

### 错误处理

- 东方财富 `rc=0` 表示成功，`rc=102` 表示无数据，`rc=100` 表示品种代码错误
- 今日头条返回空 `data` 数组表示无热榜数据
- aihot 403 = UA 缺失，429 = 限流，404 = 日报未生成

---

## 执行顺序建议

按页面展示顺序依次爬取：

1. **AI 热榜** → aihot skill（最先，因为用户可能先关注）
2. **A股指数 + 美股指数** → 东方财富 ulist 一次请求
3. **金价 + 重金属** → 东方财富期货列表筛选 + K线昨日对比
4. **时事热榜** → 今日头条热榜
5. **A股热榜** → 东方财富 clist 按成交额排序
6. **股市热榜** → 东方财富 clist 行业板块
7. **热门题材** → 东方财富 clist 概念板块

总请求约 8-10 次，串行执行，预计 5-8 秒完成全部数据采集。
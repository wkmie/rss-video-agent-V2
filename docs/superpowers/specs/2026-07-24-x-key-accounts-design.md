# X 重点账号实时推文采集设计

## 目标

在现有“信息与热点 → X 消息 → 重点账号采集”中接入 `大V.txt` 的账号名单。用户进入该页面时自动抓取一次最新推文，也可以手动刷新；推文进入现有 Web3 热点数据链路并按账号展示。

## 范围

- 导入并规范化 `大V.txt` 中的 45 个账号。
- 保留账号所属地区、备注、启用状态和优先级。
- 使用已有 `X_BEARER_TOKEN` 和 X API v2 Recent Search。
- 页面首次进入时自动抓取一次，Streamlit 重绘不重复请求。
- 提供“抓取最新推文”按钮，允许用户主动再次抓取。
- 复用现有 `Web3HotItem`、去重、互动指标和热度评分。
- 按账号分组显示推文及采集结果。
- 不增加常驻后台任务，不在页面关闭后持续请求。

## 不在本期范围

- 不实现后台定时调度器。
- 不实现账号增删改数据库管理页面。
- 不实现 X Filtered Stream 常驻连接。
- 不保证清单中的每个账号当前都真实存在或可公开访问。

## 账号配置

新增版本化 JSON 配置文件，字段如下：

```json
{
  "username": "blknoiz06",
  "display_name": "Ansem",
  "region": "全球",
  "priority": "P1",
  "enabled": true
}
```

导入时移除 `@`、序号和说明性标点；用户名按 X 规则进行格式校验。地区标题应用到其后的账号。格式无效的条目不进入查询，并在加载结果中报告。

## 采集架构

新增独立的 `XKeyAccountsCollector`，不改变现有关键词型 `XRecentSearchCollector`。采集器读取账号配置，将多个 `from:username` 条件拼成 OR 查询，并确保每个查询不超过 Recent Search 的 512 字符限制。

查询附带：

- `-is:retweet`，避免普通转推淹没原创消息。
- `tweet.fields=created_at,public_metrics,author_id,lang`
- `expansions=author_id`
- `user.fields=username,name,verified`
- `max_results=100`

X 官方文档确认 `from:` 可作为独立搜索条件，多账号可使用 OR；Recent Search 查询长度为 512 字符、每次最多返回 100 条。参考：

- https://docs.x.com/x-api/posts/search/integrate/operators
- https://docs.x.com/x-api/posts/search/integrate/overview
- https://docs.x.com/x-api/fundamentals/rate-limits

采集结果使用真实用户名作为 `author`，使用 `X / @username` 作为 `source_name`，使用 `x_key_accounts` 作为 `source_type`。推文链接使用 `https://x.com/{username}/status/{tweet_id}`。

## 数据流

1. 用户进入“重点账号采集”标签。
2. 当前 Streamlit 会话未执行过自动抓取时，前端调用重点账号抓取接口。
3. 后端按查询长度把启用账号分批。
4. 每批调用 X Recent Search，解析推文与用户扩展信息。
5. 复用 `fetch_and_store_hot_items` 的清洗、去重和热度评分流程写入数据库。
6. 前端查询 `source_type=x_key_accounts` 的最近结果。
7. 页面按账号分组展示，并显示本次抓取数量、错误和更新时间。
8. 用户点击手动刷新时重复步骤 2-7。

## API

复用现有接口，不增加重复业务协议：

- `POST /api/web3-hot/fetch-now`
  - 请求：`{"source_type": "x_key_accounts"}`
  - 响应继续使用 `fetched_count`、`inserted_count`、`updated_count`、`skipped_count`、`errors`。
- `GET /api/web3-hot/list`
  - 参数：`source_type=x_key_accounts`、`hours`、`limit`。

统一 Streamlit API 客户端增加上述 Web3 热点接口的直连模式映射，确保本地运行和 Streamlit Cloud 远程 API 模式一致。

## 前端设计

位置：`信息与热点 → X 消息 → 重点账号采集`。

页面顶部显示：

- 监控账号总数
- 最近抓取时间
- 最近新增推文数
- 本次失败批次数

操作区包含：

- “抓取最新推文”主按钮
- 时间范围选择
- 地区选择
- 账号搜索

内容区按账号分组，不采用滚动消息墙。每条推文显示：

- 账号名
- 发布时间
- 正文
- 点赞、转发、回复、引用
- 热度分
- X 原文链接

账号暂无推文时不生成空分组。账号配置清单放在折叠区，展示地区、备注、优先级和启用状态。

## 自动刷新规则

- 每个 Streamlit 会话首次执行“重点账号采集”渲染时自动请求一次。
- 使用 `st.session_state` 记录自动抓取完成状态，普通组件重绘不重复调用。
- 自动抓取失败后仍标记本次尝试完成，避免错误循环；用户可手动重试。
- 手动刷新不受会话标记限制。

## 错误处理

- 未配置 `X_BEARER_TOKEN`：显示明确提示，不影响 RSS 等其他数据源。
- 单个批次失败：记录错误并继续后续批次。
- 401/403：提示密钥或当前 X API 套餐不允许访问。
- 429：读取并展示限流信息，不在页面请求中长时间阻塞重试。
- 无效账号或无返回结果：不阻断其他账号。
- 数据库重复：沿用 `content_hash` 去重并更新互动指标。

## 测试

- 账号配置解析和用户名规范化测试。
- 查询分批测试，确保每条查询不超过 512 字符并包含全部启用账号。
- X API 响应解析测试，确保 `author` 为用户名且互动指标正确。
- 分批失败隔离测试。
- 数据库存储与重复更新测试。
- Streamlit 页面测试，验证自动抓取只执行一次、手动刷新可再次调用、结果按账号展示。

## 验收标准

- 重点账号页面能识别配置中的全部有效账号。
- 首次进入页面自动触发一次抓取，重绘不会重复触发。
- 手动刷新可以再次获取推文。
- 推文以真实账号分组显示，并带互动指标、热度和原文链接。
- 单批失败不影响其他批次入库。
- 不破坏现有关键词 X 搜索、RSS、Web3 热度评分和内容生成功能。

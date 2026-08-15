# Growth Analytics Decision Platform V2 独立发布验收报告

## 1. 最终结论

**GO。**

当前工作树满足本地发布候选标准：两个案例的事实边界、业务方法论、静态数据、FastAPI、DuckDB、React 六页、桌面端与移动端视觉、隐私检查和自动化质量门禁均已通过独立复验。验收期间发现的发布级问题已经全部修复并回归通过，没有剩余 HIGH 或 BLOCKER。

该结论表示“代码、内容与本地可运行交付物可以进入公开发布流程”，不表示 GitHub Pages 或远程 Docker 构建已经在线成功。发布后的 GitHub Actions、Pages 实际地址和线上静态资源仍须以对应 commit 的远程结果为准。

| 项目 | 验收状态 |
|---|---|
| 验收日期 | 2026-08-16（Asia/Shanghai） |
| 被测对象 | V2 未提交工作树，最终 commit SHA 待发布 |
| Python 自动化 | 158 passed，0 failed |
| 覆盖率 | 92.86%，高于 85% 门槛 |
| 前端门禁 | lint、typecheck、普通构建、Pages base 构建全部通过 |
| 浏览器验收 | 六页桌面端和移动端全部通过 |
| 控制台错误 | 六页均为 0 |
| 页面级横向溢出 | 桌面端和移动端均未发现 |
| 隐私扫描 | 真实雇主名、真实业务量级、真实激励金额、精确 referral 样本量均未发现 |
| Docker 本机运行 | 本机无 Docker；仅完成配置审查，远程 CI 为最终运行门禁 |
| GitHub Pages 在线地址 | 尚未发布；发布后必须 smoke test |

## 2. 验收原则与独立性

本报告不采信实现者的“已完成”声明，而是从仓库、运行时响应、真实浏览器渲染和自动化测试重新取证。验收中未修改生产代码；发现缺陷后由实现者修复，再由独立验收重新执行对应回归。

本次特别遵守以下内容边界：

1. 两个项目只共享“业务问题 → 指标体系 → 拆解定位 → 负证据 → 假设 → 实验 → 价值决策 → 治理”的分析方法，不伪造成同一条生产数据链。
2. 用户口述中的真实项目事实与公开方法论严格分开；公开资料只用来校验 SOP，不用于补写用户经历或业务数字。
3. 缺少绝对实验提升值时不反推、不虚构；存在口径风险时明确标注并冻结决策。
4. 对外数据采用合成或脱敏表达；不公开真实雇主、真实日活规模、真实激励金额和被要求隐藏的精确样本量。

## 3. 发现并关闭的缺陷

### HIGH：GitHub Pages base path 与仓库名可能不一致

- 风险：仓库重命名后，硬编码 base path 会导致 JS、CSS、favicon 或静态 JSON 在 Pages 上 404。
- 修复：Pages workflow 从 `github.event.repository.name` 动态生成 `VITE_BASE_PATH`。
- 回归：分别用旧仓库 slug 和新仓库 slug 构建，入口脚本、favicon 和 `data/portfolio.json` 的前缀均正确。
- 结果：关闭。

### HIGH：深滚动后切换模块仍停留在旧滚动位置

- 风险：招聘官从长页面进入新模块时直接看到页面中段，误以为页面标题或首屏缺失。
- 修复：Router 内基于 location 变化执行同步归顶，并在下一帧校准。
- 回归：桌面端与移动端从总览底部依次切换六个模块，`scrollY=0`；标题回到首屏。
- 结果：关闭。

### MEDIUM：浏览器前进/后退可能恢复旧滚动位置

- 风险：点击导航正常，但浏览器历史导航仍可能落在页面中段。
- 修复：挂载期间设置 `history.scrollRestoration='manual'`，location key/pathname 变化时归顶。
- 回归：连续两次后退、两次前进均回到页面顶部，控制台无错误。
- 结果：关闭。

### HIGH：公开数据曾包含不必要的精确 referral 样本量

- 风险：UI 使用脱敏描述，但静态 JSON、API 或文档仍可能泄露更精确的真实项目口径。
- 修复：referral 实验改为 `sample_size=null`、`sample_display="百万级脱敏样本"`，并将精确值加入隐私禁项；留存实验仍保留用户明确给出的“约30万样本”。
- 回归：工作树全文扫描禁项 0 命中；重新导出的静态 JSON、临时 DuckDB 和 API 返回完全一致。
- 结果：关闭。

## 4. 两个真实项目的内容一致性

### 4.1 老带新增长项目

| 必须表达的事实 | UI / 数据 / 文档验收 |
|---|---|
| 最终业务指标是拉新用户数 | 通过；核心业务结果与实验过程指标分层展示 |
| 曝光 → 活动页面 → 邀请点击 → 微信分享 → 新用户 | 通过；漏斗链路完整，未把中间转化当最终业务结果 |
| 裂变率从 2.14% 到 2.9%，但分母待确认 | 通过；展示变化，同时冻结口径、避免据此直接决策 |
| 邀请点击率约 21% → 17% → 23.5% | 通过；体现原版、复杂改版、简化改版的定位闭环 |
| 微信分享成功率约 95% | 通过；作为稳定环节和负证据使用 |
| 激励金额不能公开真实值 | 通过；公开版仅用 100 → 160 的指数化表达 |
| 两周、百万级脱敏样本 | 通过；无精确 referral 样本量残留 |
| 实验结果 p<0.05 | 通过；同时要求统计显著与业务显著 |
| 首月 LTV/CAC 为 2.18，外投基准 1.90 | 通过；比较清楚，未误写成净 ROI |

结论：项目链路不是“做了一张看板”，而是从指标树识别关键卡点，以稳定环节形成负证据，再用实验和单位经济性决定是否继续迭代。

### 4.2 新用户留存项目

| 必须表达的事实 | UI / 数据 / 文档验收 |
|---|---|
| 次 7 日内留存从 48% 下滑到 41% | 通过 |
| 口径是 Day 1–7 至少回访一次，不是 exact Day 7 | 通过；指标合同和案例说明均有明确区分 |
| 分层包含渠道、设备类型、设备品牌、系统、年龄、性别、地域、城市等级 | 通过；维度无缺失 |
| 平板留存约低 10pp，且平板占比上升 | 通过；作为 mix shift 的结构性解释 |
| 提升手机投放占比的建议短期未落地 | 通过；未伪造策略已上线或已产生收益 |
| 下载 → 注册登录 → 首页 → 浏览点击 → 浏览内容 → 互动/主页/关注 | 通过；产品路径完整 |
| 路径转化无明显变化 | 通过；被正确用作排除“使用卡点”的负证据 |
| 高频高时用户作为标杆用户 | 通过；未补造存在冲突的具体阈值 |
| 主页浏览/关注渗透率为 2.5x | 通过；只作为相关性线索，不声称因果 |
| 退出页弹窗引导访问主页并关注 | 通过；实验组与对照组唯一策略差异清楚 |
| 约 30 万样本、两周 | 通过 |
| 留存显著提升，p<0.05 | 通过；未虚构用户没有提供的绝对 lift |

结论：项目从结构分解和路径排查开始，先解释“为何下滑”，再用标杆用户寻找候选杠杆，最后用 A/B 实验从相关性推进到因果证据。

### 4.3 两个案例的共通点与边界

页面明确说明：两案不是同一条生产链路，而是同一套可复用分析方法在“拉新”和“留存”两个问题上的应用。共通能力包括：

- 先定义业务结果，再建立指标树和口径合同；
- 用分层、漏斗、mix shift 和负证据缩小问题范围；
- 将描述性发现、相关性线索和因果结论分级；
- 预先确定核心指标、护栏指标、MDE、Power、周期与停止规则；
- 最终把统计结果放回业务价值和治理约束中决策。

这一表达能够突出业务判断和可复用经验，不会让技术组件抢在业务问题之前。

## 5. 公开方法论对照

`docs/public-methodology-benchmark_zh.md` 的来源集合已逐项检查。来源覆盖 North Star 与 metric tree、referral funnel、区间留存、mix shift、路径分析、相关性边界、MDE/Power、A/A、SRM、SMD、固定实验周期、新奇效应、网络干扰以及 LTV/CAC 与 ROI 区分。

验收确认：

- 外部资料只支持分析流程和统计治理，不承担两个项目的事实证明；
- 文档将描述性证据、相关性证据、实验因果证据和商业决策分开；
- A/A 用于检查分流、口径和埋点，不被误写成证明策略有效；
- SRM、SMD、分层结果、固定 horizon、中途不按 p 值停试均进入实验健康检查；
- 新奇效应和网络效应被列为适用时的风险，而不是为了显得复杂而强行宣称已发生；
- LTV/CAC 作为价值比率展示，与净 ROI 的公式边界清楚。

## 6. 全栈与数据一致性

### 6.1 前端

- React + TypeScript + Vite。
- ECharts 负责指标树、漏斗、趋势、分层、实验与经济性图表。
- HashRouter 提供六个公开可访问路由：总览、老带新、留存、实验中心、价值评估、指标治理。
- GitHub Pages base path 由仓库名动态生成，兼容重命名。
- 静态模式从 `web/public/data/portfolio.json` 读取；API 模式可切换至 FastAPI。

### 6.2 后端与数据库

- FastAPI `/health` 与 `/api/v2/*` 路由可运行。
- `/api/v2/portfolio`、overview、两个 case、experiments、metric contracts、decisions 均由 V2 服务层提供。
- DuckDB 含 12 张 `portfolio_*` V2 表。
- 使用全新临时 DuckDB 初始化后，静态 bundle、新导出文件与 API 核心事实一致。

关键一致性结果：

```text
static_equals_fresh_export = True
API /api/v2/portfolio      = 200
referral sample_size       = null
referral sample_display    = 百万级脱敏样本
retention sample_size      = 300000
retention sample_display   = 约30万样本
DuckDB referral sample     = (null, 百万级脱敏样本)
```

### 6.3 两种运行模式

- 静态模式：生产 Vite preview 请求 `/data/portfolio.json` 返回 200。
- API 模式：本地启动 Uvicorn 后，生产 Vite preview 请求 `/api/v2/portfolio` 返回 200，首页 KPI 与图表正常渲染，控制台错误为 0。

### 6.4 Docker 与 nginx

静态检查确认：

- backend 容器提供 FastAPI 8000 端口并使用持久化数据卷；
- frontend 容器使用 nginx，对外提供 80 端口；
- `/api/` 代理至 backend，SPA 路由有 fallback；
- compose 将前端映射到本机 8501；
- CORS 覆盖本地开发和 compose 访问源；
- CI 包含 `docker compose config --quiet` 与 `docker compose build --pull`。

本机未安装 Docker，因此没有声称“本地容器已经跑通”。远程 CI 的 Docker job 是发布后的必要运行证据。

## 7. 自动化质量门禁

### 7.1 Python

执行：

```powershell
..\growthlab-user-growth-analytics\.venv\Scripts\python.exe -m ruff check .
..\growthlab-user-growth-analytics\.venv\Scripts\python.exe -m ruff format --check .
..\growthlab-user-growth-analytics\.venv\Scripts\python.exe -m compileall -q analytics backend scripts frontend tests
..\growthlab-user-growth-analytics\.venv\Scripts\python.exe -m pytest `
  --cov=analytics --cov=backend --cov=scripts `
  --cov-report=term-missing --cov-fail-under=85
```

结果：

- Ruff：通过；100 个文件格式正确。
- Compileall：通过。
- Pytest：158 passed，0 failed。
- Coverage：92.86%。
- 唯一警告：Starlette TestClient 使用的 httpx 兼容接口已弃用；当前行为不受影响。

### 7.2 前端

执行并通过：

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run build
$env:VITE_BASE_PATH='/growth-analytics-decision-platform/'
npm.cmd run build
```

Vite 对主 chunk 超过 500 kB 给出构建警告，但不影响正确性；这是 LOW 级性能优化项，可以在未来按页面拆包。

### 7.3 仓库卫生与隐私

- `git diff --check`：通过。
- 待发布文件中无大于 10 MiB 的候选文件。
- 本地 DuckDB 约 101 MiB，但已被忽略，不会进入发布提交。
- 真实雇主名称：0 命中。
- 真实业务量级：0 命中。
- 精确 referral 样本量禁项：0 命中。
- 明显密钥、token 与私钥：未发现真实凭据。
- 隐私扫描使用 `git ls-files --cached --others --exclude-standard`，覆盖已跟踪与待提交的新文件，而不只检查 git diff。

## 8. 真实浏览器视觉验收

浏览器验收使用 Playwright CLI 和真实 Chromium，不只检查 DOM。所有页面分别检查 1440×1000 桌面端和 390×844 移动端的首屏、滚到底部和整页截图，并实际查看截图。

| 页面 | 桌面端 | 移动端 | 图表渲染 | Console |
|---|---|---|---|---|
| 总览 | 通过 | 通过 | 通过 | 0 error |
| 老带新 | 通过 | 通过 | 通过 | 0 error |
| 留存 | 通过 | 通过 | 通过 | 0 error |
| 实验中心 | 通过 | 通过 | 通过 | 0 error |
| 价值评估 | 通过 | 通过 | 通过 | 0 error |
| 指标治理 | 通过 | 通过 | 通过 | 0 error |

检查结果：

- 六页均有实际 SVG 图表节点，未出现空白图表容器。
- 桌面端文档宽度不超过 viewport；无页面级横向滚动。
- 移动端无页面级横向溢出；必要的宽表或流程条只在自身组件内滚动。
- 移动菜单可打开、跳转并收起。
- 深滚动后点击六个模块均回到顶部。
- 浏览器连续后退/前进均回到新页面首屏。
- 标题、KPI、图例、说明文字和底部内容未发现明显裁切或遮挡。
- README 主截图是最新 V2 总览，且未包含公开限制信息。

验收截图保存在本地忽略目录 `output/playwright/`，不会作为无必要的大文件进入发布提交。

## 9. 招聘官三分钟体验

### 0–30 秒：先看业务问题

README 与首页首先呈现两个问题：如何在外部拉新承压时建立可持续 referral 增长，以及如何解释并改善新用户留存下滑。技术栈没有抢占首屏叙事。

### 30–90 秒：看指标体系与定位

招聘官可以直接看到 referral 指标树、完整漏斗、稳定环节、异常定位，以及留存的区间口径、mix shift、路径负证据和标杆用户对比。

### 90–150 秒：看实验与价值

实验中心展示目标、核心与护栏指标、MDE/Power、Hash 分流、A/A、SRM/SMD、固定周期、新奇效应和网络效应；价值页把实验显著性放回 LTV/CAC 与外投基准中判断。

### 150–180 秒：看可复用沉淀

指标治理页展示指标合同、证据层级、决策记录和 SOP。两项目用同一框架复盘，但没有被包装成同一生产系统。

结论：资深数据分析师能够从链接快速识别候选人的业务理解、指标口径意识、负证据意识、因果边界、单位经济性与治理能力，而不会首先看到技术堆砌。

中文小白教程将“招聘官只看 GitHub/在线页面”和“项目所有者本地启动”分开，步骤简洁，适合作为仓库入口说明。

## 10. 剩余风险与发布后门禁

以下项目不是当前仓库的阻断缺陷，但在声称“已经线上发布”前必须完成：

1. 提交并推送最终 commit，记录 commit SHA。
2. 确认 GitHub Actions 的 Python、frontend、Docker jobs 全绿。
3. 确认 Pages 实际仓库地址加载首页、六个 HashRouter 页面和静态 JSON，且无 404。
4. 用无登录浏览器打开公开链接，完成一次桌面端与移动端 smoke test。
5. 发布后重新读取 README，确认主截图、在线链接、合成/脱敏声明与最终仓库名一致。

性能方面仅剩一个 LOW：前端主 chunk 较大，可在未来通过路由级 lazy import 和 ECharts 按需引入优化；它不影响当前内容、功能或发布正确性。

## 11. 发布判断

**最终独立 QA：GO。**

可以进入提交、推送和 GitHub Pages 发布阶段。发布负责人不得在远程 CI 和线上 readback 完成前，把本报告解释为“Docker 与 Pages 已经在线验证成功”。

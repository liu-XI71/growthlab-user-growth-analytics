import type { EChartsOption } from 'echarts'
import { ArrowRight, BadgeCheck, BookOpenCheck, Check, ChevronRight, CircleDollarSign, Clock3, Database, FlaskConical, GitCompareArrows, Network, ShieldCheck, Target, UsersRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import { axis, Chart, ChartCard, colors, EvidenceBadge, Insight, KpiCard, PageHeader, SectionTitle, tooltip } from '../components'
import type { PortfolioData } from '../types'

export function OverviewPage({ data }: { data: PortfolioData }) {
  const loop = data.decisionLoop
  const radar: EChartsOption = {
    radar: { radius: '62%', indicator: [{ name: '指标体系', max: 5 }, { name: '业务拆解', max: 5 }, { name: '实验设计', max: 5 }, { name: '经济判断', max: 5 }, { name: '治理沉淀', max: 5 }], splitNumber: 5, axisName: { color: colors.ink, fontWeight: 600 }, splitArea: { areaStyle: { color: ['#fff', '#f7f9fd'] } }, axisLine: { lineStyle: { color: '#dce4f0' } }, splitLine: { lineStyle: { color: '#dce4f0' } } },
    series: [{ type: 'radar', data: [{ value: [5, 5, 5, 4, 5], areaStyle: { color: 'rgba(58,115,255,.20)' }, lineStyle: { color: colors.cobalt, width: 3 }, itemStyle: { color: colors.cobalt } }] }],
  }
  return <>
    <section className="hero">
      <div className="hero-copy"><span className="eyebrow">DATA ANALYTICS PORTFOLIO · V2.0</span><h1>把增长问题，变成<br /><em>可验证的业务决策</em></h1><p>以老带新获客与新用户留存两个项目为主线，展示我如何搭指标、找断点、排除错误解释、设计实验，并用用户质量与经济性决定下一步。</p><div className="hero-actions"><Link className="primary-button" to="/referral">从案例一开始 <ArrowRight size={17} /></Link><Link className="secondary-button" to="/retention">查看留存案例</Link></div><div className="hero-proof"><span><BadgeCheck />两段真实经历脱敏重构</span><span><Database />公开数据边界清晰</span><span><FlaskConical />相关与因果严格区分</span></div></div>
      <div className="hero-visual"><div className="goal-ring"><div><span>DAU 目标完成度</span><strong>81.25%</strong><small>公开版标准化指数</small></div></div><div className="floating-card card-a"><span>获客效率</span><strong>+6.5 pp</strong><small>邀请点击率实验提升</small></div><div className="floating-card card-b"><span>用户质量</span><strong>显著提升</strong><small>次7日内留存 · p&lt;0.05</small></div><div className="floating-card card-c"><span>单位经济性</span><strong>2.18×</strong><small>首月LTV/CAC</small></div></div>
    </section>

    <section className="recruiter-route"><div><Clock3 /><span>给招聘官的 3 分钟路线</span></div><ol><li><b>60秒</b>看两个业务问题与结论</li><li><b>90秒</b>看定位链路和关键图表</li><li><b>30秒</b>看实验与指标治理</li></ol></section>
    <section className="kpi-grid four"><KpiCard label="案例一 · 实验主指标" value="17% → 23.5%" note="邀请点击率，两周百万级脱敏样本" tone="blue" /><KpiCard label="案例一 · 决策护栏" value="2.18× > 1.90×" note="首月LTV/CAC高于外投基准" tone="teal" /><KpiCard label="案例二 · 异常幅度" value="48% → 41%" note="次7日内窗口留存" tone="coral" /><KpiCard label="案例二 · 实验结论" value="p < 0.05" note="约30万样本，策略显著提升" tone="amber" /></section>

    <SectionTitle step="01" title="一套共同框架，处理两个不同的增长问题" description="不是把项目硬拼成一条生产数据链，而是把可复用的分析判断沉淀成同一套工作方式。" />
    <div className="case-grid">
      <Link to="/referral" className="case-card referral"><div className="case-card-head"><Network /><span>CASE 01 · 获客</span></div><h3>老带新增长</h3><p>外部流量下滑时，如何提高新增用户，并守住首月单位经济性？</p><div className="case-chain"><span>邀请断点</span><ChevronRight /><span>页面改版</span><ChevronRight /><span>A/B验证</span><ChevronRight /><span>LTV/CAC</span></div><div className="case-result"><strong>17% → 23.5%</strong><span>邀请点击率</span></div><small>进入完整分析 <ArrowRight /></small></Link>
      <Link to="/retention" className="case-card retention"><div className="case-card-head"><UsersRound /><span>CASE 02 · 留存</span></div><h3>新用户留存提升</h3><p>投放用户留不住时，如何区分结构变化、路径卡点与产品机会？</p><div className="case-chain"><span>分层拆解</span><ChevronRight /><span>路径排除</span><ChevronRight /><span>标杆分析</span><ChevronRight /><span>A/B验证</span></div><div className="case-result"><strong>显著提升</strong><span>次7日内留存 · p&lt;0.05</span></div><small>进入完整分析 <ArrowRight /></small></Link>
    </div>

    <SectionTitle step="02" title="我的增长分析闭环" description="从“发生了什么”走到“下一步该不该做”，每一步都留下证据、边界与决策。" />
    <div className="loop-grid">{loop.map((row, index) => <article key={String(row.step_key)}><span>{String(index + 1).padStart(2, '0')}</span><h3>{String(row.label)}</h3><p>{String(row.question)}</p>{index < loop.length - 1 && <ArrowRight className="loop-arrow" />}</article>)}</div>

    <SectionTitle step="03" title="我希望这份作品集证明什么" description="重点不是框架数量，而是面对模糊业务问题时，能否做出清晰、可信、可落地的判断。" />
    <section className="chart-grid wide-left"><ChartCard title="能力结构" subtitle="作品集各模块对应的业务能力，不是自我打分证明" badge="PORTFOLIO MAP"><Chart option={radar} height={380} ariaLabel="数据分析能力结构雷达图" /></ChartCard><div className="capability-list"><div><Target /><span><strong>指标不是越多越好</strong><p>区分结果指标、机制指标、护栏与诊断指标。</p></span></div><div><GitCompareArrows /><span><strong>定位不是寻找相关性</strong><p>保留负证据，区分结构解释、行为线索与因果结论。</p></span></div><div><FlaskConical /><span><strong>实验不是只看 p 值</strong><p>预设假设、样本、周期、护栏与可信度检查。</p></span></div><div><CircleDollarSign /><span><strong>增长最终要回到价值</strong><p>效果显著后仍要比较用户质量和单位经济性。</p></span></div></div></section>
    <Insight title="一句话总结" tone="teal" label="我的差异化"><p>我能把看板异常拆成可控业务问题，用漏斗、分层和负证据定位原因，再通过实验与经济性形成可复用的决策闭环。</p></Insight>
  </>
}

export function ExperimentPage({ data }: { data: PortfolioData }) {
  const referral = data.experiments.find(item => item.case_id === 'referral_growth')!
  const retention = data.experiments.find(item => item.case_id === 'new_user_retention')!
  const timeline = ['目标与假设', '指标与护栏', '样本与周期', '稳定Hash分流', 'A/A与SRM', '固定周期运行', '显著与业务判断']
  return <>
    <PageHeader eyebrow="EXPERIMENT CENTER" title="实验中心：先证明结果可信，再讨论是否上线" description="实验页不抢业务首页的注意力，但为每个结论提供可信度底座：预注册、分流、A/A、SRM、平衡、新奇效应、网络干扰与固定周期判断。" aside={<div className="case-tag"><ShieldCheck size={20} /><div><span>决策原则</span><strong>可信 × 显著 × 值得</strong></div></div>} />
    <div className="sop-timeline">{timeline.map((item, index) => <div key={item}><span>{index + 1}</span><p>{item}</p>{index < timeline.length - 1 && <ArrowRight />}</div>)}</div>
    <SectionTitle step="01" title="两个实验回答两个不同的业务问题" description="主指标必须处于策略可直接影响的位置，同时保留最终业务指标和不能被伤害的护栏。" />
    <section className="experiment-table"><header><span>实验</span><span>假设与策略</span><span>主指标</span><span>样本 / 周期</span><span>结论</span></header>{[referral, retention].map(item => <div key={String(item.experiment_id)}><strong>{String(item.title)}</strong><p>{String(item.strategy)}</p><span>{String(item.primary_metric)}</span><span>{item.case_id === 'referral_growth' ? '百万级脱敏样本' : '约30万'} / {String(item.duration_days)}天</span><b>{String(item.significance)}<small>{String(item.decision)}</small></b></div>)}</section>
    <SectionTitle step="02" title="老带新实验预注册卡" description="把实验前已经决定的内容与实验后看到的结果分开，避免事后选择口径。" />
    <div className="preregister-grid"><article><span>业务目的</span><strong>提高拉新用户数</strong><p>通过简化邀请界面，提升老用户点击邀请率。</p></article><article><span>核心与护栏</span><strong>邀请点击率</strong><p>最终指标：拉新用户数；护栏：新用户首月 LTV/CAC。</p></article><article><span>样本设计</span><strong>17% 基线 · MDE 3pp</strong><p>α=0.05，Power=80%；实际回收为百万级脱敏样本，不冒充最低样本量。</p></article><article><span>周期规则</span><strong>预设两周</strong><p>覆盖完整业务周期；途中监控严重风险，但不看到普通p值显著就停。</p></article></div>
    <SectionTitle step="03" title="可信度检查先于效果判断" />
    <div className="trust-grid"><article><span>01</span><h3>稳定 Hash 分流</h3><p>hash(experiment_id + user_id) % 100，保证用户稳定、不同实验独立。</p><b>作品集标准 SOP</b></article><article><span>02</span><h3>A/A 实验</h3><p>验证分流、埋点、指标和统计管道；单次 p&lt;0.05 触发调查而非自动定罪。</p><b>作品集标准 SOP</b></article><article><span>03</span><h3>SRM 与人群均衡</h3><p>先查样本比例，再看渠道、设备、城市等实验前属性，防止人群结构混淆。</p><b>作品集标准 SOP</b></article><article><span>04</span><h3>固定周期与风险</h3><p>不频繁偷看停止；老带新识别社交网络干扰，新版关注新奇效应。</p><b>已识别风险 / 可选方案</b></article></div>
    <section className="result-compare"><div><EvidenceBadge type="causal" /><h3>邀请页简化实验</h3><strong>+6.5 pp</strong><p>17.0% → 23.5% · p&lt;0.05</p><span>效果大小已披露</span></div><div><EvidenceBadge type="causal" /><h3>主页与关注引导实验</h3><strong>显著提升</strong><p>次7日内留存 · p&lt;0.05</p><span>绝对提升未稳定披露，不补造</span></div></section>
    <Insight title="p < 0.05 不是自动上线按钮" tone="amber" label="实验判断"><p>上线还需同时看业务效果大小、置信区间、护栏、数据质量、样本与周期是否达标。作品集把这些作为标准 SOP，不反向声称实习期间一定运行过平台中的全部检查。</p></Insight>
  </>
}

export function ValuePage({ data }: { data: PortfolioData }) {
  const versions = data.referral.versions
  const economics: EChartsOption = { tooltip, grid: { left: 60, right: 25, top: 30, bottom: 45 }, xAxis: { type: 'category', data: ['外部投放基准', '老带新简化版'], ...axis }, yAxis: { type: 'value', max: 2.5, name: '首月 LTV/CAC', ...axis }, series: [{ type: 'bar', barWidth: 60, data: [{ value: 1.9, itemStyle: { color: '#c9d4e6', borderRadius: [8, 8, 0, 0] } }, { value: 2.18, itemStyle: { color: colors.teal, borderRadius: [8, 8, 0, 0] }, label: { show: true, position: 'top', formatter: '2.18×', color: colors.teal, fontWeight: 700 } }] }] }
  const incentive: EChartsOption = { tooltip, grid: { left: 55, right: 25, top: 30, bottom: 55 }, xAxis: { type: 'category', data: versions.map(row => String(row.label)), axisLabel: { rotate: 12, color: colors.muted }, ...axis }, yAxis: { type: 'value', name: '激励指数', ...axis }, series: [{ type: 'line', step: 'middle', symbolSize: 10, lineStyle: { width: 4, color: colors.amber }, itemStyle: { color: colors.amber }, data: versions.map(row => row.incentive_index) }] }
  return <>
    <PageHeader eyebrow="VALUE & CHANNEL" title="价值与渠道：增长不是越便宜越好，也不是越多越好" description="当目标优先级是扩大新增时，较高的价值成本比意味着存在再投资空间；增加激励后，仍要用同口径的首月 LTV/CAC 与外部投放比较。" aside={<div className="case-tag"><CircleDollarSign size={20} /><div><span>经济口径</span><strong>首月价值 / 获客成本</strong></div></div>} />
    <section className="kpi-grid three"><KpiCard label="初始价值成本比" value="2.90×" note="不是“ROI太高”，而是存在增长再投入空间" tone="blue" /><KpiCard label="激励调整" value="100 → 160" note="公开版指数化，不披露真实金额" tone="amber" /><KpiCard label="改版后价值成本比" value="2.18×" note="仍高于外部投放1.90×" tone="teal" /></section>
    <SectionTitle step="01" title="先纠正一个业务表达：2.9 不是“ROI太高”" description="若计算式是价值÷成本，专业名称应是 LTV/CAC 或价值成本比。高于目标不是异常，而是表明在增长优先时有成本扩张空间。" />
    <div className="formula-panel"><div><span>首月 LTV</span><strong>新用户月活跃天数 × 日活跃时长 × 单位时长商业化价值</strong></div><i>÷</i><div><span>首月 CAC</span><strong>归因范围内实际激励成本 ÷ 有效新增用户数</strong></div><b>= 首月 LTV/CAC</b></div>
    <section className="chart-grid two"><ChartCard title="首月单位经济性对比" subtitle="同一时间窗口和价值口径下进行渠道比较" badge="经济护栏"><Chart option={economics} ariaLabel="老带新和外投LTV CAC对比柱状图" /></ChartCard><ChartCard title="激励投入的版本变化" subtitle="真实金额已隐去，统一标准化为指数100→160" badge="隐私安全"><Chart option={incentive} ariaLabel="老带新激励指数变化图" /></ChartCard></section>
    <SectionTitle step="02" title="为什么选择首月，而不是等三个月或半年" />
    <div className="reason-grid"><article><span>01</span><h3>快速形成可决策证据</h3><p>一个月能够积累较丰富的用户行为和商业化数据，支持及时判断方向。</p></article><article><span>02</span><h3>增长策略需要持续迭代</h3><p>等待三到六个月会拖慢反馈周期；更长期价值可在模型与后续回收中持续校准。</p></article><article><span>03</span><h3>所有渠道必须同口径</h3><p>老带新与外部投放都用首月窗口，避免拿短期成本与长期价值错误比较。</p></article></div>
    <div className="decision-banner"><div><EvidenceBadge type="decision" /><h2>当前决策：继续上线与迭代</h2><p>邀请页面实验显著提升关键动作；增加激励后，首月 LTV/CAC 仍为 2.18，高于外部投放 1.90。增长有效且单位经济性保持相对优势。</p></div><strong>2.18× <small>&gt; 1.90×</small></strong></div>
    <Insight title="经济性结论的边界" tone="amber" label="不做过度承诺"><p>首月 LTV/CAC 不等于完整生命周期 LTV，也不能写成净 ROI 218%；它支持当前版本与外部投放的相对判断，不代表所有预算都应无条件转向老带新。</p></Insight>
  </>
}

export function GovernancePage({ data }: { data: PortfolioData }) {
  const metrics = data.metricContracts
  const decisions = data.decisions
  return <>
    <PageHeader eyebrow="METRIC GOVERNANCE" title="指标治理：让每个结论都能被复核" description="同一个指标在页面、API、SQL 和面试讲述中保持同一口径；同时标明哪些是项目事实、哪些是模拟明细、哪些仍待业务确认。" aside={<div className="case-tag"><BookOpenCheck size={20} /><div><span>治理目标</span><strong>同口径 · 可追溯 · 有边界</strong></div></div>} />
    <section className="governance-principles"><div><Database /><strong>统一定义</strong><span>分子、分母、窗口、粒度</span></div><div><ShieldCheck /><strong>成熟度检查</strong><span>观察窗未完成不进入分母</span></div><div><GitCompareArrows /><strong>证据分级</strong><span>描述性、相关性、因果性</span></div><div><BadgeCheck /><strong>决策留痕</strong><span>事实、解释、假设、动作、边界</span></div></section>
    <SectionTitle step="01" title="核心指标合同" description="指标字典不是附录，而是所有看板和实验共用的业务契约。" />
    <div className="metric-contract-list">{metrics.map(metric => <article key={String(metric.metric_key)}><header><div><span>{String(metric.metric_key)}</span><h3>{String(metric.metric_name)}</h3></div><b>{String(metric.grain)}</b></header><div className="fraction"><p><small>分子</small>{String(metric.numerator)}</p><i>÷</i><p><small>分母</small>{String(metric.denominator)}</p></div><footer><strong>口径边界</strong><span>{String(metric.boundary)}</span></footer></article>)}</div>
    <Insight title="裂变率口径仍需冻结" tone="amber" label="待确认项"><p>原始材料只提供 2.14%→2.9%，没有给出唯一分母。公开版保留结果与待确认标记，不在没有证据时自行定义为“新增用户/活动曝光”或其他公式。</p></Insight>
    <SectionTitle step="02" title="证据等级决定可以说多重的话" />
    <div className="evidence-ladder"><div><EvidenceBadge type="descriptive" /><h3>看见与解释</h3><p>看板趋势、分层、Mix Shift、漏斗。可以定位，但不自动证明因果。</p></div><ArrowRight /><div><EvidenceBadge type="correlation" /><h3>生成候选机制</h3><p>标杆用户行为差异。适合提出假设，不等于产品功能导致留存。</p></div><ArrowRight /><div><EvidenceBadge type="causal" /><h3>验证策略效果</h3><p>随机实验支持“完整策略”的总效果，但不替代机制分解。</p></div><ArrowRight /><div><EvidenceBadge type="decision" /><h3>形成业务动作</h3><p>结合效果大小、护栏、经济性与风险决定上线或继续观察。</p></div></div>
    <SectionTitle step="03" title="决策记录：结论不是一张孤立图" />
    <div className="decision-log">{decisions.map((record, index) => <article key={String(record.decision_id)}><header><span>DECISION {String(index + 1).padStart(2, '0')}</span><strong>{record.case_id === 'referral_growth' ? '老带新页面改版' : '新用户关注引导'}</strong></header>{(['fact', 'interpretation', 'hypothesis', 'action', 'decision', 'limitation'] as const).map((key, itemIndex) => <div key={key}><span>{['事实', '解释', '假设', '动作', '决策', '边界'][itemIndex]}</span><p>{String(record[key])}</p></div>)}</article>)}</div>
    <SectionTitle step="04" title="公开作品集的数据边界" />
    <section className="boundary-grid"><article><Check /><div><strong>项目事实</strong><p>用户提供并经统一口径整理：关键趋势、核心实验设计与已披露结论。</p></div></article><article><Check /><div><strong>脱敏表达</strong><p>DAU规模标准化；真实激励金额改为指数；不出现真实公司与内部系统。</p></div></article><article><Check /><div><strong>模拟明细</strong><p>图表所需UV、非核心功能值、辅助趋势为确定性模拟，并在页面明确标注。</p></div></article><article><Check /><div><strong>不补造</strong><p>留存实验绝对提升、未提供护栏、标杆阈值冲突、裂变率分母均不猜测。</p></div></article></section>
  </>
}

import type { EChartsOption } from 'echarts'
import { CheckCircle2, CircleAlert, GitBranch, Search, Sparkles } from 'lucide-react'
import { axis, Chart, ChartCard, colors, EvidenceBadge, Insight, KpiCard, MethodStrip, PageHeader, SectionTitle, tooltip } from '../components'
import type { PortfolioData } from '../types'

export function RetentionPage({ data }: { data: PortfolioData }) {
  const { trend, segments, path, benchmark, experiment } = data.retention
  const trendOption: EChartsOption = {
    tooltip: { ...tooltip, valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(1)}%` },
    legend: { bottom: 0 }, grid: { left: 52, right: 24, top: 30, bottom: 52 },
    xAxis: { type: 'category', data: [1, 2, 3, 4, 5, 6, 7].map(day => `Cohort ${day}`), ...axis },
    yAxis: { type: 'value', min: 0.36, max: 0.54, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: ['下滑前', '下滑后'].map((period, index) => ({ name: period, type: 'line', smooth: true, symbolSize: 8, lineStyle: { width: 3 }, color: index === 0 ? colors.cobalt : colors.coral, data: trend.filter(row => row.period === period).map(row => row.retention_d1_7_window) })),
  }
  const segmentOption: EChartsOption = {
    tooltip: { ...tooltip, valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(0)}%` },
    legend: { bottom: 0 }, grid: { left: 48, right: 20, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: ['手机', '平板', '其他'], ...axis },
    yAxis: { type: 'value', min: 0.3, max: 0.55, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: ['下滑前', '下滑后'].map((period, index) => ({ name: period, type: 'bar', barMaxWidth: 34, itemStyle: { color: index === 0 ? colors.cobalt : colors.coral, borderRadius: [6, 6, 0, 0] }, data: ['手机', '平板', '其他'].map(segment => segments.find(row => row.period === period && row.segment === segment)?.retention) })),
  }
  const shareOption: EChartsOption = {
    tooltip: { ...tooltip, valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(0)}%` },
    legend: { bottom: 0 }, grid: { left: 48, right: 20, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: ['下滑前', '下滑后'], ...axis },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: ['手机', '平板', '其他'].map((segment, index) => ({ name: segment, type: 'bar', stack: 'mix', itemStyle: { color: [colors.cobalt, colors.amber, '#bec9da'][index] }, data: ['下滑前', '下滑后'].map(period => segments.find(row => row.period === period && row.segment === segment)?.share) })),
  }
  const pathOption: EChartsOption = {
    tooltip: { ...tooltip, valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(1)}%` },
    legend: { bottom: 0 }, grid: { left: 80, right: 20, top: 22, bottom: 55 },
    xAxis: { type: 'category', data: path.map(row => String(row.step_label)), axisLabel: { interval: 0, rotate: 28, color: colors.muted }, ...axis },
    yAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: [{ name: '下滑前', type: 'line', color: colors.cobalt, data: path.map(row => row.baseline_rate), symbolSize: 7 }, { name: '下滑后', type: 'line', color: colors.coral, data: path.map(row => row.current_rate), symbolSize: 7 }],
  }
  const benchmarkOption: EChartsOption = {
    tooltip: { ...tooltip, valueFormatter: (value: unknown) => `${(Number(value) * 100).toFixed(0)}%` },
    legend: { bottom: 0 }, grid: { left: 112, right: 20, top: 25, bottom: 50 },
    yAxis: { type: 'category', data: benchmark.map(row => String(row.feature)), axisLabel: { color: colors.muted }, ...axis }, xAxis: { type: 'value', max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: [{ name: '标杆用户', type: 'bar', itemStyle: { color: colors.teal, borderRadius: [0, 5, 5, 0] }, data: benchmark.map(row => row.benchmark_penetration) }, { name: '非标杆用户', type: 'bar', itemStyle: { color: '#ced6e4', borderRadius: [0, 5, 5, 0] }, data: benchmark.map(row => row.other_penetration) }],
  }

  return <>
    <PageHeader eyebrow="CASE 02 · RETENTION" title="新用户留存：从结构变化到产品机制验证" description="投放带来的新用户留不住时，我先拆人群、再排查路径，保留排除性证据；随后从高频高时用户中寻找候选行为，最后用随机实验把相关性推进到因果验证。" aside={<div className="case-tag"><GitBranch size={20} /><div><span>核心业务指标</span><strong>次 7 日内留存</strong></div></div>} />
    <MethodStrip active={6} />
    <section className="kpi-grid four"><KpiCard label="看板监测异常" value="48% → 41%" note="Day 1–7 窗口留存，下降7pp" tone="coral" /><KpiCard label="设备结构差异" value="约 -10 pp" note="平板用户留存天然低于手机" tone="amber" /><KpiCard label="候选关键行为" value="2.5×" note="标杆用户主页浏览/关注渗透率" tone="blue" /><KpiCard label="策略实验" value="显著提升" note="约30万样本、两周，p < 0.05" tone="teal" /></section>

    <SectionTitle step="01" title="先把留存口径说清楚，再谈为什么下滑" description="这里不是精确第7天留存，而是新增后的第1—7天内至少回来一次；只有完整经历7天观察窗的用户才能进入分母。" />
    <section className="chart-grid wide-left"><ChartCard title="次 7 日内留存监测" subtitle="确定性模拟 Cohort 趋势校准至 48%→41% 的项目叙述" badge="异常发现"><Chart option={trendOption} ariaLabel="新用户次七日内留存趋势" /></ChartCard><div className="definition-card"><EvidenceBadge type="descriptive" /><h3>次 7 日内留存率</h3><div className="formula"><span>新增后 Day 1—7 至少回访一次的用户数</span><i>÷</i><span>完整经历 7 天观察窗的新增用户数</span></div><ul><li>起始事件：成为新用户</li><li>回访事件：再次访问产品</li><li>计数方式：去重用户 UV</li><li>成熟度：未走完窗口不计入分母</li></ul></div></section>

    <SectionTitle step="02" title="分层拆解：总体下降里混入了人群结构变化" description="渠道、设备、品牌、系统、年龄、性别、地域、城市等级依次排查；设备类型给出了最强解释信号。" />
    <section className="chart-grid two"><ChartCard title="设备内留存率" subtitle="平板比手机低约10pp；组内表现没有出现同量级突降" badge="组内表现"><Chart option={segmentOption} ariaLabel="手机平板留存率分组柱状图" /></ChartCard><ChartCard title="新增用户设备构成" subtitle="平板用户占比上升，低留存人群权重增加" badge="Mix Shift"><Chart option={shareOption} ariaLabel="新用户设备占比堆叠柱状图" /></ChartCard></section>
    <Insight title="设备 Mix Shift 可以解释总体留存下滑的重要部分" tone="amber" label="描述性结论"><p>平板用户留存天然低于手机约 10 个百分点，同时平板新增占比增加，拉低了加权后的总体留存。建议在 LTV/CAC 约束内提高手机投放占比，但该建议短期未落地，不能包装为已实现收益。</p></Insight>

    <SectionTitle step="03" title="路径漏斗：用负证据排除“新用户不会用”" description="如果基础使用存在卡点，下载到关注的关键环节应出现同步恶化；但前后两期路径几乎重合。" />
    <ChartCard title="新用户核心路径前后对比" subtitle="下载 → 注册登录 → 首页 → 浏览点击 → 浏览内容 → 互动 → 博主主页 → 关注" badge="排除性证据"><Chart option={pathOption} height={365} ariaLabel="新用户核心路径转化折线图" /></ChartCard>
    <Insight title="现有证据不支持把留存下滑主要归因于基础使用卡点" tone="blue" label="负证据"><p>各环节转化率没有足以解释 7pp 留存下降的明显异常。这个结论并非“产品完全没有体验问题”，而是帮助团队停止在低解释力方向继续消耗分析资源。</p></Insight>

    <SectionTitle step="04" title="标杆用户：从行为差异中生成产品假设" description="用首月活跃天数与日均使用时长定义高频高时标杆用户，比较各项功能渗透率；这一步发现相关性，不宣称因果。" />
    <section className="chart-grid wide-right"><div className="benchmark-method"><EvidenceBadge type="correlation" /><h3>标杆用户定义</h3><div className="quadrant"><div>低频低时</div><div>低频高时</div><div>高频低时</div><div className="selected"><Sparkles size={16} />高频高时</div></div><p>阈值来自业务分布，但口述材料中的 18/20 分钟尚未冻结，因此公开版不补造具体阈值。</p><div className="callout-number"><strong>2.5×</strong><span>主页浏览与关注渗透率<br />标杆 / 非标杆</span></div></div><ChartCard title="标杆与非标杆功能渗透率" subtitle="除2.5倍核心结果外，其余功能值为演示数据" badge="相关性"><Chart option={benchmarkOption} height={410} ariaLabel="标杆用户功能渗透率对比图" /></ChartCard></section>

    <SectionTitle step="05" title="随机实验：把候选行为推进到策略因果" description="实验验证的是“退出页面增加主页浏览与关注引导”的整体策略效果，不把全部提升归因于关注这一单一中介。" />
    <section className="experiment-summary"><div className="experiment-design"><div className="design-head"><EvidenceBadge type="causal" /><span>{String(experiment.experiment_id)}</span></div><h3>退出页增加博主主页与关注引导</h3><div className="arm-grid"><div><span>对照组</span><strong>无额外弹窗</strong><p>保持原有退出体验</p></div><div className="treatment"><span>实验组</span><strong>展示引导弹窗</strong><p>引导浏览主页并关注</p></div></div><ul><li><CheckCircle2 />核心指标：次 7 日内留存率</li><li><CheckCircle2 />约 30 万样本；实验周期两周</li><li><CheckCircle2 />实验组显著提升，p &lt; 0.05</li></ul></div><div className="decision-card"><span>BUSINESS DECISION</span><strong>策略推广，并持续优化</strong><p>从标杆分析的相关性假设出发，通过随机实验验证引导策略能够提升留存。</p><div className="significant-result"><Search size={30} /><b>显著提升</b><i>p &lt; 0.05</i></div><small>边界：用户没有稳定披露绝对提升百分点，公开作品集不补造；实验最后一批用户需完整经历 Day 1—7 后再进入结果。</small></div></section>
    <div className="warning-row"><CircleAlert /><p><strong>因果边界：</strong>实验支持“增加引导”这一策略的总效果；不能因此断言关注是唯一机制，也不能把 2.5× 渗透率差异写成 2.5× 留存提升。</p></div>
  </>
}

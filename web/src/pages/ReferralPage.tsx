import type { EChartsOption } from 'echarts'
import { CheckCircle2, CircleDollarSign, MousePointerClick, Share2, UsersRound } from 'lucide-react'
import { axis, Chart, ChartCard, colors, EvidenceBadge, Insight, KpiCard, MethodStrip, PageHeader, SectionTitle, tooltip } from '../components'
import type { PortfolioData } from '../types'

export function ReferralPage({ data }: { data: PortfolioData }) {
  const versions = data.referral.versions
  const funnel = data.referral.funnel.filter(row => row.version_id === 'simplified_ui')
  const versionOption: EChartsOption = {
    tooltip,
    legend: { bottom: 0, textStyle: { color: colors.muted } },
    grid: { left: 52, right: 30, top: 35, bottom: 55 },
    xAxis: { type: 'category', data: versions.map(row => String(row.label)), axisLabel: { color: colors.muted }, ...axis },
    yAxis: { type: 'value', min: 0.14, max: 0.26, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` }, ...axis },
    series: [{ name: '邀请点击率', type: 'line', smooth: true, symbolSize: 11, lineStyle: { width: 4, color: colors.cobalt }, itemStyle: { color: colors.cobalt }, areaStyle: { color: 'rgba(58,115,255,.12)' }, data: versions.map(row => row.invite_click_rate) }],
  }
  const funnelOption: EChartsOption = {
    tooltip: { trigger: 'item', formatter: '{b}<br/>模拟UV：{c}' },
    series: [{ type: 'funnel', top: 18, bottom: 15, left: '8%', width: '84%', minSize: '18%', maxSize: '100%', sort: 'none', gap: 3, label: { show: true, position: 'inside', formatter: '{b}\n{c}', color: '#fff', fontWeight: 600 }, itemStyle: { borderColor: '#fff', borderWidth: 2 }, data: funnel.map((row, index) => ({ name: String(row.step_label), value: Number(row.users), itemStyle: { color: [colors.cobalt, '#4b89ff', colors.violet, colors.teal, '#26c6b7', '#60d6c9'][index] } })) }],
  }

  return <>
    <PageHeader eyebrow="CASE 01 · ACQUISITION" title="老带新增长：从激励加码到页面断点定位" description="外部拉新供给承压时，我没有停在“裂变率上涨”，而是沿邀请链路定位可控断点，用随机实验验证改版，并用首月 LTV/CAC 决定是否值得继续投入。" aside={<div className="case-tag"><UsersRound size={20} /><div><span>最终业务指标</span><strong>拉新用户数</strong></div></div>} />
    <MethodStrip active={6} />

    <section className="kpi-grid four">
      <KpiCard label="裂变率" value="2.14% → 2.90%" note="策略方向有效；分母口径待最终冻结" tone="blue" />
      <KpiCard label="异常断点" value="约21% → 17%" note="玩法升级后邀请点击率下滑" tone="coral" />
      <KpiCard label="A/B 实验结果" value="17% → 23.5%" note="两周、百万级脱敏样本，p < 0.05" tone="teal" />
      <KpiCard label="首月 LTV/CAC" value="2.18× > 1.90×" note="高于外部投放基准" tone="amber" />
    </section>

    <SectionTitle step="01" title="先搭指标树：把业务结果与页面动作分开" description="邀请点击率是实验主指标，拉新用户数才是最终业务结果；经济性是能否扩大投入的决策护栏。" />
    <div className="metric-tree">
      <div className="tree-root"><span>公司级背景</span><strong>DAU 目标差距</strong><small>公开版标准化：81.25 / 100</small></div>
      <div className="tree-line" />
      <div className="tree-branches">
        <div><UsersRound /><span>结果指标</span><strong>拉新用户数</strong><small>活动最终带来的有效新用户</small></div>
        <div><MousePointerClick /><span>机制指标</span><strong>邀请点击率</strong><small>本次页面改版的直接作用点</small></div>
        <div><Share2 /><span>诊断指标</span><strong>分享成功率</strong><small>约95%，用于排除分享链路异常</small></div>
        <div><CircleDollarSign /><span>经济护栏</span><strong>首月 LTV/CAC</strong><small>价值/获客成本，不等于净ROI</small></div>
      </div>
    </div>

    <SectionTitle step="02" title="沿版本变化定位断点，而不是只看一张漏斗" description="激励和留存玩法增加后，裂变率提升，但邀请动作反而受损。版本对比把问题收敛到活动页面的信息与 CTA 位置。" />
    <section className="chart-grid two">
      <ChartCard title="三次版本迭代：邀请点击率先降后升" subtitle="约23%为初始版本叙述范围内的展示点；17%与23.5%为实验前后口径" badge="版本诊断"><Chart option={versionOption} ariaLabel="三次版本邀请点击率折线图" /></ChartCard>
      <ChartCard title="简化版邀请漏斗" subtitle="UV 为确定性模拟，仅用于展示漏斗计算与看板交互" badge="演示数据"><Chart option={funnelOption} ariaLabel="老带新活动漏斗图" /></ChartCard>
    </section>
    <Insight title="主断点在“发现并点击邀请”，而不是后续微信分享" tone="coral" label="定位结论"><p>新版信息增多、重点不聚焦，且邀请按钮放到第二页。与此同时，分享成功率仍约 95%，这条负证据帮助排除“分享链路不稳定”的解释。</p></Insight>

    <SectionTitle step="03" title="把产品反馈翻译成可证伪假设" description="与产品、用研共同确认页面复杂度问题后，策略不是继续加奖励，而是降低行动发现成本。" />
    <div className="hypothesis-flow"><div><span>FACT</span><strong>邀请点击率降至17%</strong><p>玩法升级后发生，分享成功率稳定</p></div><i>→</i><div><span>INTERPRETATION</span><strong>邀请前链路受阻</strong><p>不是微信分享能力下降</p></div><i>→</i><div><span>HYPOTHESIS</span><strong>CTA 发现成本过高</strong><p>内容复杂且按钮位于第二页</p></div><i>→</i><div><span>ACTION</span><strong>简化并移回首屏</strong><p>用随机实验检验页面机制</p></div></div>

    <SectionTitle step="04" title="实验验证与价值决策" description="先判断改版是否提升关键动作，再确认增加激励后单位经济性仍在可接受区间。" />
    <section className="experiment-summary">
      <div className="experiment-design"><div className="design-head"><EvidenceBadge type="causal" /><span>referral_ui_simplification_v2</span></div><h3>简化页面、邀请按钮放回首屏</h3><div className="arm-grid"><div><span>对照组</span><strong>原复杂活动页</strong><p>邀请按钮在第二页</p></div><div className="treatment"><span>实验组</span><strong>首屏 CTA 简化版</strong><p>信息聚焦，第一屏完成邀请</p></div></div><ul><li><CheckCircle2 />核心指标：邀请点击率</li><li><CheckCircle2 />百万级脱敏样本；周期：两周</li><li><CheckCircle2 />17.0% → 23.5%，p &lt; 0.05</li></ul></div>
      <div className="decision-card"><span>BUSINESS DECISION</span><strong>上线，并在该版本上持续迭代</strong><p>页面改版达到统计显著和业务显著；新增激励后，老带新首月 LTV/CAC 为 2.18，高于外部投放 1.90 的基准。</p><div><b>2.18×</b><i>老带新</i><b>1.90×</b><i>外部投放</i></div><small>边界：首月价值成本比不是完整生命周期价值，也不能写成净 ROI 218%。</small></div>
    </section>
    <Insight title="这个项目体现的不是“会做 Z 检验”，而是知道何时继续投钱" tone="teal" label="能力沉淀"><p>从业务目标出发，区分结果、机制与护栏；用负证据缩小问题；把产品反馈写成实验假设；最后用单位经济性约束增长。这套链路可以复用到优惠券、召回、会员转化等增长场景。</p></Insight>
  </>
}

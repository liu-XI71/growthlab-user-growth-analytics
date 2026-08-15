import type { EChartsOption } from 'echarts'
import { BarChart, FunnelChart, LineChart, RadarChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import ReactEChartsCore from 'echarts-for-react/esm/core'
import { SVGRenderer } from 'echarts/renderers'
import { ArrowRight, CheckCircle2, CircleAlert, Database, FlaskConical, Lightbulb, Target } from 'lucide-react'
import type { ReactNode } from 'react'

echarts.use([BarChart, FunnelChart, LineChart, RadarChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer])

export const colors = {
  navy: '#071426', cobalt: '#3a73ff', teal: '#00b8a9', amber: '#f6ad3c', coral: '#ff6b6b', ink: '#172033', muted: '#738097', grid: '#e9eef7', pale: '#f5f8fd', violet: '#7c66ff',
}

export function Chart({ option, height = 340, ariaLabel }: { option: EChartsOption; height?: number; ariaLabel: string }) {
  return <ReactEChartsCore echarts={echarts} option={{ animationDuration: 650, textStyle: { fontFamily: 'Inter, PingFang SC, Microsoft YaHei, sans-serif', color: colors.ink }, ...option }} style={{ height }} opts={{ renderer: 'svg' }} aria-label={ariaLabel} />
}

export function PageHeader({ eyebrow, title, description, aside }: { eyebrow: string; title: string; description: string; aside?: ReactNode }) {
  return <section className="page-header"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{aside && <div className="header-aside">{aside}</div>}</section>
}

export function SectionTitle({ step, title, description }: { step?: string; title: string; description?: string }) {
  return <div className="section-title">{step && <span>{step}</span>}<div><h2>{title}</h2>{description && <p>{description}</p>}</div></div>
}

export function KpiCard({ label, value, note, tone = 'blue' }: { label: string; value: string; note: string; tone?: 'blue' | 'teal' | 'amber' | 'coral' }) {
  return <article className={`kpi-card tone-${tone}`}><p>{label}</p><strong>{value}</strong><small>{note}</small></article>
}

export function ChartCard({ title, subtitle, children, badge }: { title: string; subtitle?: string; children: ReactNode; badge?: string }) {
  return <article className="chart-card"><header><div><h3>{title}</h3>{subtitle && <p>{subtitle}</p>}</div>{badge && <span className="card-badge">{badge}</span>}</header>{children}</article>
}

export function Insight({ title, children, tone = 'blue', label = '分析判断' }: { title: string; children: ReactNode; tone?: 'blue' | 'teal' | 'amber' | 'coral'; label?: string }) {
  const Icon = tone === 'amber' ? CircleAlert : tone === 'teal' ? CheckCircle2 : Lightbulb
  return <article className={`insight tone-${tone}`}><div className="insight-icon"><Icon size={18} /></div><div><span>{label}</span><h3>{title}</h3><div>{children}</div></div></article>
}

export function MethodStrip({ active }: { active: number }) {
  const steps = ['监测异常', '定义指标', '拆解定位', '保留负证据', '提出假设', '实验验证', '价值决策']
  return <div className="method-strip" aria-label="增长分析闭环">{steps.map((step, index) => <div key={step} className={index <= active ? 'active' : ''}><span>{index + 1}</span><p>{step}</p>{index < steps.length - 1 && <ArrowRight size={14} />}</div>)}</div>
}

export function EvidenceBadge({ type }: { type: 'descriptive' | 'correlation' | 'causal' | 'decision' }) {
  const map = { descriptive: ['描述性证据', Database], correlation: ['相关性证据', Lightbulb], causal: ['因果性证据', FlaskConical], decision: ['业务决策', Target] } as const
  const [label, Icon] = map[type]
  return <span className={`evidence evidence-${type}`}><Icon size={13} />{label}</span>
}

export const axis = { axisLine: { lineStyle: { color: '#d8e0ed' } }, axisTick: { show: false }, splitLine: { lineStyle: { color: colors.grid } } }

export const tooltip = { trigger: 'axis' as const, backgroundColor: '#071426', borderWidth: 0, textStyle: { color: '#fff' }, padding: 12 }

export function EmptyState({ message }: { message: string }) { return <div className="empty-state">{message}</div> }

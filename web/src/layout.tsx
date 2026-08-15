import { Activity, BookOpenCheck, ChevronRight, FlaskConical, GitBranch, Menu, Network, Scale, Target, X } from 'lucide-react'
import { useState, type ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

const items = [
  ['/', '业务总览', Activity],
  ['/referral', '老带新增长', Network],
  ['/retention', '新用户留存', GitBranch],
  ['/experiments', '实验中心', FlaskConical],
  ['/value', '价值与渠道', Scale],
  ['/governance', '指标治理', BookOpenCheck],
] as const

export function Layout({ meta, children }: { meta: { projectName: string; projectNameZh: string; dataBoundary: string }; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return <div className="app-shell">
    <button className="mobile-menu" onClick={() => setOpen(!open)} aria-label="打开导航">{open ? <X /> : <Menu />}</button>
    <aside className={open ? 'sidebar open' : 'sidebar'}>
      <div className="brand"><div className="brand-mark"><Target size={22} /></div><div><strong>GADP</strong><span>Growth Analytics</span></div></div>
      <div className="brand-title"><p>{meta.projectNameZh}</p><span>{meta.projectName}</span></div>
      <nav>{items.map(([path, label, Icon]) => <NavLink key={path} to={path} end={path === '/'} onClick={() => setOpen(false)} className={({ isActive }) => isActive ? 'active' : ''}><Icon size={18} /><span>{label}</span><ChevronRight className="chevron" size={15} /></NavLink>)}</nav>
      <div className="sidebar-note"><span>PUBLIC PORTFOLIO</span><p>方法论与项目事实可追溯，演示数据不代表任何雇主生产数据。</p></div>
    </aside>
    <div className="content-shell"><div className="topbar"><span className="status-dot" />确定性脱敏演示数据 <span className="topbar-separator" /> 面试官可直接浏览，无需安装</div><main>{children}</main><footer><span>{meta.dataBoundary}</span><a href="https://github.com/liu-XI71/growth-analytics-decision-platform" target="_blank" rel="noreferrer">查看源码与口径说明</a></footer></div>
    {open && <button className="overlay" onClick={() => setOpen(false)} aria-label="关闭导航" />}
  </div>
}

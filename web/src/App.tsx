import { useEffect, useLayoutEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { loadPortfolio } from './data'
import { Layout } from './layout'
import { ExperimentPage, GovernancePage, OverviewPage, ValuePage } from './pages/PlatformPages'
import { ReferralPage } from './pages/ReferralPage'
import { RetentionPage } from './pages/RetentionPage'
import type { PortfolioData } from './types'

function ScrollToTop() {
  const { key, pathname } = useLocation()

  useLayoutEffect(() => {
    if (!('scrollRestoration' in window.history)) return
    const previous = window.history.scrollRestoration
    window.history.scrollRestoration = 'manual'
    return () => {
      window.history.scrollRestoration = previous
    }
  }, [])

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'auto' })
    const frame = window.requestAnimationFrame(() => window.scrollTo(0, 0))
    return () => window.cancelAnimationFrame(frame)
  }, [key, pathname])

  return null
}

export default function App() {
  const [data, setData] = useState<PortfolioData | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadPortfolio().then(setData).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : '数据加载失败'))
  }, [])

  if (error) return <main className="load-state"><strong>页面暂时无法加载</strong><p>{error}</p></main>
  if (!data) return <main className="load-state"><div className="loader" /><strong>正在加载增长分析作品集…</strong></main>

  return <Layout meta={data.meta}>
    <ScrollToTop />
    <Routes>
      <Route path="/" element={<OverviewPage data={data} />} />
      <Route path="/referral" element={<ReferralPage data={data} />} />
      <Route path="/retention" element={<RetentionPage data={data} />} />
      <Route path="/experiments" element={<ExperimentPage data={data} />} />
      <Route path="/value" element={<ValuePage data={data} />} />
      <Route path="/governance" element={<GovernancePage data={data} />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  </Layout>
}

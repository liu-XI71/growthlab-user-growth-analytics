import type { PortfolioData } from './types'

let cached: Promise<PortfolioData> | undefined

export function loadPortfolio(): Promise<PortfolioData> {
  if (!cached) {
    const staticUrl = `${import.meta.env.BASE_URL}data/portfolio.json`
    const apiBase = String(import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
    const read = async (url: string) => {
      const response = await fetch(url)
      if (!response.ok) throw new Error(`数据加载失败：${response.status}`)
      return response.json() as Promise<PortfolioData>
    }
    cached = apiBase ? read(`${apiBase}/portfolio`).catch(() => read(staticUrl)) : read(staticUrl)
  }
  return cached
}

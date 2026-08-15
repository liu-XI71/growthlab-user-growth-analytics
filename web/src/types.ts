export type Dict = Record<string, string | number | null>

export interface PortfolioData {
  meta: { projectName: string; projectNameZh: string; version: string; dataBoundary: string }
  cases: Dict[]
  businessKpis: Dict[]
  decisionLoop: Dict[]
  referral: { versions: Dict[]; funnel: Dict[]; experiment: Dict }
  retention: { trend: Dict[]; segments: Dict[]; path: Dict[]; benchmark: Dict[]; experiment: Dict }
  experiments: Dict[]
  metricContracts: Dict[]
  decisions: Dict[]
}

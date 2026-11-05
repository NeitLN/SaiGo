// Cột kết quả: bảng so sánh Dijkstra / A* (docs/DEMO.md mục 1.3, nhãn bắt buộc ở mục 1.4).
import { ALGORITHM_LABEL, escapeHtml, type Algorithm, type AlgorithmResult, type RouteResponse } from './api'
import { COLORS } from './layers'

const ALGOS: Algorithm[] = ['dijkstra', 'astar']

function num(x: number, digits = 1): string {
  return x.toLocaleString('vi-VN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

function cost(r: AlgorithmResult): string {
  if (r.status !== 'ok' || r.cost_s === null) return 'Không có đường'
  return `${num(r.cost_s)} s (${num(r.cost_s / 60)} phút)`
}

function distance(r: AlgorithmResult): string {
  return r.status !== 'ok' || r.distance_m === null ? '—' : `${num(r.distance_m, 0)} m`
}

const ROWS: [string, (r: AlgorithmResult) => string][] = [
  ['Thời gian di chuyển ước tính (theo kịch bản)', cost],
  ['Quãng đường', distance],
  ['Số node mở rộng', (r) => num(r.expanded, 0)],
  ['Thời gian tính toán', (r) => `${num(r.runtime_ms, 2)} ms`],
]

export function renderResults(el: HTMLElement, res: RouteResponse, scenarioLabel?: string) {
  const algos = ALGOS.filter((a) => res.results[a])
  const head = algos
    .map((a) => `<th><span class="swatch" style="background:${COLORS[a]}"></span>${ALGORITHM_LABEL[a]}</th>`)
    .join('')
  const body = ROWS.map(([label, f]) => `<tr><th scope="row">${label}</th>${algos.map((a) => `<td>${f(res.results[a]!)}</td>`).join('')}</tr>`).join('')
  const match = res.costs_match === true ? 'có' : res.costs_match === false ? '<strong class="bad">không</strong>' : '—'
  el.innerHTML = `
    ${scenarioLabel ? `<p class="scenario-used">Kịch bản: <strong>${escapeHtml(scenarioLabel)}</strong></p>` : ''}
    <table class="compare">
      <thead><tr><th></th>${head}</tr></thead>
      <tbody>${body}</tbody>
    </table>
    <p class="match">Chi phí trùng khớp: ${match}</p>
    ${(res.warnings ?? []).map((w) => `<p class="warning">${escapeHtml(w)}</p>`).join('')}
  `
}

export function renderEmpty(el: HTMLElement, text: string) {
  el.innerHTML = `<p class="muted">${text}</p>`
}

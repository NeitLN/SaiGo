import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './style.css'
import { BASELINE, getDataset, getHealth, postRoute, type LatLon, type RouteResponse, type Scenario } from './api'
import { MapLayers } from './layers'
import { renderEmpty, renderResults } from './panel'

const app = document.querySelector<HTMLDivElement>('#app')!
app.innerHTML = `
  <header class="topbar">
    <strong>SaiGo</strong>
    <span class="subtitle">Lập kế hoạch lộ trình giao hàng</span>
    <span id="server-status" class="status">Đang kiểm tra server…</span>
  </header>
  <main class="layout">
    <aside class="panel controls">
      <h2>Tìm đường hai điểm</h2>
      <p id="hint" class="hint"></p>
      <dl class="points">
        <dt>Điểm đi</dt><dd id="source-text">—</dd>
        <dt>Điểm đến</dt><dd id="target-text">—</dd>
      </dl>
      <label class="field">Kịch bản
        <select id="scenario"></select>
      </label>
      <p id="scenario-note" class="muted small" hidden></p>
      <div class="buttons">
        <button id="btn-route" class="primary" disabled>Tìm đường</button>
        <button id="btn-swap" disabled>Đảo chiều</button>
        <button id="btn-clear">Xóa</button>
      </div>
      <p id="busy" class="busy" hidden>Đang tính…</p>
      <p id="message" class="message" hidden></p>
    </aside>
    <div id="map"></div>
    <aside class="panel results">
      <h2>Kết quả đo được</h2>
      <div id="results"></div>
    </aside>
  </main>
`

const $ = <T extends HTMLElement>(id: string) => document.getElementById(id) as T
const btnRoute = $<HTMLButtonElement>('btn-route')
const btnSwap = $<HTMLButtonElement>('btn-swap')
const scenarioSelect = $<HTMLSelectElement>('scenario')

// Tâm quanh chợ Bến Thành (cùng tâm với data/config/areas.json).
const map = L.map('map').setView([10.7725, 106.7], 16)

// Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19,
  attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
}).addTo(map)

const layers = new MapLayers(map)

let source: LatLon | null = null
let target: LatLon | null = null
let shown: RouteResponse | null = null
let pending: AbortController | null = null
let requestId = 0
let scenarios: Scenario[] = [BASELINE]
let scenario: Scenario = BASELINE

function fmt(p: LatLon | null): string {
  return p ? `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}` : '—'
}

function show(el: HTMLElement, text: string | null) {
  el.hidden = text === null
  if (text !== null) el.textContent = text
}

function cancelPending() {
  pending?.abort()
  pending = null
  requestId++
  $('busy').hidden = true
}

function refresh() {
  $('source-text').textContent = fmt(source)
  $('target-text').textContent = fmt(target)
  btnRoute.disabled = !(source && target)
  btnSwap.disabled = !(source && target)
  $('hint').innerHTML = !source
    ? 'Bấm lên bản đồ để chọn <strong>điểm đi</strong>.'
    : !target
      ? 'Bấm để chọn <strong>điểm đến</strong>.'
      : 'Bấm <strong>Tìm đường</strong>. Bấm lên bản đồ lần nữa để chọn lại từ đầu.'
}

function clearResult() {
  cancelPending()
  shown = null
  layers.clearRoutes()
  renderEmpty($('results'), 'Chưa có kết quả.')
  show($('message'), null)
}

async function findRoute() {
  if (!source || !target) return
  cancelPending()
  const id = requestId
  pending = new AbortController()
  $('busy').hidden = false
  show($('message'), null)
  try {
    const used = scenario
    const res = await postRoute(
      { source, target, algorithms: ['dijkstra', 'astar'], scenario_id: used.id },
      pending.signal,
    )
    if (id !== requestId) return // đã có request mới hơn
    shown = res
    layers.setSnapped(res)
    layers.drawRoutes(res)
    renderResults($('results'), res, used.label)
    // Không vẽ đường thẳng nối hai điểm khi không có đường.
    if (Object.values(res.results).some((r) => r?.status === 'no_path')) {
      show($('message'), 'Không có đường đi giữa hai điểm này trong kịch bản hiện tại.')
    }
  } catch (err) {
    if (id !== requestId || (err as Error).name === 'AbortError') return
    shown = null
    layers.clearRoutes()
    layers.setPoints(source, target)
    renderEmpty($('results'), 'Chưa có kết quả.')
    show($('message'), `Lỗi: ${(err as Error).message}`)
  } finally {
    if (id === requestId) $('busy').hidden = true
  }
}

map.on('click', (e: L.LeafletMouseEvent) => {
  const p = { lat: e.latlng.lat, lon: e.latlng.lng }
  if (!source || target) {
    // Lần đầu, hoặc đã có đủ hai điểm: bắt đầu lại từ điểm đi.
    clearResult()
    source = p
    target = null
  } else {
    target = p
  }
  layers.setPoints(source, target)
  refresh()
})

btnRoute.addEventListener('click', () => void findRoute())

btnSwap.addEventListener('click', () => {
  ;[source, target] = [target, source]
  layers.setPoints(source, target)
  refresh()
  if (shown) void findRoute() // đang có kết quả thì tìm lại theo chiều mới
  else clearResult()
})

$('btn-clear').addEventListener('click', () => {
  clearResult()
  source = target = null
  layers.clear()
  refresh()
})

function fillScenarios(list: Scenario[]) {
  scenarios = list.length ? list : [BASELINE]
  // Option + textContent: nhãn từ API không được chèn thẳng vào HTML.
  scenarioSelect.replaceChildren(...scenarios.map((s) => new Option(s.label || s.id, s.id)))
  // Giữ kịch bản đang chọn nếu còn (danh sách có thể về sau khi đã có kết quả); mặc định là baseline.
  scenario = scenarios.find((s) => s.id === scenario.id) ?? scenarios.find((s) => s.id === 'baseline') ?? scenarios[0]
  scenarioSelect.value = scenario.id
  layers.setZones(scenario)
}

// Đổi kịch bản: vẽ lại vùng ùn tắc; nếu đang có kết quả thì tìm lại.
scenarioSelect.addEventListener('change', () => {
  scenario = scenarios.find((s) => s.id === scenarioSelect.value) ?? BASELINE
  layers.setZones(scenario)
  // Tìm lại cả khi request trước còn đang chạy; findRoute tự hủy request cũ.
  if (shown || pending) void findRoute()
})

refresh()
renderEmpty($('results'), 'Chưa có kết quả.')
fillScenarios([BASELINE])
getDataset()
  .then((d) => {
    if (d) fillScenarios(d.scenarios)
    else show($('scenario-note'), 'API chưa có /api/dataset (T51): chỉ dùng được kịch bản cơ sở.')
  })
  .catch((err) => show($('scenario-note'), `Không tải được danh sách kịch bản: ${(err as Error).message}`))

const statusEl = $('server-status')
getHealth()
  .then((h) => {
    statusEl.textContent = h.dataset_loaded ? `Server sẵn sàng · dataset ${h.dataset_id ?? ''}` : 'Server chạy, chưa nạp dataset'
  })
  .catch(() => {
    statusEl.textContent = 'Không kết nối được server'
  })

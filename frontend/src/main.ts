import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import './style.css'
import { BASELINE, getDataset, getHealth, postRoute, type LatLon, type RouteResponse, type Scenario } from './api'
import { MapLayers, type ClosedSegment } from './layers'
import { renderEmpty, renderResults } from './panel'
import { PRESETS, TourMode } from './tour'

const app = document.querySelector<HTMLDivElement>('#app')!
app.innerHTML = `
  <header class="topbar">
    <strong>SaiGo</strong>
    <span class="subtitle">Lập kế hoạch lộ trình giao hàng</span>
    <span id="server-status" class="status">Đang kiểm tra server…</span>
  </header>
  <main class="layout">
    <aside class="panel controls">
      <div class="mode-tabs" role="tablist">
        <button id="tab-route" class="tab active" role="tab">Tìm đường hai điểm</button>
        <button id="tab-tour" class="tab" role="tab">Tour</button>
      </div>
      <label class="field">Kịch bản
        <select id="scenario"></select>
      </label>
      <p id="scenario-note" class="muted small" hidden></p>
      <div id="route-controls">
      <p id="hint" class="hint"></p>
      <dl class="points">
        <dt>Điểm đi</dt><dd id="source-text">—</dd>
        <dt>Điểm đến</dt><dd id="target-text">—</dd>
      </dl>
      <div class="buttons">
        <button id="btn-route" class="primary" disabled>Tìm đường</button>
        <button id="btn-swap" disabled>Đảo chiều</button>
        <button id="btn-clear">Xóa</button>
      </div>
      <div class="buttons closures">
        <button id="btn-reopen" disabled>Mở lại tất cả</button>
        <span id="closed-text" class="muted small">Chưa đóng đoạn nào</span>
      </div>
      <p id="busy" class="busy" hidden>Đang tính…</p>
      <p id="message" class="message" hidden></p>
      </div>
      <div id="tour-controls" hidden>
        <p id="tour-hint" class="hint"></p>
        <label class="field">Case demo
          <select id="tour-preset"></select>
        </label>
        <ol id="tour-points" class="tour-points"></ol>
        <div class="buttons">
          <button id="btn-plan" class="primary" disabled>Lập tour</button>
          <button id="btn-tour-clear">Xóa</button>
        </div>
        <p id="tour-busy" class="busy" hidden>Đang lập tour…</p>
        <p id="tour-message" class="message" hidden></p>
      </div>
    </aside>
    <div id="map"></div>
    <aside class="panel results">
      <h2>Kết quả đo được</h2>
      <div id="results"></div>
      <div id="tour-results" hidden></div>
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
const tour = new TourMode(map, {
  list: $('tour-points'),
  hint: $('tour-hint'),
  btnPlan: $<HTMLButtonElement>('btn-plan'),
  busy: $('tour-busy'),
  message: $('tour-message'),
  results: $('tour-results'),
}, () => scenario.id)
let mode: 'route' | 'tour' = 'route'

let source: LatLon | null = null
let target: LatLon | null = null
let shown: RouteResponse | null = null
let pending: AbortController | null = null
let requestId = 0
let scenarios: Scenario[] = [BASELINE]
let scenario: Scenario = BASELINE
let closed: ClosedSegment[] = []

function blockedIds(): number[] {
  return [...new Set(closed.flatMap((c) => c.ids))].sort((a, b) => a - b)
}

function refreshClosures() {
  layers.setClosures(closed)
  $<HTMLButtonElement>('btn-reopen').disabled = closed.length === 0
  $('closed-text').textContent = closed.length
    ? `Đã đóng ${closed.length} đoạn (${blockedIds().length} cạnh có hướng)`
    : 'Chưa đóng đoạn nào'
}

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
      : shown?.results.dijkstra?.status === 'ok'
        ? 'Bấm vào một đoạn <strong>trên tuyến</strong> để đóng đoạn đó. Bấm chỗ khác để chọn lại từ đầu.'
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
      { source, target, algorithms: ['dijkstra', 'astar'], scenario_id: used.id, blocked_edge_ids: blockedIds() },
      pending.signal,
    )
    if (id !== requestId) return // đã có request mới hơn
    shown = res
    layers.setSnapped(res)
    layers.drawRoutes(res)
    layers.setClickableSegments(res, closeSegment)
    renderResults($('results'), res, used.label)
    refresh()
    // Không vẽ đường thẳng nối hai điểm khi không có đường.
    if (Object.values(res.results).some((r) => r?.status === 'no_path')) {
      show($('message'), closed.length
        ? 'Không còn đường đi: các đoạn đã đóng chặn hết lối giữa hai điểm. Bấm "Mở lại tất cả" để thử lại.'
        : 'Không có đường đi giữa hai điểm này trong kịch bản hiện tại.')
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
  if (mode === 'tour') {
    tour.addPoint(p)
    return
  }
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

// Đóng một đoạn trên tuyến (cả cạnh đối nếu là đường hai chiều) rồi tìm lại.
function closeSegment(seg: ClosedSegment) {
  if (seg.ids.every((id) => blockedIds().includes(id))) return
  closed = [...closed, seg]
  refreshClosures()
  void findRoute()
}

$('btn-reopen').addEventListener('click', () => {
  closed = []
  refreshClosures()
  if (source && target && (shown || pending)) void findRoute()
})

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
  closed = []
  refreshClosures()
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
  if (mode === 'tour') {
    tour.scenarioChanged()
    return
  }
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

// ---------- Chế độ tour (T73) ----------

const presetSelect = $<HTMLSelectElement>('tour-preset')
presetSelect.replaceChildren(
  new Option(PRESETS.length ? '— Chọn case —' : 'Chưa có data/demo/cases.json (T55)', ''),
  ...PRESETS.map((p) => new Option(p.label, p.id)),
)
presetSelect.disabled = PRESETS.length === 0
presetSelect.addEventListener('change', () => {
  const preset = PRESETS.find((p) => p.id === presetSelect.value)
  if (preset) tour.loadPreset(preset)
})
$('btn-plan').addEventListener('click', () => void tour.plan())
$('btn-tour-clear').addEventListener('click', () => {
  presetSelect.value = ''
  tour.clear()
})

// Đổi chế độ: xóa kết quả của chế độ cũ để bản đồ chỉ có lớp của chế độ đang dùng.
function setMode(next: 'route' | 'tour') {
  if (next === mode) return
  mode = next
  $('tab-route').classList.toggle('active', mode === 'route')
  $('tab-tour').classList.toggle('active', mode === 'tour')
  $('route-controls').hidden = mode !== 'route'
  $('results').hidden = mode !== 'route'
  $('tour-controls').hidden = mode !== 'tour'
  $('tour-results').hidden = mode !== 'tour'
  if (mode === 'tour') {
    $('btn-clear').click()
  } else {
    presetSelect.value = ''
    tour.clear()
  }
}
$('tab-route').addEventListener('click', () => setMode('route'))
$('tab-tour').addEventListener('click', () => setMode('tour'))

// Chế độ tour (T73): kho + điểm giao, 3 thẻ Thứ tự nhập / NN / NN + 2-opt (docs/DEMO.md mục 1.1, 1.3).
import L from 'leaflet'
import { escapeHtml, postTour, TOUR_LABEL, type LatLon, type TourMethod, type TourResponse } from './api'
import { toLatLngs } from './layers'

const METHODS: TourMethod[] = ['input', 'nearest_neighbor', 'nearest_neighbor_2opt']
const MAX_STOPS = 9 // backend dùng Held–Karp làm đối chứng tới 10 điểm (kể cả kho)

interface NamedPoint extends LatLon {
  name?: string
}

export interface TourPreset {
  id: string
  label: string
  depot: NamedPoint
  stops: NamedPoint[]
}

// Preset lấy từ data/demo/cases.json (T55). Chưa có file thì glob trả rỗng, chế độ tour vẫn dùng được bằng cách bấm.
const caseFiles = import.meta.glob<{ cases: (TourPreset & { mode: string })[] }>(
  '../../data/demo/cases.json', { eager: true, import: 'default' })
export const PRESETS: TourPreset[] = Object.values(caseFiles)
  .flatMap((f) => f.cases.filter((c) => c.mode === 'tour'))
  .map(({ id, label, depot, stops }) => ({ id, label, depot, stops }))

function num(x: number, digits = 1): string {
  return x.toLocaleString('vi-VN', { maximumFractionDigits: digits, minimumFractionDigits: digits })
}

export interface TourElements {
  list: HTMLElement
  hint: HTMLElement
  btnPlan: HTMLButtonElement
  busy: HTMLElement
  message: HTMLElement
  results: HTMLElement
}

export class TourMode {
  private layer = L.layerGroup()
  private points: NamedPoint[] = []
  private res: TourResponse | null = null
  private selected: TourMethod | null = null
  private pending: AbortController | null = null
  private requestId = 0
  private el: TourElements
  private scenarioId: () => string

  constructor(map: L.Map, el: TourElements, scenarioId: () => string) {
    this.layer.addTo(map)
    this.el = el
    this.scenarioId = scenarioId
    this.render()
  }

  // Bấm bản đồ: điểm đầu là kho, sau đó là điểm giao theo thứ tự nhập.
  addPoint(p: LatLon) {
    if (this.points.length > MAX_STOPS) {
      this.show(`Tối đa kho + ${MAX_STOPS} điểm giao.`)
      return
    }
    this.points.push(p)
    this.dropResult()
  }

  loadPreset(preset: TourPreset) {
    this.points = [preset.depot, ...preset.stops]
    this.dropResult()
  }

  clear() {
    this.points = []
    this.dropResult()
  }

  // Đổi kịch bản hoặc thoát chế độ tour: bỏ kết quả cũ (chi phí không còn đúng).
  dropResult() {
    this.pending?.abort()
    this.pending = null
    this.requestId++
    this.res = null
    this.selected = null
    this.show(null)
    this.el.busy.hidden = true
    this.render()
  }

  // Đổi kịch bản: đang có tour thì lập lại theo kịch bản mới, chưa có thì thôi.
  scenarioChanged() {
    if (this.res || this.pending) void this.plan()
  }

  async plan() {
    if (this.points.length < 2) return
    this.dropResult()
    const id = this.requestId
    this.pending = new AbortController()
    this.el.busy.hidden = false
    try {
      const [depot, ...stops] = this.points
      const res = await postTour(
        { depot: { lat: depot.lat, lon: depot.lon }, stops: stops.map(({ lat, lon }) => ({ lat, lon })),
          scenario_id: this.scenarioId() },
        this.pending.signal)
      if (id !== this.requestId) return
      this.res = res
      if (res.status !== 'ok') {
        // Không vẽ tour khi có cặp điểm không tới được.
        const pairs = res.unreachable.map(([i, j]) => `${this.name(i)} → ${this.name(j)}`).join(', ')
        this.show(`Không lập được tour theo mô hình: không có đường ${pairs}.`)
      } else {
        this.selected = res.chosen ?? 'nearest_neighbor_2opt'
      }
    } catch (err) {
      if (id !== this.requestId || (err as Error).name === 'AbortError') return
      this.show(`Lỗi: ${(err as Error).message}`)
    } finally {
      if (id === this.requestId) this.el.busy.hidden = true
    }
    this.render()
  }

  select(method: TourMethod) {
    if (!this.res?.plans[method]) return
    this.selected = method
    this.render()
  }

  private name(i: number): string {
    const p = this.points[i]
    const base = i === 0 ? 'Kho' : `Điểm ${i}`
    return p?.name ? `${base} (${p.name})` : base
  }

  private show(text: string | null) {
    this.el.message.hidden = text === null
    if (text !== null) this.el.message.textContent = text
  }

  private render() {
    this.renderList()
    this.renderMap()
    this.renderCards()
    this.el.btnPlan.disabled = this.points.length < 2
    this.el.hint.innerHTML = this.points.length === 0
      ? 'Bấm lên bản đồ để đặt <strong>kho</strong>, hoặc chọn case demo.'
      : `Bấm để thêm <strong>điểm giao</strong> (tối đa ${MAX_STOPS}), rồi bấm <strong>Lập tour</strong>.`
  }

  private renderList() {
    const items = this.points.map((p, i) =>
      `<li><span class="badge${i === 0 ? ' depot' : ''}">${i === 0 ? 'K' : i}</span>${escapeHtml(p.name ?? `${p.lat.toFixed(5)}, ${p.lon.toFixed(5)}`)}</li>`)
    this.el.list.innerHTML = items.length ? items.join('') : '<li class="muted">Chưa có điểm nào</li>'
  }

  // Marker: trước khi lập tour đánh số theo thứ tự nhập; sau đó theo thứ tự ghé của thẻ đang chọn.
  private renderMap() {
    this.layer.clearLayers()
    const plan = this.selected ? this.res?.plans[this.selected] : undefined
    if (plan) {
      L.polyline(toLatLngs(plan.geometry.coordinates), { color: '#7048e8', weight: 5, opacity: 0.85 }).addTo(this.layer)
    }
    const visit = new Map<number, number>()
    plan?.order.forEach((p, k) => visit.set(p, k))
    this.points.forEach((p, i) => {
      const at = this.res?.snapped[i] ?? p
      const label = i === 0 ? 'K' : String(plan ? visit.get(i) : i)
      const tip = plan && i !== 0 ? `Ghé thứ ${visit.get(i)} · ${this.name(i)}` : this.name(i)
      L.marker([at.lat, at.lon], {
        icon: L.divIcon({ className: `tour-marker${i === 0 ? ' depot' : ''}`, html: label, iconSize: [24, 24] }),
      }).bindTooltip(tip).addTo(this.layer)
    })
  }

  private renderCards() {
    const res = this.res
    if (!res || res.status !== 'ok') {
      this.el.results.innerHTML = '<p class="muted">Chưa có tour.</p>'
      return
    }
    const base = res.plans.input?.cost_s
    this.el.results.innerHTML = METHODS.filter((m) => res.plans[m]).map((m) => {
      const p = res.plans[m]!
      const gain = base && m !== 'input' ? ` · ${num((100 * (base - p.cost_s)) / base)}% so với thứ tự nhập` : ''
      const order = p.order.map((i) => (i === 0 ? 'K' : String(i))).concat('K').join(' → ')
      return `
        <button class="tour-card${m === this.selected ? ' selected' : ''}" data-method="${m}">
          <span class="tour-card-title">${TOUR_LABEL[m]}${m === res.chosen ? ' <em>rẻ nhất</em>' : ''}</span>
          <span>Thời gian di chuyển ước tính: <strong>${num(p.cost_s)} s</strong> (${num(p.cost_s / 60)} phút)${gain}</span>
          <span>Quãng đường: ${num(p.distance_m, 0)} m</span>
          <span class="muted small">${order}</span>
        </button>`
    }).join('') + '<p class="muted small">Số trên bản đồ là thứ tự ghé của thẻ đang chọn. '
      + 'Số trong danh sách và trong dòng thứ tự của thẻ là số điểm theo thứ tự nhập.</p>'
    this.el.results.querySelectorAll<HTMLButtonElement>('.tour-card').forEach((b) =>
      b.addEventListener('click', () => this.select(b.dataset.method as TourMethod)))
  }
}

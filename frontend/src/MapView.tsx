// Bản đồ Leaflet bọc trong một component (T56 R1): Leaflet dùng trực tiếp, không qua react-leaflet,
// để giữ logic vẽ đã kiểm trong layers.ts. Đây là chỗ duy nhất dùng phần tử DOM thường (R2).
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { getNetwork, type LatLon } from './api'
import { MapLayers } from './layers'

// Tâm quanh chợ Bến Thành (cùng tâm với data/config/areas.json).
const CENTER: L.LatLngTuple = [10.7725, 106.698]

// Nền bản đồ, người dùng chọn bằng nút góc trên phải (16/11, Tiến chọn): "Đường phố" (mặc định) là Esri World Street
// Map, có ảnh gốc tới z19 nên sắc nét ở mọi mức zoom, có tên đường và mũi tên đường một chiều; "Xám" là Esri Light
// Gray (đợt UI 15/11), sạch kiểu dashboard nhưng chỉ có ảnh tới z16 nên phóng to bị nhoè. Mỗi lựa chọn có chuỗi dự
// phòng: Esri → OSM → nền rút gọn tự vẽ từ /api/network. Chỉ xem tương tác, không tải hàng loạt tile (ARCHITECTURE 6).
interface TileProvider { url: string; maxNativeZoom: number; attribution: string }
export type BasemapChoice = 'street' | 'gray'
const OSM: TileProvider = {
  url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  maxNativeZoom: 19,
  attribution: 'Nền © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
}
export const TILE_CHAINS: Record<BasemapChoice, TileProvider[]> = {
  street: [
    {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      maxNativeZoom: 19,
      attribution: 'Nền © Esri, HERE, Garmin, USGS, © OpenStreetMap contributors, and the GIS User Community',
    },
    OSM,
  ],
  gray: [
    {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      // Esri Light Gray chỉ có ảnh tới z16; z17+ trả ảnh "Map data not yet available" với HTTP 200 (không có
      // tileerror), nên phóng tile z16 lên thay vì xin z17+.
      maxNativeZoom: 16,
      attribution: 'Nền © Esri, HERE, Garmin, © OpenStreetMap contributors, and the GIS user community',
    },
    OSM,
  ],
}
const BASEMAP_LABEL: Record<BasemapChoice, string> = { street: 'Đường phố', gray: 'Xám' }
// Lựa chọn nền nhớ theo trình duyệt của người xem (tiện lợi, không bắt buộc); trình duyệt chặn lưu thì dùng mặc định.
const BASEMAP_KEY = 'saigo.basemap'
const readChoice = (): BasemapChoice => {
  try { return localStorage.getItem(BASEMAP_KEY) === 'gray' ? 'gray' : 'street' } catch { return 'street' }
}
const saveChoice = (c: BasemapChoice) => {
  try { localStorage.setItem(BASEMAP_KEY, c) } catch { /* không lưu được: lần sau về mặc định */ }
}
// Đồ thị tìm đường là dữ liệu OSM (ODbL): ghi nguồn này luôn hiện, dù đang dùng nền nào.
const DATA_ATTRIBUTION = 'Dữ liệu tuyến © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
// Một lượt tải tile chưa xong sau ngần này mà chưa tile nào tải được thì coi như lượt hỏng (mạng treo: 'load' không tới).
const BATCH_TIMEOUT_MS = 6000

export default function MapView({ onReady, onClick }: {
  onReady: (layers: MapLayers) => void
  onClick: (p: LatLon) => void
}) {
  const el = useRef<HTMLDivElement>(null)
  const onClickRef = useRef(onClick)
  onClickRef.current = onClick

  useEffect(() => {
    // Nút zoom ghi tiếng Việt (trang là lang=vi; review 14/11 đợt 3, FE-4).
    // Người dùng chọn giảm chuyển động thì tắt hiệu ứng zoom và mờ dần của Leaflet (test lại 15/11, A-11).
    const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    const map = L.map(el.current!, {
      zoomControl: false, zoomAnimation: !still, fadeAnimation: !still, markerZoomAnimation: !still,
    }).setView(CENTER, 16)
    // Khung bản đồ nhận focus bằng Tab nhưng không có tên (A-9).
    map.getContainer().setAttribute('aria-label', 'Bản đồ. Phím mũi tên để di chuyển, phím + và − để thu phóng.')
    // Nút bản đồ gom một cột ở góc dưới phải (đợt UI "Bàn điều phối"): từ trên xuống là chọn nền, Về toàn tuyến, +/−,
    // rồi dòng ghi nguồn. Góc dưới của Leaflet chèn control mới lên trên, nên thêm zoom trước, chọn nền sau cùng.
    L.control.zoom({ zoomInTitle: 'Phóng to', zoomOutTitle: 'Thu nhỏ', position: 'bottomright' }).addTo(map)
    map.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>')   // bỏ lá cờ mặc định
    map.attributionControl.addAttribution(DATA_ATTRIBUTION)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))
    const layers = new MapLayers(map)
    onReady(layers)

    // Nhãn nhỏ góc trên phải khi đang dùng nền rút gọn (thay câu "Không tải được nền…" trong dòng ghi nguồn, trông như
    // báo lỗi và vỡ hai dòng ở màn hẹp).
    const chip = L.DomUtil.create('div', 'map-chip')
    chip.textContent = 'Nền rút gọn từ dữ liệu đồ thị'
    chip.style.display = 'none'
    const Chip = L.Control.extend({ onAdd: () => chip })
    new Chip({ position: 'topright' }).addTo(map)

    let fallback = false
    let retry: number | undefined
    let disposed = false   // bản đồ đã gỡ: request nền đang chạy về sau thì bỏ, không hẹn thử lại (góp ý #147)
    const showFallback = () => {
      fallback = true
      const load = () => getNetwork()
        .then((n) => {
          if (disposed || !fallback) return
          layers.setNetwork(n.lines, n.kinds)
          chip.style.display = ''
          muteTiles()
        })
        // Backend chưa sẵn sàng: tự thử lại sau 3 s, không đợi tới lần lỗi tile sau (review 14/11 đợt 3, QA-15).
        .catch(() => { if (!disposed && fallback) retry = window.setTimeout(load, 3000) })
      load()
    }
    const hideFallback = () => {
      fallback = false
      window.clearTimeout(retry)
      layers.setNetwork(null)
      chip.style.display = 'none'
      if (tilesMuted) map.attributionControl.addAttribution(providers[idx].attribution)
      tilesMuted = false
    }
    // Lớp tile vẫn nằm trên bản đồ khi đang dùng nền rút gọn (để tự gỡ nền rút gọn khi mạng phục hồi) nhưng không vẽ
    // gì: bỏ ghi nguồn của nó trong lúc này, chỉ còn "Dữ liệu tuyến © OpenStreetMap" (góp ý #157). Cờ để không trừ
    // hay cộng hai lần khi đổi nền giữa chừng.
    let tilesMuted = false
    const muteTiles = () => {
      if (tilesMuted || !fallback) return
      map.attributionControl.removeAttribution(providers[idx].attribution)
      tilesMuted = true
    }

    // Chuỗi nền. Mỗi nguồn một TileLayer riêng (setUrl không đổi ghi nguồn hay giới hạn zoom). Xét theo từng lượt tải
    // (reset ở 'loading', kết luận ở 'load' hoặc khi quá BATCH_TIMEOUT_MS): lượt lỗi nhiều hơn tải được thì sang nguồn
    // kế; hết nguồn thì vẽ nền rút gọn và quay về nguồn đầu, để khi mạng phục hồi tile thật đè lên và nền rút gọn được
    // gỡ (lượt sạch, không lỗi). `gen` bỏ sự kiện của nguồn đã thay.
    let choice = readChoice()
    let providers = TILE_CHAINS[choice]
    let gen = 0
    let idx = 0
    let exhausted = false
    let tiles: L.TileLayer | null = null
    let loaded = 0
    let failed = 0
    let timer: number | undefined
    const judge = (my: number, timedOut: boolean) => {
      if (my !== gen || disposed) return
      window.clearTimeout(timer)
      const bad = timedOut ? loaded === 0 : failed > loaded
      if (bad) {
        if (!exhausted && idx + 1 < providers.length) {
          use(idx + 1)
          return
        }
        if (!fallback) showFallback()
        else muteTiles()
        if (!exhausted) {
          exhausted = true
          use(0)
        }
        return
      }
      if (fallback && failed === 0 && loaded > 0) hideFallback()
    }
    const use = (i: number) => {
      gen += 1
      const my = gen
      window.clearTimeout(timer)
      tiles?.remove()
      tilesMuted = false   // lớp mới tự thêm ghi nguồn của nó
      idx = i
      const p = providers[i]
      const t = L.tileLayer(p.url, { maxZoom: 19, maxNativeZoom: p.maxNativeZoom, detectRetina: false, attribution: p.attribution })
      // Gắn listener trước khi thêm vào bản đồ, để không lỡ lượt tải đầu tiên.
      t.on('loading', () => {
        if (my !== gen) return
        loaded = 0
        failed = 0
        window.clearTimeout(timer)
        timer = window.setTimeout(() => judge(my, true), BATCH_TIMEOUT_MS)
      })
      t.on('tileload', () => { if (my === gen) loaded += 1 })
      t.on('tileerror', () => { if (my === gen) failed += 1 })
      t.on('load', () => judge(my, false))
      tiles = t.addTo(map)
      tiles.bringToBack()
    }
    use(0)

    // Nút chọn nền "Đường phố / Xám" (16/11). Đổi nền thì chạy lại chuỗi dự phòng của lựa chọn mới từ đầu.
    const switcher = L.DomUtil.create('div', 'leaflet-bar leaflet-control map-basemap')
    switcher.setAttribute('role', 'group')
    switcher.setAttribute('aria-label', 'Chọn nền bản đồ')
    const buttons = (['street', 'gray'] as BasemapChoice[]).map((c) => {
      const b = L.DomUtil.create('button', 'map-basemap-btn', switcher) as HTMLButtonElement
      b.type = 'button'
      b.textContent = BASEMAP_LABEL[c]
      b.addEventListener('click', () => {
        if (c === choice) return
        choice = c
        saveChoice(c)
        providers = TILE_CHAINS[c]
        exhausted = false
        use(0)
        paint()
      })
      return [c, b] as const
    })
    const paint = () => buttons.forEach(([c, b]) => b.setAttribute('aria-pressed', String(c === choice)))
    paint()
    L.DomEvent.disableClickPropagation(switcher)
    L.DomEvent.disableScrollPropagation(switcher)   // lăn chuột trên nút không zoom bản đồ (góp ý #162)
    const Switcher = L.Control.extend({ onAdd: () => switcher })
    new Switcher({ position: 'bottomright' }).addTo(map)

    // Khung bản đồ đổi kích thước theo bố cục: báo Leaflet tính lại để không bị ô trắng.
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(el.current!)
    return () => {
      disposed = true
      window.clearTimeout(retry)
      window.clearTimeout(timer)
      resize.disconnect()
      map.remove()
    }
  }, [onReady])

  return <div ref={el} className="map-frame" />
}

// Bản đồ Leaflet bọc trong một component (T56 R1): Leaflet dùng trực tiếp, không qua react-leaflet,
// để giữ logic vẽ đã kiểm trong layers.ts. Đây là chỗ duy nhất dùng phần tử DOM thường (R2).
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import { getNetwork, type LatLon } from './api'
import { MapLayers } from './layers'

// Tâm quanh chợ Bến Thành (cùng tâm với data/config/areas.json).
const CENTER: L.LatLngTuple = [10.7725, 106.698]

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
    L.control.zoom({ zoomInTitle: 'Phóng to', zoomOutTitle: 'Thu nhỏ' }).addTo(map)
    // Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))
    const layers = new MapLayers(map)
    onReady(layers)

    // T56 R8: mạng chặn tile OSM (vd. DNS không phân giải được) thì nền trống → vẽ mạng đường từ dữ liệu đồ thị làm
    // nền; vẫn giữ dòng ghi nguồn OSM. Xét theo từng lượt tải tile (từ 'loading' tới 'load'): lượt xong mà có ≥ 3 tile
    // lỗi và lỗi nhiều hơn tải được thì bật nền dự phòng; một lượt sau tải đủ, không lỗi, thì gỡ đi. Trước đây chỉ bật khi
    // chưa tile nào tải được và không bao giờ gỡ, nên mạng chập chờn (3 lỗi về trước tile đầu tiên) để nền dự phòng
    // đè lên tile thật mãi, còn mạng mất một nửa tile thì không có nền dự phòng (R3 15/11, Minh).
    const NOTE = 'Không tải được nền OSM: đang vẽ mạng đường từ dữ liệu'
    let batchLoaded = 0
    let batchFailed = 0
    let fallback = false
    let retry: number | undefined
    let disposed = false   // bản đồ đã gỡ: request nền đang chạy về sau thì bỏ, không hẹn thử lại (góp ý #147)
    const showFallback = () => {
      fallback = true
      const load = () => getNetwork()
        .then((n) => {
          if (disposed || !fallback) return
          layers.setNetwork(n.lines)
          map.attributionControl.addAttribution(NOTE)
        })
        // Backend chưa sẵn sàng: tự thử lại sau 3 s, không đợi tới lần lỗi tile sau (lúc đó bản đồ có thể đã nạp
        // hết tile lỗi và không còn lỗi mới, nên nền cứ xám trống; review 14/11 đợt 3, QA-15).
        .catch(() => { if (!disposed && fallback) retry = window.setTimeout(load, 3000) })
      load()
    }
    const hideFallback = () => {
      fallback = false
      window.clearTimeout(retry)
      layers.setNetwork(null)
      map.attributionControl.removeAttribution(NOTE)
    }
    tiles.on('loading', () => { batchLoaded = 0; batchFailed = 0 })
    tiles.on('tileload', () => { batchLoaded += 1 })
    tiles.on('tileerror', () => { batchFailed += 1 })
    // Quyết định khi cả lượt đã xong (góp ý #156): xét ngay ở lỗi thứ 3 thì 3 tile lỗi về trước 13 tile tải được vẫn
    // bật nền dự phòng cho cả lượt. Mạng chặn hẳn (DNS) thì mọi tile lỗi ngay nên lượt xong gần như tức thì.
    tiles.on('load', () => {
      if (!fallback && batchFailed >= 3 && batchFailed > batchLoaded) showFallback()
      else if (fallback && batchFailed === 0 && batchLoaded > 0) hideFallback()
    })
    // Khung bản đồ đổi kích thước theo bố cục: báo Leaflet tính lại để không bị ô trắng.
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(el.current!)
    return () => {
      disposed = true
      window.clearTimeout(retry)
      resize.disconnect()
      map.remove()
    }
  }, [onReady])

  return <div ref={el} className="map-frame" />
}

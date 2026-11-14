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
    const map = L.map(el.current!, { zoomControl: false }).setView(CENTER, 16)
    L.control.zoom({ zoomInTitle: 'Phóng to', zoomOutTitle: 'Thu nhỏ' }).addTo(map)
    // Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
    const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))
    const layers = new MapLayers(map)
    onReady(layers)

    // T56 R8: mạng chặn tile OSM (vd. DNS không phân giải được) thì nền trống. Lỗi liên tiếp mà chưa tile nào
    // tải được → vẽ mạng đường từ dữ liệu đồ thị làm nền; vẫn giữ dòng ghi nguồn OSM.
    let loaded = 0
    let failed = 0
    let fallback = false
    let retry: number | undefined
    tiles.on('tileload', () => { loaded += 1 })
    tiles.on('tileerror', () => {
      failed += 1
      if (fallback || loaded > 0 || failed < 3) return
      fallback = true
      const load = () => getNetwork()
        .then((n) => {
          layers.setNetwork(n.lines)
          map.attributionControl.addAttribution('Không tải được nền OSM: đang vẽ mạng đường từ dữ liệu')
        })
        // Backend chưa sẵn sàng: tự thử lại sau 3 s, không đợi tới lần lỗi tile sau (lúc đó bản đồ có thể đã nạp
        // hết tile lỗi và không còn lỗi mới, nên nền cứ xám trống; review 14/11 đợt 3, QA-15).
        .catch(() => { retry = window.setTimeout(load, 3000) })
      load()
    })
    // Khung bản đồ đổi kích thước theo bố cục: báo Leaflet tính lại để không bị ô trắng.
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(el.current!)
    return () => {
      window.clearTimeout(retry)
      resize.disconnect()
      map.remove()
    }
  }, [onReady])

  return <div ref={el} className="map-frame" />
}

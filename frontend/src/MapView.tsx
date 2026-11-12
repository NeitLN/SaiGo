// Bản đồ Leaflet bọc trong một component (T56 R1): Leaflet dùng trực tiếp, không qua react-leaflet,
// để giữ logic vẽ đã kiểm trong layers.ts. Đây là chỗ duy nhất dùng phần tử DOM thường (R2).
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import type { LatLon } from './api'
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
    const map = L.map(el.current!).setView(CENTER, 16)
    // Nền tile OSM chỉ để xem tương tác, không tải hàng loạt (docs/ARCHITECTURE.md mục 6).
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: 'Dữ liệu © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
    }).addTo(map)
    map.on('click', (e: L.LeafletMouseEvent) => onClickRef.current({ lat: e.latlng.lat, lon: e.latlng.lng }))
    onReady(new MapLayers(map))
    // Khung bản đồ đổi kích thước theo bố cục: báo Leaflet tính lại để không bị ô trắng.
    const resize = new ResizeObserver(() => map.invalidateSize())
    resize.observe(el.current!)
    return () => {
      resize.disconnect()
      map.remove()
    }
  }, [onReady])

  return <div ref={el} className="map-frame" />
}

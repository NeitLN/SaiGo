// Trạng thái server và dataset (tách khỏi App.tsx sau review UI 14/11): badge "Server sẵn sàng", danh sách kịch
// bản, id dataset và khung vùng dữ liệu. Hành vi giữ nguyên như trong App trước đây.
import { useCallback, useEffect, useRef, useState } from 'react'
import { BASELINE, getDataset, getEdgeNames, getHealth, type BBox, type Scenario } from './api'

export interface ServerBadge { text: string; ok: boolean | null }

export function useServerStatus() {
  const [server, setServer] = useState<ServerBadge>({ text: 'Đang kiểm tra server…', ok: null })
  const [datasetId, setDatasetId] = useState<string | null>(null)
  // Số node của đồ thị: trục của thanh node ở khay phân tích (đợt UI "Bàn điều phối"), không viết cứng 1.889.
  const [nodeCount, setNodeCount] = useState<number | null>(null)
  // Tên đường theo id cạnh (đánh giá dùng thử 16/11), cho danh sách đóng đoạn; lỗi hay backend cũ thì để rỗng.
  const [edgeNames, setEdgeNames] = useState<(string | null)[]>([])
  const [dataArea, setDataArea] = useState<BBox | null>(null)   // viền vùng có dữ liệu (PM-7, UX-3)
  const [scenarios, setScenarios] = useState<Scenario[]>([BASELINE])
  const [scenarioNote, setScenarioNote] = useState<string | null>(null)

  const badgeFrom = (loaded: boolean, id?: string | null): ServerBadge =>
    ({ text: loaded ? `Server sẵn sàng · ${id ?? ''}` : 'Server chạy, chưa nạp dataset', ok: loaded })
  const DOWN: ServerBadge = { text: 'Không kết nối được server', ok: false }

  // Kiểm lúc mở trang và mỗi khi một request lỗi, để badge không báo "sẵn sàng" khi backend đã tắt.
  const checkServer = useCallback(() => {
    getHealth()
      .then((h) => setServer(badgeFrom(h.dataset_loaded, h.dataset_id)))
      .catch(() => setServer(DOWN))
  }, [])

  // Đã đọc được /api/dataset (hoặc biết API không có). Lần đầu đọc lỗi thì nhịp kiểm 10 s đọc lại (test lại 15/11,
  // C-3: trước đây chỉ đọc lại khi server từ tắt sang bật, nên lỗi một lần lúc mở trang thì mất danh sách kịch bản).
  const datasetRead = useRef(false)
  const loadDataset = useCallback(() => {
    getDataset()
      .then((d) => {
        datasetRead.current = true
        if (d === null) {
          setScenarioNote('API chưa có /api/dataset (T51); chỉ có điều kiện cơ sở.')
          return
        }
        setScenarioNote(null)
        setDatasetId(d.dataset_id)
        setNodeCount(d.node_count ?? null)
        getEdgeNames().then((n) => setEdgeNames(n.names)).catch(() => setEdgeNames([]))
        if (d.scenarios.length) setScenarios(d.scenarios)
        setDataArea(d.bbox ?? null)
      })
      .catch((e: Error) => setScenarioNote(`Không đọc được danh sách điều kiện giao thông: ${e.message}`))
  }, [])

  // Request thành công sau khi backend bật lại (kể cả khi mở trang lúc backend còn tắt): đưa badge về
  // "sẵn sàng" và đọc lại danh sách kịch bản, không cần tải lại trang.
  const serverOk = useRef(server.ok)
  serverOk.current = server.ok
  const markServerUp = useCallback(() => {
    if (serverOk.current === true && datasetRead.current) return
    checkServer()
    loadDataset()
  }, [checkServer, loadDataset])

  useEffect(() => {
    checkServer()
    loadDataset()
  }, [checkServer, loadDataset])

  // Badge tự cập nhật (review 14/11 đợt 3, QA-7): kiểm mỗi 10 s và khi quay lại cửa sổ; lên lại thì đọc lại
  // danh sách kịch bản như markServerUp.
  useEffect(() => {
    const tick = () => {
      getHealth()
        .then((h) => {
          if (h.dataset_loaded && (serverOk.current !== true || !datasetRead.current)) loadDataset()
          setServer(badgeFrom(h.dataset_loaded, h.dataset_id))
        })
        .catch(() => setServer(DOWN))
    }
    const id = window.setInterval(tick, 10_000)
    window.addEventListener('focus', tick)
    return () => {
      window.clearInterval(id)
      window.removeEventListener('focus', tick)
    }
  }, [loadDataset])

  return { server, datasetId, nodeCount, edgeNames, dataArea, scenarios, scenarioNote, checkServer, markServerUp }
}

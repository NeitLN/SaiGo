// Kịch bản demo 4 phút (docs/DEMO.md mục 2) chạy trên app thật ở 1280 × 800. Mỗi bước kiểm số đo được
// mà DEMO ghi, nên khi đổi giao diện mà số hay tên nút đổi theo thì test báo ngay.
// Helper tìm điều khiển theo vai trò và tên (chế độ, lộ trình mẫu, điều kiện giao thông), không theo class,
// để vẫn dùng được khi ô chọn đổi thành chip hay danh sách.
import { expect, test, type Page } from '@playwright/test'

const CASE_DATASET = 'hcm-benthanh-r2000-20261024'

/** Chọn một mục theo tên: ô chọn (combobox) nếu có, không thì nút radio hoặc nút bấm cùng tên. */
async function choose(page: Page, label: string, option: string | RegExp) {
  const box = page.getByRole('combobox', { name: label })
  if (await box.count()) {
    await box.first().click()
    await page.getByRole('option', { name: option, exact: typeof option === 'string' }).first().click()
    return
  }
  const group = page.getByRole('radiogroup', { name: label }).or(page.getByRole('group', { name: label })).or(page.getByRole('region', { name: label }))
  const scope = (await group.count()) ? group.first() : page
  const radio = scope.getByRole('radio', { name: option, exact: typeof option === 'string' })
  if (await radio.count()) { await radio.first().click(); return }
  await scope.getByRole('button', { name: option, exact: typeof option === 'string' }).first().click()
}

async function mode(page: Page, name: 'Tìm đường' | 'Tour') {
  const radio = page.getByRole('radio', { name, exact: true })
  if (await radio.count()) await radio.first().click()
  else await page.getByRole('tab', { name, exact: true }).first().click()
}

const body = (page: Page) => page.locator('body')

/** Đợi app hết tính (không còn vòng quay "Đang tính…" hay "Đang kiểm điểm…"). */
async function settled(page: Page) {
  await expect(page.getByText(/Đang tính…|Đang kiểm điểm/)).toHaveCount(0)
}

/** Số đứng riêng: "404" không khớp vào "1.404", "4040" hay "404,5" (góp ý review #163). */
const escape = (t: string) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
const exact = (t: string) => new RegExp(`(?<![\\d.,])${escape(t)}(?!\\d|[.,]\\d)`)

async function expectAll(page: Page, texts: (string | RegExp)[]) {
  await settled(page)
  // innerText (không phải textContent) để các ô bảng cạnh nhau có dấu tách, vd. "1.762<tab>1.762" chứ không "1.7621.762".
  for (const t of texts) {
    const want = typeof t === 'string' ? (/^[+\d]/.test(t) ? exact(t) : new RegExp(escape(t))) : t
    await expect.poll(() => body(page).innerText(), { message: `trang có ${want}` }).toMatch(want)
  }
}

test.beforeEach(async ({ page, request }) => {
  const ds = await (await request.get('http://127.0.0.1:8000/api/dataset')).json()
  test.skip(ds.dataset_id !== CASE_DATASET, `Cần đồ thị ${CASE_DATASET} (đang nạp ${ds.dataset_id})`)
  await page.addInitScript(() => { try { localStorage.clear() } catch { /* trình duyệt chặn bộ nhớ */ } })
  await page.goto('/')
  await expect(page.getByText('Đã kết nối')).toBeVisible()
})

test('Tìm đường: bước 1–7 của DEMO', async ({ page }) => {
  // Bước 1–2: lộ trình mẫu tự chạy cả Dijkstra lẫn A*.
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1', '1.565', '404', '106'])

  // Bước 4: đảo chiều, đường một chiều làm chi phí khác.
  await page.getByRole('button', { name: 'Đảo chiều', exact: true }).click()
  await expectAll(page, ['193,0', '1.417', '477', '108'])

  // Bước 5: đảo lại rồi bật cao điểm trung tâm.
  await page.getByRole('button', { name: 'Đảo chiều', exact: true }).click()
  await expectAll(page, ['186,1'])
  await choose(page, 'Điều kiện giao thông', /Cao điểm mô phỏng — trung tâm|Cao điểm — trung tâm/)
  await expectAll(page, ['246,1', '1.748', '+32,2%', '442', '111'])

  // Bước 6: đóng đoạn 10/18 của tuyến đang xem.
  await choose(page, 'Đóng một đoạn trên tuyến', /^Đoạn 10\/18/)
  await expectAll(page, ['302,3', '2.118'])

  // Bước 7: không còn đường, hai thuật toán cùng mở 1.762 node.
  await choose(page, 'Lộ trình mẫu', 'Không còn đường')
  await expectAll(page, [/[Kk]hông có đường/, '1.762'])
})

test('Tour: bước 9–11 của DEMO', async ({ page }) => {
  await mode(page, 'Tour')

  // Bước 9: ba phương án và Held–Karp đối chứng.
  await choose(page, 'Lộ trình mẫu', 'Kho + 5 điểm giao')
  await expectAll(page, ['898,1', '1.066,0', '627,8', '43,0%'])
  const show = page.getByRole('button', { name: 'Xem trên bản đồ', exact: true })
  await expect(show.first()).toBeVisible()

  // Bước 10: đóng sẵn cạnh 1666, có "Giữ thứ tự cũ" và phương án sắp lại.
  await choose(page, 'Lộ trình mẫu', 'Kho + 5 điểm, đóng đường gần Bến Bạch Đằng')
  await expectAll(page, ['Giữ thứ tự cũ', '962,7', '692,5'])
  // "Giữ thứ tự cũ" đứng đầu danh sách phương án; xem nó thì có dòng so với cùng thứ tự trước khi đóng.
  await page.getByRole('button', { name: 'Xem trên bản đồ', exact: true }).first().click()
  await expectAll(page, ['Cùng thứ tự, trước khi đóng', '+7,2%'])

  // Bước 11: không vẽ tour một phần, báo rõ điểm không tới được.
  await choose(page, 'Lộ trình mẫu', 'Tour không còn khả thi')
  await expectAll(page, ['Không điểm nào đi tới được Nhà hát Thành phố'])
})

test('Khung 1280 × 800: không cuộn trang, nút chính và số chính nằm trong màn hình', async ({ page }) => {
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1'])
  const scroll = await page.evaluate(() => ({
    x: document.documentElement.scrollWidth - window.innerWidth,
    y: document.documentElement.scrollHeight - window.innerHeight,
  }))
  expect(scroll.x, 'trang cuộn ngang').toBeLessThanOrEqual(0)
  expect(scroll.y, 'trang cuộn dọc').toBeLessThanOrEqual(0)
  await expect(page.getByRole('button', { name: 'Tìm đường', exact: true })).toBeInViewport()
  await expect(page.getByText('Thời gian di chuyển ước tính').first()).toBeInViewport()
  // Khay phân tích (đợt UI "Bàn điều phối"): thanh node và kết luận chi phí thấy ngay ở 1280 × 800, không cần cuộn.
  await expect(page.getByText('Chi phí trùng khớp').first()).toBeInViewport()
  await expect(page.getByRole('progressbar', { name: /Dijkstra: 404 node/ })).toBeInViewport()
  await expect(page.getByRole('progressbar', { name: /A\*: 106 node/ })).toBeInViewport()
})

test('Khay phân tích thu gọn được, bản đồ cao lên và vẫn thấy cả tuyến', async ({ page }) => {
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1'])
  const map = page.locator('.map-frame')
  const before = (await map.boundingBox())!.height
  await page.getByRole('button', { name: 'Ẩn khay', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Hiện khay', exact: true })).toHaveAttribute('aria-expanded', 'false')
  // aria-controls trỏ tới phần tử có thật, ẩn khi thu gọn (góp ý review #165).
  await expect(page.locator('#tray-body')).toBeHidden()
  await expect(page.locator('#tray-body')).toHaveCount(1)
  await expect.poll(async () => (await map.boundingBox())!.height).toBeGreaterThan(before + 100)
  // Thu phóng lại sau khi đổi kích thước: hai marker vẫn nằm trong khung bản đồ.
  await page.waitForTimeout(800)
  const box = (await map.boundingBox())!
  for (const m of await page.locator('.leaflet-marker-pane .leaflet-marker-icon').all()) {
    const b = (await m.boundingBox())!
    expect(b.y >= box.y && b.y + b.height <= box.y + box.height, 'marker trong khung bản đồ').toBe(true)
  }
  await page.getByRole('button', { name: 'Hiện khay', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Ẩn khay', exact: true })).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('#tray-body')).toBeVisible()
})

test('Bản đồ: ký hiệu A/B có tên địa danh, chú giải thu gọn được', async ({ page }) => {
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1'])
  await expect(page.getByRole('img', { name: 'Điểm đi: Dinh Độc Lập' })).toBeVisible()
  await expect(page.getByRole('img', { name: 'Điểm đến: Bitexco' })).toBeVisible()
  const legend = page.getByRole('button', { name: 'Chú giải' })
  await expect(legend).toHaveAttribute('aria-expanded', 'true')
  await expect(page.locator('#map-legend-rows')).toBeVisible()
  await legend.click()
  await expect(page.getByRole('button', { name: 'Chú giải' })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.locator('#map-legend-rows')).toBeHidden()
  await page.getByRole('button', { name: 'Chú giải' }).click()
  await expect(page.locator('#map-legend-rows')).toBeVisible()
  // Nút giữ focus khi bản đồ vẽ lại vì có kết quả mới (góp ý review #166).
  await page.getByRole('button', { name: 'Chú giải' }).focus()
  await page.getByRole('button', { name: 'Đảo chiều', exact: true }).evaluate((b: HTMLElement) => b.click())
  await expectAll(page, ['193,0'])
  await expect(page.getByRole('button', { name: 'Chú giải' })).toBeFocused()
})

test('Tour: lịch trình khớp marker, rê dòng làm nổi điểm, dòng phương án có vạch Held–Karp', async ({ page }) => {
  await mode(page, 'Tour')
  await choose(page, 'Lộ trình mẫu', 'Kho + 5 điểm giao')
  await expectAll(page, ['898,1'])
  // NN + 2-opt: p1, p2, p4, p3, p5 → Nhà thờ Đức Bà, Nhà hát Thành phố, Bến Bạch Đằng, Bảo tàng Mỹ thuật, Công viên Tao Đàn.
  const rows = page.locator('.itin-row')
  await expect(rows).toHaveCount(7)
  await expect(rows.nth(3)).toHaveAccessibleName('Điểm 3: Bến Bạch Đằng')
  await expect(rows.nth(3)).toContainText('nhập #4')
  await rows.nth(3).focus()
  await expect(page.getByRole('img', { name: 'Điểm 3: Bến Bạch Đằng' })).toHaveClass(/is-highlighted/)
  await rows.nth(3).blur()
  await expect(page.getByRole('img', { name: 'Điểm 3: Bến Bạch Đằng' })).not.toHaveClass(/is-highlighted/)
  // Bốn phương án, mỗi dòng một thanh có vạch tối ưu (Held–Karp chạy trong cùng response).
  await expect(page.locator('.plan-row')).toHaveCount(4)
  await expect(page.locator('.plan-row .astryx-progress-bar-mark')).toHaveCount(4)
  await expect(page.getByText('chậm hơn tối ưu 43,0%')).toBeVisible()
})

test('Điều khiển: chip điều kiện bằng phím mũi tên, danh sách mẫu theo chế độ, chế độ chặn bật/tắt bằng Esc', async ({ page }) => {
  // Danh sách mẫu chỉ có mẫu của chế độ đang dùng, mẫu đang mở có aria-pressed.
  const cases = page.getByRole('group', { name: 'Lộ trình mẫu' }).getByRole('button')
  await expect(cases).toHaveText(['Hai điểm qua trung tâm', 'Không còn đường'])
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1'])
  await expect(page.getByRole('button', { name: 'Hai điểm qua trung tâm' })).toHaveAttribute('aria-pressed', 'true')
  // Chip: một chip nhận Tab, mũi tên phải chọn chip kế và tính lại ngay.
  const chips = page.getByRole('radiogroup', { name: 'Điều kiện giao thông' }).getByRole('radio')
  await expect(chips).toHaveCount(3)
  await expect(chips.nth(0)).toHaveAttribute('aria-checked', 'true')
  await chips.nth(0).focus()
  await page.keyboard.press('ArrowRight')
  await expect(chips.nth(1)).toBeFocused()
  await expect(chips.nth(1)).toHaveAttribute('aria-checked', 'true')
  await expectAll(page, ['246,1', '+32,2%'])
  // Chặn trên bản đồ: nút bật/tắt có aria-pressed, Esc tắt.
  const tool = page.getByRole('button', { name: 'Chặn trên bản đồ' })
  await expect(tool).toHaveAttribute('aria-pressed', 'false')
  await expect(page.locator('path.route-hit')).toHaveCount(0)
  await tool.click()
  await expect(tool).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('path.route-hit').first()).toBeAttached()
  await page.keyboard.press('Escape')
  await expect(tool).toHaveAttribute('aria-pressed', 'false')
  await expect(page.locator('path.route-hit')).toHaveCount(0)
  // Đổi chế độ thì chế độ chặn tắt: sang Tour mở mẫu, tour không bấm đóng được ngay (góp ý review #169).
  await tool.click()
  await expect(tool).toHaveAttribute('aria-pressed', 'true')
  await mode(page, 'Tour')
  await choose(page, 'Lộ trình mẫu', 'Kho + 5 điểm giao')
  await expectAll(page, ['898,1'])
  await expect(page.locator('path.route-hit')).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Chặn trên bản đồ' })).toHaveAttribute('aria-pressed', 'false')
})

test('So với Cơ sở khi đổi giữa hai kiểu cao điểm; bấm ngoài vùng có dữ liệu thì báo rõ', async ({ page }) => {
  await choose(page, 'Lộ trình mẫu', 'Hai điểm qua trung tâm')
  await expectAll(page, ['186,1'])
  await choose(page, 'Điều kiện giao thông', /Cao điểm — trung tâm/)
  await expectAll(page, ['246,1', 'So với Cơ sở (không ùn tắc, không đóng đường): 186,1 s → 246,1 s: +60,0 s (+32,2%)'])
  // Đổi điều kiện thì bản đồ thu phóng lại vừa tuyến mới: hai marker nằm trong khung bản đồ.
  await page.waitForTimeout(800)
  const frame = (await page.locator('.map-frame').boundingBox())!
  for (const name of ['Điểm đi: Dinh Độc Lập', 'Điểm đến: Bitexco']) {
    const m = (await page.getByRole('img', { name }).boundingBox())!
    expect(m.y >= frame.y && m.y + m.height <= frame.y + frame.height, `${name} trong khung`).toBe(true)
  }
  // Sang cao điểm khác: "lần trước" là cao điểm trung tâm, nhưng dòng Cơ sở vẫn so với giờ bình thường.
  await choose(page, 'Điều kiện giao thông', /Cao điểm — Bến Thành/)
  await expect(page.getByText(/So với Cơ sở \(không ùn tắc, không đóng đường\): 186,1 s → /)).toBeVisible()
  await expect(page.getByText(/So với Cơ sở[^\n]*: 186,1 s → [\d.,]+ s: \+/)).toBeVisible()
  // Bấm ngoài khung vùng có dữ liệu: thu nhỏ tới mức xa nhất (z13, khung chỉ còn ở giữa), rồi bấm góc trên trái.
  await page.getByRole('button', { name: 'Xóa', exact: true }).click()
  const zoomOut = page.getByRole('button', { name: 'Thu nhỏ' })
  for (let i = 0; i < 8 && (await zoomOut.getAttribute('aria-disabled')) !== 'true'; i++) {
    await zoomOut.click()
    await page.waitForTimeout(400)   // Leaflet bỏ qua lệnh zoom trong lúc đang chạy hiệu ứng zoom trước
  }
  const b = (await page.locator('.map-frame').boundingBox())!
  await page.mouse.click(b.x + 40, b.y + 40)
  await expect(page.getByText('Điểm này nằm ngoài vùng có dữ liệu')).toBeVisible()
})

test('Tour: so với Cơ sở dùng cùng thứ tự giao, cao điểm không bao giờ nhanh hơn giờ bình thường', async ({ page }) => {
  await mode(page, 'Tour')
  await choose(page, 'Lộ trình mẫu', 'Kho + 5 điểm giao')
  await expectAll(page, ['898,1'])
  await choose(page, 'Điều kiện giao thông', /Cao điểm — trung tâm/)
  // Cùng thứ tự giao: chi phí ở cao điểm (hệ số ≥ 1) không thể thấp hơn ở Cơ sở, nên phần chênh luôn là dấu +.
  const line = page.getByText(/So với Cơ sở \(không ùn tắc, không đóng đường\), cùng thứ tự giao: /)
  await expect(line).toBeVisible()
  await expect(line).toContainText('+')
  await expect(line).not.toContainText('−')
})

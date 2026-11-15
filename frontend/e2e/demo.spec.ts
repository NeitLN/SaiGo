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
})

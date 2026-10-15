import { readFileSync } from 'node:fs'
import { expect, test, type Page } from '@playwright/test'

/* Every route renders against the built site, with no failed request to the
 * site itself and no console error. Read from dist/ rather than public/, so
 * the ids and the date are the ones the server under test actually serves. */

function readJson<T>(name: string): T {
  return JSON.parse(readFileSync(`dist/data/${name}`, 'utf-8')) as T
}

const meta = readJson<{ snapshot_date: string }>('meta.json')
const animals = readJson<{ id: string; subid: string }[]>('animals.json')
const shelters = readJson<{ shelters: { id: string; name: string }[] }>('shelters.json').shelters

/** Fails the test on a 4xx/5xx from this site or an error in the console.
 *  Requests to other hosts (photos on pet.gov.tw, Google Fonts) are answered
 *  with an empty 204: the test is about this site, and CI should not depend
 *  on a government server being up. */
async function watch(page: Page): Promise<string[]> {
  const problems: string[] = []
  await page.route(
    (url) => url.hostname !== 'localhost',
    (route) => route.fulfill({ status: 204, body: '' }),
  )
  page.on('response', (response) => {
    const url = new URL(response.url())
    if (url.hostname === 'localhost' && response.status() >= 400) {
      problems.push(`${response.status()} ${url.pathname}`)
    }
  })
  page.on('console', (message) => {
    if (message.type() === 'error') problems.push(`console: ${message.text()}`)
  })
  page.on('pageerror', (error) => problems.push(`page error: ${error.message}`))
  return problems
}

const ROUTES = [
  { path: '', name: '首頁' },
  { path: 'animals', name: '找動物' },
  { path: 'shelters', name: '收容所' },
  { path: `shelters/${shelters[0]!.id}`, name: '收容所介紹' },
  { path: 'map', name: '縣市地圖' },
  { path: 'quality', name: '資料品質' },
  { path: 'analysis', name: '資料分析' },
  { path: 'about', name: '關於本站' },
  { path: 'shortlist', name: '候選清單' },
]

for (const route of ROUTES) {
  test(`${route.name} (/${route.path}) renders`, async ({ page }) => {
    const problems = await watch(page)
    await page.goto(route.path)
    await expect(page.locator('h1').first()).toBeVisible()
    // The footer date comes from meta.json, so seeing it proves the data
    // fetch resolved under the sub-path.
    await expect(page.locator('footer')).toContainText(meta.snapshot_date)
    await page.waitForLoadState('networkidle')
    expect(problems).toEqual([])
  })
}

test('the data pages are entered from the about page, not the top bar', async ({ page }) => {
  const problems = await watch(page)
  await page.goto('about')
  const bar = page.getByRole('navigation', { name: '主要導覽', exact: true })
  await expect(bar.getByRole('link', { name: '關於本站' })).toBeVisible()
  await expect(bar.getByRole('link', { name: '資料品質' })).toHaveCount(0)
  await expect(bar.getByRole('link', { name: '資料分析' })).toHaveCount(0)
  await page
    .locator('#ab-data')
    .getByRole('link', { name: /資料分析/ })
    .click()
  await expect(page.locator('h1')).toHaveText('資料分析')
  // The bar marks the entrance, since it has no item of its own to mark.
  await expect(bar.getByRole('link', { name: '關於本站' })).toHaveAttribute('aria-current', 'page')
  expect(problems).toEqual([])
})

test('a shared animal link opens that animal', async ({ page }) => {
  const problems = await watch(page)
  const animal = animals[0]!
  await page.goto(`animals?animal=${animal.id}`)
  await expect(page.getByRole('dialog')).toContainText(animal.subid)
  expect(problems).toEqual([])
})

test('a link to an animal not in the roster says so', async ({ page }) => {
  const problems = await watch(page)
  await page.goto('animals?animal=0')
  await expect(page.getByRole('dialog')).toContainText('不在目前名單')
  expect(problems).toEqual([])
})

test('404.html is the built app, so a refresh on a deep link works on Pages', () => {
  // GitHub Pages has no rewrite rule: /stray-atlas/shelters/<id> is served
  // 404.html, and the app must boot from it (vite.config.ts writes the copy).
  expect(readFileSync('dist/404.html', 'utf-8')).toBe(readFileSync('dist/index.html', 'utf-8'))
})

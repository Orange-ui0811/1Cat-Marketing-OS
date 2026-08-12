import { expect, test } from '@playwright/test'

test('中文工作台登录、导航与R0安全边界', async ({ page }) => {
  const password = process.env.ONECAT_ADMIN_PASSWORD
  test.skip(!password, '需要由测试脚本从项目.env注入一次性管理员密码')

  await page.goto('/')
  await expect(page.getByRole('heading', { name: '进入组织工作台' })).toBeVisible()
  await expect(page.getByText('四平台人工发布')).toBeVisible()
  await expect(page.getByText('PII关闭')).toBeVisible()

  await page.getByLabel('用户名').fill('admin')
  await page.getByLabel('密码').fill(password!)
  await page.getByRole('button', { name: '安全登录' }).click()

  await expect(page.getByRole('heading', { name: '组织运行总览' })).toBeVisible()
  await expect(page.getByText('R0安全运行中')).toBeVisible()
  await expect(page.getByText('数字岗位').first()).toBeVisible()

  await page.getByText('人工任务', { exact: true }).click()
  await expect(page.getByRole('heading', { name: '人工发布与接管' })).toBeVisible()
  await page.getByRole('button', { name: '新建人工发布任务' }).click()
  await page.getByLabel('平台').click()
  await expect(page.getByText('抖音', { exact: true })).toBeVisible()
  await expect(page.getByText('小红书', { exact: true })).toBeVisible()
  await expect(page.getByText('B站', { exact: true })).toBeVisible()
  await expect(page.getByText('公众号', { exact: true })).toBeVisible()
  await expect(page.getByText('视频号', { exact: true })).toHaveCount(0)
  await page.keyboard.press('Escape')
  await page.locator('.ant-modal-close').click()

  await page.getByText('Lead与销售反馈', { exact: true }).click()
  await expect(page.getByRole('heading', { name: 'LeadStub与销售反馈' })).toBeVisible()
  await expect(page.getByText(/姓名、手机、邮箱、私信正文均禁止/)).toBeVisible()

  await page.getByText('审计与证据', { exact: true }).click()
  await expect(page.getByRole('heading', { name: '审计与证据' })).toBeVisible()
})

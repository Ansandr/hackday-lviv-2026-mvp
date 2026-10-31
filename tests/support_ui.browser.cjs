// Run with Playwright available: node tests/support_ui.browser.cjs
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_PATH || 'playwright');

(async () => {
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'msedge' });
  try {
    const page = await browser.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.addInitScript(() => sessionStorage.setItem('support-session', 'browser-test'));
    const messages = [], requests = [];
    let release, hold = true, fail = false, failHistory = false;
    const analysis={priority:'urgent',urgency:'high',impact:'business_blocked',priority_reason:'Клієнт повідомив про зупинку роботи.',customer_tone:{emotion:'worried',sentiment:'negative',rationale:'Клієнт висловлює занепокоєння.'},tone_source:'model'};
    const turn = reply => ({schema_version:'1',conversation_id:'c',state:'needs_input',reply,questions:[],evidence:[],proposed_action:null,action_result:null,analysis});
    await page.route('**/api/v1/**', async route => {
      const request = route.request(), path = new URL(request.url()).pathname;
      if (request.method() === 'POST' && path.endsWith('/messages')) {
        const input = request.postDataJSON(); requests.push(input);
        if (hold) await new Promise(resolve => { release = resolve; });
        if (fail) return route.fulfill({status:503,json:{error:{message:'AI тимчасово недоступний'}}});
        const response = turn('Відповідь на: ' + input.text);
        messages.push({role:'user',text:input.text},{role:'assistant',text:response.reply,turn:response});
        return route.fulfill({json:response});
      }
      if (path.endsWith('/health')) return route.fulfill({json:{status:'ok',mode:'integrated'}});
      if (path.endsWith('/conversations')) return route.fulfill({json:[{conversation_id:'c',title:'Тест',state:'needs_input'}]});
      if (failHistory) return route.fulfill({status:503,json:{error:{message:'History unavailable'}}});
      return route.fulfill({json:{conversation_id:'c',messages,analysis:messages.length?analysis:null}});
    });
    await page.goto(process.env.SUPPORT_TEST_URL || 'http://127.0.0.1:8001');
    await page.locator('#workspace').waitFor({state:'visible'});
    await page.locator('#message').fill('Перший запит');
    await page.locator('#send').click();
    await page.getByText('Перший запит',{exact:true}).waitFor();
    assert.equal(await page.locator('#message').inputValue(), '');
    assert.equal(await page.locator('#agent-waiting').isVisible(), true);
    await page.locator('#message').fill('Чернетка наступного повідомлення');
    while (!release) await new Promise(resolve => setTimeout(resolve, 10));
    hold = false; release();
    await page.getByText('Відповідь на: Перший запит',{exact:true}).waitFor();
    assert.equal(await page.getByText('Перший запит',{exact:true}).count(), 1);
    assert.equal(await page.locator('#message').inputValue(), 'Чернетка наступного повідомлення');
    assert.match(await page.locator('.priority-badge').innerText(),/Критичний/);
    assert.match(await page.locator('.tone-badge').innerText(),/Занепокоєння/);
    await page.locator('.analysis-summary').click();
    await page.getByText('Орієнтовна оцінка тону за текстом · Gemma',{exact:true}).waitFor();
    await Promise.all([page.waitForRequest(r=>r.url().includes('sort=priority')),page.locator('#history-sort').selectOption('priority')]);

    fail = true;
    await page.locator('#message').fill('Запит із помилкою');
    await page.locator('#send').click();
    await page.getByRole('button',{name:'Повторити',exact:true}).waitFor();
    assert.equal(await page.locator('#message').inputValue(), '');
    await page.locator('#message').fill('Нова чернетка');
    fail = false;
    await page.getByRole('button',{name:'Повторити',exact:true}).click();
    await page.getByText('Відповідь на: Запит із помилкою',{exact:true}).waitFor();
    assert.equal(requests[1].client_message_id, requests[2].client_message_id);
    assert.equal(await page.getByText('Запит із помилкою',{exact:true}).count(), 1);
    assert.equal(await page.locator('#message').inputValue(), 'Нова чернетка');

    failHistory = true;
    await page.locator('#message').fill('Відповідь без оновлення історії');
    await page.locator('#send').click();
    await page.getByText('Відповідь на: Відповідь без оновлення історії',{exact:true}).waitFor();
    assert.equal(await page.getByRole('button',{name:'Повторити',exact:true}).count(), 0);
    assert.equal(requests.length, 4);
    assert.deepEqual(errors, []);
    console.log('Browser passed: immediate message, cleared input, waiting state, preserved draft, retry same ID, no duplicate, history failure recovery.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });

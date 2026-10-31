const assert=require('node:assert/strict');
const view=require('../src/ui/presentation.js');
assert.equal(view.parameter('max_redemptions',null),'Без обмежень');
assert.equal(view.parameter('max_redemptions',50),'50');
assert.match(view.parameter('expires_at','2026-11-11T00:00:00+02:00'),/10 листопада 2026/);
assert.equal(view.evidence({kind:'log',id:'log_pos_03',summary:'POS_SYNC_FAILED · {"reason":"delivery_timeout"}'}),'Оновлення не дійшло до каси через збій синхронізації.');
assert.equal(view.evidence({kind:'kb',id:'FILE-promo',summary:'<!-- intent: promo -->\n# Промокод не працює\n## Details\n1. Long text'}),'Промокод не працює');
assert.equal(view.text('**Знижка:** `10%`'),'Знижка: 10%');
console.log('Presentation regression checks passed');

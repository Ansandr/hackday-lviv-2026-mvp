const pptxgen = require("pptxgenjs");
const out = process.argv[2];
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625
pres.title = "AI Support Desk — Team 14";

const INK = "1B2440", AMBER = "F2A541", LIGHT = "F4F6FA", MUTED = "6B7280", WHITE = "FFFFFF", TEAL = "2A9D8F", RED = "C8553D";
const H = "Cambria", B = "Calibri";

function title(s, text, dark) {
  s.addText(text, { x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: H, fontSize: 30, bold: true, color: dark ? WHITE : INK, margin: 0 });
}
function card(s, x, y, w, h, fill) {
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: fill || WHITE }, rectRadius: 0.12,
    shadow: { type: "outer", color: "000000", opacity: 0.12, blur: 6, offset: 2, angle: 90 } });
}
function dot(s, x, y, label, fill) {
  s.addShape(pres.shapes.OVAL, { x, y, w: 0.5, h: 0.5, fill: { color: fill || AMBER } });
  s.addText(label, { x, y, w: 0.5, h: 0.5, align: "center", valign: "middle", fontFace: B, fontSize: 16, bold: true, color: INK, margin: 0 });
}

// 1. Title
let s = pres.addSlide(); s.background = { color: INK };
s.addText("Підтримка, яка не лише відповідає, а діє", { x: 0.5, y: 1.3, w: 9, h: 1.4, fontFace: H, fontSize: 38, bold: true, color: WHITE, margin: 0 });
s.addText("AI-служба підтримки для SaaS закладів: Gemma + RAG + дії з підтвердженням", { x: 0.5, y: 2.85, w: 9, h: 0.5, fontFace: B, fontSize: 18, color: AMBER, margin: 0 });
s.addText("Команда 14 · PolyTech Code Fest × SKELAR · 31.10.2026", { x: 0.5, y: 4.6, w: 9, h: 0.4, fontFace: B, fontSize: 12, color: "B8C0D4", margin: 0 });
s.addNotes("Ми будуємо не чат-бот, а службу підтримки компанії-розробника SaaS для закладів: вона сама знаходить причину, пропонує дію і передає розробникам лише справжні баги.");

// 2. Problem
s = pres.addSlide(); s.background = { color: LIGHT };
title(s, "Проблема: кожне звернення читає людина");
s.addText("75%", { x: 0.5, y: 1.3, w: 3.6, h: 1.4, fontFace: H, fontSize: 72, bold: true, color: RED, margin: 0 });
s.addText("історичних тікетів закриваються документацією або однією дією в системі (9 з 12 у нашому корпусі)", { x: 0.5, y: 2.75, w: 3.6, h: 1.0, fontFace: B, fontSize: 14, color: INK, margin: 0 });
const pains = [
  ["Довго", "Власник закладу чекає години, поки промокод на касі запрацює"],
  ["Дорого", "Саппорт і розробники витрачають час на однакові питання"],
  ["Ризиковано", "Людина помиляється: у тікеті TCK-1010 скасовано обидві підписки і пообіцяно повернення, якого не було"],
];
pains.forEach(([h, t], i) => {
  const y = 1.3 + i * 1.25; card(s, 4.6, y, 4.9, 1.05);
  dot(s, 4.8, y + 0.27, String(i + 1));
  s.addText(h, { x: 5.5, y: y + 0.1, w: 3.8, h: 0.35, fontFace: B, fontSize: 16, bold: true, color: INK, margin: 0 });
  s.addText(t, { x: 5.5, y: y + 0.45, w: 3.85, h: 0.55, fontFace: B, fontSize: 12, color: MUTED, margin: 0 });
});
s.addNotes("Наш корпус з 12 минулих тікетів: 5 закриваються поясненням з документації, 4 однією дією (resync каси, створення промокоду, скасування дубля). Ще 2 це атаки, 1 це помилка людини, яка коштувала грошей і довіри.");

// 3. Solution
s = pres.addSlide(); s.background = { color: WHITE };
title(s, "Рішення: AI-шар між власником закладу і розробниками");
const sol = [
  ["Відповідає", "питання «як зробити» закриває з бази знань і показує джерело", TEAL],
  ["Діє", "знаходить причину в логах і пропонує одну з 4 дій; виконує лише після підтвердження власника", AMBER],
  ["Ескалує", "до людей і розробників доходять лише справжні баги та гроші, що потребують рішення", RED],
];
sol.forEach(([h, t, c], i) => {
  const x = 0.5 + i * 3.05; card(s, x, 1.45, 2.85, 2.6, LIGHT);
  s.addShape(pres.shapes.OVAL, { x: x + 0.25, y: 1.65, w: 0.45, h: 0.45, fill: { color: c } });
  s.addText(h, { x: x + 0.25, y: 2.25, w: 2.4, h: 0.45, fontFace: H, fontSize: 20, bold: true, color: INK, margin: 0 });
  s.addText(t, { x: x + 0.25, y: 2.75, w: 2.4, h: 1.2, fontFace: B, fontSize: 12.5, color: MUTED, margin: 0, valign: "top" });
});
s.addText("Ми не будуємо SaaS і не замінюємо саппорт: ми прибираємо з його черги рутину.", { x: 0.5, y: 4.4, w: 9, h: 0.5, fontFace: B, fontSize: 15, italic: true, color: INK, margin: 0 });
s.addNotes("Клієнт це власник кафе або мережі, який користується SaaS (промокоди, каса, підписка). Він пише у підтримку компанії-розробника. Наш AI відповідає, діє з підтвердженням або передає людям.");

// 4. How it works
s = pres.addSlide(); s.background = { color: WHITE };
title(s, "Як це працює");
const steps = [["Звернення", "власник пише як звик"], ["Gemma", "інтент і тон клієнта, вибір інструментів"], ["RAG + логи", "embeddinggemma + Atlas Vector Search; траси подій"], ["Пропозиція", "дія з превʼю і сумою"], ["Підтвердження", "лише власник, одним кліком"], ["Виконання", "атомарно, з перевіркою і аудитом"]];
steps.forEach(([h, t], i) => {
  const x = 0.5 + i * 1.53; card(s, x, 1.55, 1.38, 2.0, i === 4 ? "FFF4E0" : LIGHT);
  dot(s, x + 0.44, 1.7, String(i + 1), i === 4 ? AMBER : "D7DEEA");
  s.addText(h, { x: x + 0.08, y: 2.3, w: 1.22, h: 0.4, fontFace: B, fontSize: 11.5, bold: true, color: INK, align: "center", margin: 0 });
  s.addText(t, { x: x + 0.08, y: 2.7, w: 1.22, h: 0.75, fontFace: B, fontSize: 10.5, color: MUTED, align: "center", margin: 0 });
});
s.addText("Модель лише читає і пропонує. Гроші, права і ізоляція клієнтів контролюються кодом, а не промптом.", { x: 0.5, y: 4.0, w: 9, h: 0.6, fontFace: B, fontSize: 15, italic: true, color: INK, margin: 0 });
s.addNotes("Ключ: агент не має доступу до мутацій. Він пропонує одну з 4 дій, сервер сам перевіряє права, версії ресурсів і суму, а виконання можливе лише після підтвердження власника.");

// 5. Gemma
s = pres.addSlide(); s.background = { color: WHITE };
title(s, "Gemma + RAG: точність і контроль даних");
card(s, 0.5, 1.3, 4.35, 3.6, LIGHT);
s.addText("Gemma", { x: 0.75, y: 1.45, w: 3.9, h: 0.45, fontFace: H, fontSize: 20, bold: true, color: INK, margin: 0 });
s.addText([
  { text: "Агент: Gemma 4 (hosted) з фолбеком на локальну gemma3", options: { bullet: true, breakLine: true } },
  { text: "Ембедінги: embeddinggemma локально через Ollama, текст клієнта не йде стороннім сервісам", options: { bullet: true, breakLine: true } },
  { text: "Витягує з минулих тікетів структуровані знання (symptom, cause, steps)", options: { bullet: true, breakLine: true } },
  { text: "Відкриті ваги: можна розгорнути on-prem у клієнта", options: { bullet: true } },
], { x: 0.75, y: 1.95, w: 3.95, h: 2.8, fontFace: B, fontSize: 12.5, color: INK, paraSpaceAfter: 6, margin: 0, valign: "top" });
card(s, 5.15, 1.3, 4.35, 3.6, LIGHT);
s.addText("RAG", { x: 5.4, y: 1.45, w: 3.9, h: 0.45, fontFace: H, fontSize: 20, bold: true, color: INK, margin: 0 });
s.addText([
  { text: "MongoDB Atlas Vector Search, фільтр по тенанту і інтенту ще до пошуку", options: { bullet: true, breakLine: true } },
  { text: "Агент цитує лише докази з інструментів, вигадані id відкидаються", options: { bullet: true, breakLine: true } },
  { text: "Нові знання з тікетів спершу pending_review і не потрапляють у відповіді без перевірки", options: { bullet: true, breakLine: true } },
  { text: "Менше токенів: у промпт ідуть 4 релевантні фрагменти, а не вся документація", options: { bullet: true } },
], { x: 5.4, y: 1.95, w: 3.95, h: 2.8, fontFace: B, fontSize: 12.5, color: INK, paraSpaceAfter: 6, margin: 0, valign: "top" });
s.addNotes("RAG дає точність (відповідь спирається на джерело) і оптимізацію (короткий контекст замість усієї документації). Атака отруєння бази знань з тікета TCK-1012 не пройде: такі записи чекають перевірки.");

// 6. Demo
s = pres.addSlide(); s.background = { color: LIGHT };
title(s, "Живе демо: три типові звернення");
const demo = [
  ["Промокод не працює на касі", "Gemma знаходить POS_SYNC_FAILED у трасі, бачить версію 6 замість 7, пропонує resync_pos. Після підтвердження чек проходить.", TEAL],
  ["З мене списали двічі", "Знаходить дубль підписки після SUBSCRIPTION_CREATE_RETRY. Окремо: скасувати дубль і подати запит на повернення (pending_review, гроші не рухаються без людини).", RED],
  ["Створи промокод -10% до 10 листопада", "Уточнює ліміт використань, показує превʼю, створює промокод після підтвердження.", AMBER],
];
demo.forEach(([h, t, c], i) => {
  const y = 1.3 + i * 1.02; card(s, 0.5, y, 3.55, 0.92);
  s.addShape(pres.shapes.OVAL, { x: 0.62, y: y + 0.12, w: 0.25, h: 0.25, fill: { color: c } });
  s.addText(h, { x: 0.98, y: y + 0.06, w: 3.0, h: 0.36, fontFace: B, fontSize: 12, bold: true, color: INK, margin: 0, valign: "middle" });
  s.addText(t, { x: 0.62, y: y + 0.42, w: 3.35, h: 0.48, fontFace: B, fontSize: 8, color: MUTED, margin: 0, valign: "top" });
});
// demo clip lives outside the repo (submission/ is gitignored); rebuild needs it on disk
s.addMedia({ type: "video", path: "C:/Workspace/04_Projects/Software/2026-10-31_hackday-lviv-gemma/submission/team14-demo.mp4", x: 4.25, y: 1.3, w: 5.25, h: 2.95 });
s.addText("Демо: промокод на касі → докази → підтвердження → перевірка; роздратований клієнт → пріоритет Високий", { x: 0.5, y: 4.45, w: 9, h: 0.5, fontFace: B, fontSize: 12, bold: true, color: INK, valign: "middle", margin: 0 });
s.addNotes("Демо в браузері: логін tenant_a. Показати докази під відповіддю, картку дії, підтвердження і результат. Для подвійного списання підкреслити: запит на повернення, а не повернення.");

// 7. Safety
s = pres.addSlide(); s.background = { color: WHITE };
title(s, "Безпека: модель пропонує, код вирішує");
const m = [["50", "автотестів зелені"], ["0", "дій без підтвердження власника"], ["2", "тенанти ізольовані на рівні запиту"], ["4", "дії з ідемпотентністю і аудитом"]];
m.forEach(([n, l], i) => {
  const x = 0.5 + i * 2.3; card(s, x, 1.4, 2.1, 1.7, LIGHT);
  s.addText(n, { x, y: 1.5, w: 2.1, h: 0.9, fontFace: H, fontSize: 44, bold: true, color: INK, align: "center", margin: 0 });
  s.addText(l, { x: x + 0.15, y: 2.4, w: 1.8, h: 0.6, fontFace: B, fontSize: 12, color: MUTED, align: "center", margin: 0 });
});
s.addText([
  { text: "Текст клієнта це дані, не інструкції: спроби атаки (TCK-1011) і отруєння бази (TCK-1012) не змінюють поведінку", options: { bullet: true, breakLine: true } },
  { text: "Знання з тікетів спершу pending_review і без перевірки не потрапляють у відповіді", options: { bullet: true, breakLine: true } },
  { text: "Повернення коштів: лише запит на розгляд на повну суму платежу, сума береться з системи, а не з моделі", options: { bullet: true } },
], { x: 0.5, y: 3.4, w: 9, h: 1.3, fontFace: B, fontSize: 13, color: INK, paraSpaceAfter: 6, margin: 0, valign: "top" });
s.addNotes("Сценарій TCK-1010 (людина скасувала обидві підписки і пообіцяла повернення) у нашій системі неможливий: сервер перевіряє, що це справді дубль, а повернення лише реєструється на розгляд.");

// 8. Value
s = pres.addSlide(); s.background = { color: LIGHT };
title(s, "Цінність для компанії-розробника");
s.addChart(pres.charts.BAR, [{ name: "Години саппорту / міс", labels: ["Зараз", "З AI Support Desk"], values: [200, 50] }], {
  x: 0.4, y: 1.25, w: 4.6, h: 3.4, barDir: "col", chartColors: [INK], showValue: true, dataLabelPosition: "outEnd",
  dataLabelColor: INK, dataLabelFontSize: 14, showTitle: true, title: "Години саппорту на 1 000 тікетів/міс", titleFontSize: 12, titleColor: INK,
  catAxisLabelColor: INK, valAxisLabelColor: MUTED, valGridLine: { color: "E2E6EE", size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
});
const stats = [["−150 год", "на місяць ≈ 0,9 FTE"], ["≈ 28 500 грн", "економії щомісяця (≈ 340 тис/рік)"], ["«Зекономлено N хв»", "лічильник у застосунку після кожного звернення"]];
stats.forEach(([n, l], i) => {
  const y = 1.3 + i * 1.08; card(s, 5.3, y, 4.2, 0.92);
  s.addText(n, { x: 5.5, y: y + 0.08, w: 3.9, h: 0.48, fontFace: H, fontSize: i === 2 ? 18 : 24, bold: true, color: i === 2 ? TEAL : INK, margin: 0 });
  s.addText(l, { x: 5.5, y: y + 0.55, w: 3.9, h: 0.3, fontFace: B, fontSize: 12, color: MUTED, margin: 0 });
});
s.addText("Модель: 1 000 тікетів/міс × 12 хв; 75% автоматизовано; 190 грн/год саппорту. Припущення, крім 75% (наш корпус) і 5 с (замір).", { x: 0.5, y: 4.85, w: 9, h: 0.4, fontFace: B, fontSize: 10, color: MUTED, margin: 0 });
s.addNotes("Формула: 1000 × 12 хв = 200 год. 25% залишаються людям = 50 год. Різниця 150 год ≈ 0,9 ставки, при 190 грн/год це ≈ 28,5 тис грн на місяць. Ще ефект для розробників: до них доходять тільки справжні баги зі структурованим тікетом.");

// 9. Roadmap
s = pres.addSlide(); s.background = { color: INK };
title(s, "Дорожня карта", true);
const nx = [["Тікет розробникам", "Якщо дія не допомогла, Gemma збирає готовий баг-репорт: кроки, траса, версії"], ["Gemma-суддя", "Автооцінка 100% закритих звернень замість 5–10% опитувань"], ["Проактивна підтримка", "Побачили POS_SYNC_FAILED у логах і запропонували фікс до того, як клієнт написав"], ["Емоційний тон", "Роздратований клієнт отримує пріоритет і спокійну відповідь з планом"]];
nx.forEach(([h, t], i) => {
  const y = 1.2 + i * 0.88; dot(s, 0.5, y + 0.1, String(i + 1));
  s.addText(h, { x: 1.2, y, w: 8, h: 0.4, fontFace: B, fontSize: 18, bold: true, color: AMBER, margin: 0 });
  s.addText(t, { x: 1.2, y: y + 0.42, w: 8, h: 0.4, fontFace: B, fontSize: 13, color: "D5DBE8", margin: 0 });
});
s.addNotes("Усе це вже має основу в коді: корпус з полем judge, траси з POS_SYNC_FAILED, структуровані записи з тікетів.");

// 10. Next step
s = pres.addSlide(); s.background = { color: INK };
title(s, "Наступний крок", true);
s.addText("Пілот на реальній тікет-системі одного SaaS для закладів", { x: 0.5, y: 1.5, w: 9, h: 1.0, fontFace: H, fontSize: 28, bold: true, color: AMBER, margin: 0 });
s.addText([
  { text: "2 тижні: підключити історію тікетів і документацію, порахувати реальну частку автоматизації", options: { bullet: true, breakLine: true } },
  { text: "Шукаємо: SaaS-партнера з тікетами та ментора з продукту", options: { bullet: true, breakLine: true } },
  { text: "Код: github.com/Ansandr/hackday-lviv-2026-mvp", options: { bullet: true } },
], { x: 0.5, y: 2.7, w: 9, h: 2.0, fontFace: B, fontSize: 16, color: "D5DBE8", paraSpaceAfter: 8, margin: 0, valign: "top" });
s.addNotes("Закінчуємо наступним кроком і проханням, без «дякуємо за увагу».");

pres.writeFile({ fileName: out }).then(f => console.log("wrote", f));

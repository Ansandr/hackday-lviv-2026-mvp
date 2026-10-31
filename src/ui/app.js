const $ = s => document.querySelector(s);
let token = sessionStorage.getItem('support-session'), current = null, busy = false;
const outbox=[];
const labels = {resync_pos:'Синхронізація каси',cancel_duplicate_subscription:'Скасування зайвої підписки',create_promo:'Створення промокоду',create_refund_request:'Запит на повернення коштів'};
const fields = {venue_id:'Заклад',business_id:'Бізнес',subscription_id:'Зайва підписка',retained_subscription_id:'Основна підписка',discount_percent:'Знижка, %',starts_at:'Початок',expires_at:'Діє до',max_redemptions:'Використання',payment_id:'Платіж',related_payment_id:'Пов’язаний платіж',amount_minor:'Сума в мінімальних одиницях',currency:'Валюта',venue_name:'Заклад'};
function el(tag, cls, text){const x=document.createElement(tag); if(cls)x.className=cls;if(text!==undefined)x.textContent=text;return x;}
function error(e){$('#error').textContent=e.message;$('#error').hidden=false;setTimeout(()=>$('#error').hidden=true,8000);}
function setBusy(value,text=''){busy=value;$('#progress').textContent=text;$('#send').disabled=value;$('#new').disabled=value;$('#logout').disabled=value;document.querySelectorAll('.actions button, .suggestions button, .retry-message, .resolution-actions button, .ticket-retry').forEach(b=>b.disabled=value);}
async function api(path, method='GET', body){const r=await fetch('/api/v1'+path,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok){if(r.status===401){token=null;sessionStorage.removeItem('support-session');showLogin();}throw Error(data.error?.message||data.detail?.[0]?.msg||'Не вдалося виконати запит');}return data;}
function showLogin(){$('#login').hidden=false;$('#workspace').hidden=true;}
const priorityNames={low:'Низький',normal:'Звичайний',high:'Високий',urgent:'Критичний'};
const emotionNames={neutral:'Нейтральний',confused:'Потрібне пояснення',frustrated:'Роздратування',angry:'Обурення',worried:'Занепокоєння',positive:'Позитивний',unknown:'Недостатньо даних'};
function showAnalysis(analysis){
  const panel=$('#analysis');panel.replaceChildren();panel.hidden=!analysis;if(!analysis)return;
  const details=el('details','analysis-card'),summary=el('summary','analysis-summary');
  summary.append(el('span','','Аналіз звернення'),el('span','priority-badge '+analysis.priority,'Пріоритет: '+(priorityNames[analysis.priority]||'Звичайний')),el('span','tone-badge','Тон: '+(emotionNames[analysis.customer_tone?.emotion]||'Недостатньо даних')));
  details.append(summary);
  const body=el('div','analysis-body');body.append(el('p','',analysis.priority_reason));
  if(analysis.customer_tone?.rationale)body.append(el('p','',analysis.customer_tone.rationale));
  const impact={none:'Роботу не зупинено',limited:'Окрема проблема',business_blocked:'Повідомлено про зупинку роботи',multiple_venues:'Зачеплено кілька закладів',unknown:'Вплив ще не визначено'};
  const urgency={low:'Низька',normal:'Звичайна',high:'Висока'};
  body.append(el('p','analysis-meta',`${impact[analysis.impact]||impact.unknown} · Терміновість: ${urgency[analysis.urgency]||urgency.normal}`));
  body.append(el('p','analysis-meta',analysis.tone_source==='model'?'Орієнтовна оцінка тону за текстом · Gemma':'Орієнтовна оцінка тону за словами у повідомленні'));
  details.append(body);panel.append(details);
}
async function history(){const list=await api('/conversations?sort='+$('#history-sort').value);$('#history').replaceChildren();for(const c of list){const b=el('button',c.conversation_id===current?'active':'');const p=c.analysis?.priority;if(p&&priorityNames[p]){const dot=el('span','priority-dot '+p);dot.title='Пріоритет: '+priorityNames[p];dot.setAttribute('aria-label',dot.title);b.append(dot);}b.append(el('span','history-title',c.title));b.onclick=()=>!busy&&load(c.conversation_id);$('#history').append(b);}}
function addMessage(m,latest){const box=el('article','message '+m.role);if(m.role==='assistant')box.append(el('div','author','ЛІНІЯ · ПІДТРИМКА'));box.append(el('div','text',SupportPresentation.text(m.text)));const t=m.turn;if(t){for(const q of t.questions||[]){box.append(el('p','question',q.prompt));if(q.options)for(const option of q.options){const b=el('button','',option);b.onclick=()=>send(option);box.append(b);}}
if(t.questions?.some(q=>q.field==='promo')){const b=el('button','','Заповнити приклад параметрів');b.onclick=()=>{$('#message').value=JSON.stringify({venue_id:'venue_01',discount_percent:20,starts_at:new Date().toISOString(),expires_at:new Date(Date.now()+7*86400000).toISOString(),max_redemptions:100},null,2);$('#message').focus();};box.append(b);}
if(t.evidence?.length){const d=el('details','card'),s=el('summary','card-title','Що ми перевірили · '+t.evidence.length);d.append(s);const body=el('div','card-body');for(const e of t.evidence)body.append(el('span','evidence',`${e.kind==='kb'?'Правила сервісу':'Історія роботи'}\n${SupportPresentation.evidence(e)}`));d.append(body);box.append(d);}
if(t.proposed_action){const a=t.proposed_action,card=el('div','card');card.append(el('div','card-title',labels[a.type]||a.type));const body=el('div','card-body');body.append(el('div','',a.summary));const dl=el('dl','params');for(const [k,v] of Object.entries({...a.parameters,...a.preview})){if(k==='demo'||(k==='venue_id'&&a.preview?.venue_name))continue;dl.append(el('dt','',fields[k]||k),el('dd','',SupportPresentation.parameter(k,v)));}body.append(dl,el('div','evidence','Дійсна до '+new Date(a.expires_at).toLocaleTimeString('uk-UA')));if(a.type==='create_refund_request')body.append(el('p','','Це запит на розгляд. Гроші автоматично не повертаються.'));if(latest){const buttons=el('div','actions');for(const [decision,title] of [['confirm','Підтвердити'],['reject','Відмовитися']]){const b=el('button',decision,title);b.onclick=()=>decide(a.action_id,decision);buttons.append(b);}body.append(buttons);}else body.append(el('div','evidence','Попередня пропозиція · перегляньте актуальний стан розмови'));card.append(body);box.append(card);}
if(t.resolution_prompt){
 const prompt=t.resolution_prompt,card=el('div','card resolution-card');card.append(el('div','card-title',prompt.question));
 const body=el('div','card-body');
 if(latest){
  const comment=el('textarea','resolution-comment');comment.rows=2;comment.maxLength=2000;comment.placeholder='Що залишилося невирішеним? (необов’язково)';comment.setAttribute('aria-label','Коментар до результату');
  body.append(comment,el('p','evidence','Якщо проблема залишилася, передамо опис і діагностику команді в Telegram.'));
  const buttons=el('div','actions resolution-actions');
  for(const [resolved,title] of [[true,'Так, вирішено'],[false,'Ні, створити тікет']]){const b=el('button',resolved?'confirm':'',title);b.type='button';b.onclick=()=>feedback(prompt.prompt_id,resolved,comment.value);buttons.append(b);}body.append(buttons);
 }else body.append(el('div','evidence','Подальша відповідь збережена в історії розмови.'));
 card.append(body);box.append(card);
}
if(t.support_ticket){
 const ticket=t.support_ticket,card=el('div','card');card.append(el('div','card-title','Тікет '+ticket.ticket_id));const body=el('div','card-body');
 const d=ticket.delivery||{};
 const deliveryText=d.status==='sent'?`Надіслано команді в Telegram: ${d.delivered} із ${d.recipients}.`:d.uncertain?'Тікет збережено. Статус частини відправлень потребує перевірки; автоматичного дублювання не буде.':d.status==='partial'?`Тікет збережено. Надіслано ${d.delivered} із ${d.recipients}; решту можна надіслати повторно.`:'Тікет збережено. Надсилання в Telegram ще не завершене.';
 body.append(el('p','',deliveryText));
 if(d.status!=='sent'&&!d.uncertain){const b=el('button','ticket-retry','Повторити надсилання');b.type='button';b.onclick=()=>retryTicket(ticket.ticket_id);body.append(b);}card.append(body);box.append(card);
}
if(t.action_result){const a=t.action_result;const names={succeeded:'Виконано',failed:'Не виконано',rejected:'Відхилено',expired:'Пропозиція застаріла',executing:'Перевіряємо результат'};let text=names[a.status]||a.status;if(a.result){if(a.result.after.demo)text='Демонстрація завершена';else text+=' · '+a.result.resource_id;if(a.result.type==='create_refund_request')text+=' · Очікує розгляду';}if(a.error)text+='\n'+a.error.message;box.append(el('div','result',text));}}
$('#thread').append(box);return box;}
function scrollThread(){$('#thread').scrollTop=$('#thread').scrollHeight;}
function renderOutgoing(entry){
  const box=addMessage({role:'user',text:entry.text},false);
  box.classList.add('outgoing');box.dataset.clientMessageId=entry.client_message_id;
  entry.element=box;updateOutgoing(entry);return box;
}
function updateOutgoing(entry){
  const box=entry.element;if(!box?.isConnected)return;
  box.querySelector('.delivery-status')?.remove();
  const status=el('div','delivery-status');status.setAttribute('role','status');
  if(entry.status==='failed'){
    status.append(el('span','delivery-error',entry.error||'Не вдалося отримати відповідь.'));
    const retry=el('button','retry-message','Повторити');retry.type='button';retry.onclick=()=>!busy&&deliver(entry);status.append(retry);
  }else status.textContent=entry.status==='sent'?'Надіслано':'Очікуємо відповіді';
  box.append(status);
}
function waiting(show){
  $('#agent-waiting')?.remove();
  if(show){const node=el('div','agent-waiting','Лінія готує відповідь…');node.id='agent-waiting';node.setAttribute('role','status');$('#thread').append(node);}
}
async function load(id){current=id;const c=await api('/conversations/'+id);showAnalysis(c.analysis||c.latest_turn?.analysis);const local=outbox.filter(e=>e.conversation_id===id);$('#welcome').hidden=c.messages.length>0||local.length>0;$('#thread').replaceChildren();c.messages.forEach((m,i)=>addMessage(m,i===c.messages.length-1));local.forEach(renderOutgoing);scrollThread();await history().catch(error);}
async function create(){const c=await api('/conversations','POST',{});await load(c.conversation_id);}
async function enter(){await history();$('#login').hidden=true;$('#workspace').hidden=false;const list=await api('/conversations');if(list.length)await load(list[0].conversation_id);else await create();}
async function send(text){
  if(busy||!text.trim())return;
  const entry={client_message_id:crypto.randomUUID(),text,conversation_id:current,status:'sending'};
  outbox.push(entry);$('#message').value='';$('#welcome').hidden=true;renderOutgoing(entry);$('#message').focus();
  await deliver(entry);
}
async function deliver(entry){
  if(busy)return;
  entry.status='sending';entry.error=null;updateOutgoing(entry);setBusy(true,'');waiting(true);scrollThread();
  try{
    if(!entry.conversation_id){const c=await api('/conversations','POST',{});current=entry.conversation_id=c.conversation_id;}
    const turn=await api('/conversations/'+entry.conversation_id+'/messages','POST',{client_message_id:entry.client_message_id,text:entry.text});
    entry.status='sent';updateOutgoing(entry);const index=outbox.indexOf(entry);if(index>=0)outbox.splice(index,1);waiting(false);
    try{await load(entry.conversation_id);}catch{
      // The reply already arrived. A failed history refresh must not mark it as unsent.
      addMessage({role:'assistant',text:turn.reply,turn},true);showAnalysis(turn.analysis);history().catch(error);
    }
  }catch(e){entry.status='failed';entry.error=e.message;updateOutgoing(entry);if(token&&entry.conversation_id===current){try{const c=await api('/conversations/'+current);showAnalysis(c.analysis);}catch{}}}
  finally{waiting(false);setBusy(false);scrollThread();}
}
async function decide(id,decision){if(busy)return;setBusy(true,decision==='confirm'?'Виконуємо дію та перевіряємо результат…':'Відхиляємо пропозицію…');try{await api('/actions/'+id+'/confirm','POST',{decision});await load(current);}catch(e){error(e);$('#progress').textContent='Повторне підтвердження безпечне: використовується той самий ID дії.';}finally{setBusy(false);}}
$('#login-form').onsubmit=async e=>{e.preventDefault();try{const result=await api('/session','POST',{token:$('#access').value});token=result.access_token;sessionStorage.setItem('support-session',token);$('#access').value='';$('#identity').textContent=result.identity.tenant_id;await enter();}catch(err){error(err);}};
$('#composer').onsubmit=e=>{e.preventDefault();send($('#message').value);};
$('#message').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send($('#message').value);}};
$('#new').onclick=()=>{if(!busy)create().catch(error);};
$('#logout').onclick=async()=>{try{await api('/session','DELETE');}catch{}token=null;current=null;outbox.length=0;sessionStorage.removeItem('support-session');$('#history').replaceChildren();showLogin();};
document.querySelectorAll('[data-prompt]').forEach(b=>b.onclick=()=>send(b.dataset.prompt));
api('/health').then(h=>{$('#mode').textContent=h.mode==='demo'?'ДЕМО · без AI':h.mode==='integrated'?'GEMMA · підключення':'АГЕНТ';$('#demo-hint').hidden=h.mode!=='demo';}).catch(error);
if(token)enter().catch(error);

$('#history-sort').onchange=()=>history().catch(error);

async function feedback(promptId,resolved,comment){
 if(busy)return;setBusy(true,resolved?'Зберігаємо підтвердження…':'Формуємо тікет і надсилаємо діагностику команді…');
 try{await api('/conversations/'+current+'/feedback','POST',{prompt_id:promptId,resolved,comment});await load(current);}catch(e){error(e);}finally{setBusy(false);}
}
async function retryTicket(id){
 if(busy)return;setBusy(true,'Перевіряємо надсилання тікета…');
 try{await api('/tickets/'+id+'/delivery','POST',{});await load(current);}catch(e){error(e);}finally{setBusy(false);}
}

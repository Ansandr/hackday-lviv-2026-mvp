/* Pure display helpers; all rendering still uses textContent. */
(function(root){
  const events={
    PROMO_CACHE_MISS:'Каса не знайшла актуальні дані промокоду та звернулася до сервера.',
    PROMO_LOOKUP_OK:'Сервер знайшов промокод і підтвердив, що він активний.',
    POS_SYNC_FAILED:'Оновлення не дійшло до каси через збій синхронізації.',
    SUBSCRIPTION_CREATE_RETRY:'Повторний запит створив ще одну підписку. Це могло спричинити зайве списання.'
  };
  function text(value){return String(value??'').replace(/<!--[\s\S]*?-->/g,'').replace(/^#{1,6}\s*/gm,'').replace(/\*\*|`/g,'').trim();}
  function evidence(item){
    for(const [code,summary] of Object.entries(events))if(item.summary.startsWith(code))return summary;
    const clean=text(item.summary);
    if(item.kind==='kb')return clean.split('\n').find(line=>line.trim())?.slice(0,220)||'Перевірено правила сервісу для цього питання.';
    return clean.replace(/\s*·\s*\{[\s\S]*$/,'')||'Перевірено пов’язану подію в історії сервісу.';
  }
  function parameter(key,value){
    if(key==='max_redemptions' && value===null)return 'Без обмежень';
    if((key==='starts_at'||key==='expires_at') && value){
      const date=new Date(value);
      if(!Number.isNaN(date.getTime()))return new Intl.DateTimeFormat('uk-UA',{dateStyle:'long',timeStyle:'short',timeZone:'Europe/Kyiv'}).format(key==='expires_at'?new Date(date.getTime()-1):date);
    }
    return typeof value==='object'?text(JSON.stringify(value)):String(value);
  }
  const api={text,evidence,parameter};root.SupportPresentation=api;
  if(typeof module!=='undefined')module.exports=api;
})(globalThis);

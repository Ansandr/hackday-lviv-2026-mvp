"""User-facing evidence summaries. Internal identifiers stay available to the dispatcher."""
import re

from src.support.models import Evidence


EVENTS={
    'PROMO_CACHE_MISS':'Каса не знайшла актуальні дані промокоду та звернулася до сервера.',
    'PROMO_LOOKUP_OK':'Сервер знайшов промокод і підтвердив, що він активний.',
    'POS_SYNC_FAILED':'Оновлення даних не дійшло до каси через збій синхронізації.',
    'SUBSCRIPTION_CREATE_RETRY':'Запит на підписку повторився. У системі з’явилася друга підписка.',
}


def log_evidence(event):
    return Evidence(kind='log',id=event['log_id'],summary=EVENTS.get(event['event'],'Перевірено пов’язану подію в історії роботи сервісу.'))


def kb_evidence(hit):
    text=re.sub(r'<!--[\s\S]*?-->','',hit['text'])
    headings=re.findall(r'^#{1,3}\s+(.+)',text,re.M)
    title=headings[0] if headings else next((line.strip() for line in text.splitlines() if line.strip()),'Правила сервісу')
    title=re.sub(r'[*`_\[\]]','',title)
    if title=='Коди подій у логах': title='Як зрозуміти причину помилки за історією роботи сервісу'
    return Evidence(kind='kb',id=hit['kb_id'],summary=title[:250])

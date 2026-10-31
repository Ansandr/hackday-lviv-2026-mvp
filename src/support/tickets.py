"""Persistent escalation bundles and explicit Telegram delivery receipts."""
import json
import os
import re
import hashlib
from datetime import datetime,timezone
from uuid import uuid4

import httpx


class DeliveryRejected(Exception): pass
class DeliveryUnknown(Exception): pass


def parse_resolution(text):
    clean=text.strip().lower().rstrip('.!')
    if clean in ('так','так, вирішено','так вирішено','вирішено','все працює','так, дякую','yes'):
        return True,''
    if clean in ('не допомогло','не вирішено','проблема залишилась','проблема залишилася'):
        return False,text.strip()
    match=re.match(r'^(ні|no)\b[\s,.:!-]*(.*)$',text.strip(),re.I|re.S)
    return (False,match[2].strip()) if match else None


def redact(value):
    if isinstance(value,dict):
        return {k:('[REDACTED]' if re.search(r'token|secret|password|api_key|authorization|card_number|cvv',k,re.I) else redact(v)) for k,v in value.items()}
    if isinstance(value,list):return [redact(v) for v in value]
    if not isinstance(value,str):return value
    value=re.sub(r'\b\d{6,}:[A-Za-z0-9_-]{20,}\b','[TOKEN]',value)
    value=re.sub(r'[\w.+-]+@[\w.-]+\.[\w]+','[EMAIL]',value)
    value=re.sub(r'\+380[\d ()-]{9,15}','[PHONE]',value)
    return re.sub(r'\b(?:\d[ -]?){16}\b','[CARD]',value)


def caption(ticket):
    priority={'low':'Низький','normal':'Звичайний','high':'Високий','urgent':'Критичний'}
    tone={'neutral':'Нейтральний','confused':'Потребує пояснення','frustrated':'Роздратування','angry':'Обурення','worried':'Занепокоєння','positive':'Позитивний','unknown':'Не визначено'}
    a=ticket.get('analysis') or {}
    text=(f"Новий тікет {ticket['ticket_id']}\n"
          f"Пріоритет: {priority.get(a.get('priority'),'Не визначено')}\n"
          f"Тон клієнта: {tone.get(a.get('customer_tone',{}).get('emotion'),'Не визначено')}\n\n"
          f"Тема: {ticket['title'][:150]}\n"
          f"Що не вирішено: {ticket['description'][:350]}\n\n"
          f"Виконаних/запропонованих дій: {len(ticket['actions'])}\n"
          f"Логів: {len(ticket['diagnostics'].get('logs',[]))}; джерел: {len(ticket['evidence'])}\n"
          'Повний опис, історія та діагностика — у файлі.')
    return text[:1000]


class TelegramSender:
    def targets(self):
        try:
            ids=json.loads(os.getenv('TELEGRAM_CHAT_IDS','[]'))
            if not isinstance(ids,list):return []
            return list(dict.fromkeys(str(x) for x in ids))
        except ValueError:return []

    def send(self,chat_id,ticket):
        token=os.getenv('TELEGRAM_BOT_TOKEN','')
        if not token: raise DeliveryRejected('Telegram is not configured')
        payload={k:v for k,v in ticket.items() if k!='delivery'}
        document=json.dumps(payload,ensure_ascii=False,indent=2).encode('utf-8')
        try:
            with httpx.Client(timeout=12) as client:
                response=client.post('https://api.telegram.org/bot'+token+'/sendDocument',data={'chat_id':chat_id,'caption':caption(ticket)},files={'document':(ticket['ticket_id']+'.json',document,'application/json')})
            if 400<=response.status_code<500:raise DeliveryRejected('Telegram rejected delivery')
            if response.status_code>=500:raise DeliveryUnknown('Telegram outcome is unknown')
            data=response.json()
            if not data.get('ok'):raise DeliveryRejected('Telegram rejected delivery')
            return str(data['result']['message_id'])
        except httpx.ConnectError as exc:raise DeliveryRejected('Telegram connection failed') from exc
        except (httpx.HTTPError,ValueError,KeyError) as exc:raise DeliveryUnknown('Telegram outcome is unknown') from exc


class Tickets:
    def __init__(self,store,sender=None):
        self.store=store;self.sender=sender or TelegramSender()

    def build(self,ctx,conversation,prompt_id,comment,bridge):
        ticket_id='TCK-'+hashlib.sha256((ctx.tenant_id+':'+conversation['conversation_id']+':'+prompt_id).encode()).hexdigest()[:12].upper()
        existing=self.store.get('ticket',ticket_id,ctx.tenant_id)
        if existing:return existing
        evidence={}
        for message in conversation['messages']:
            for item in (message.get('turn') or {}).get('evidence',[]):evidence[(item['kind'],item['id'])]=item
        actions=[a for a in self.store.list('action',ctx.tenant_id) if a['conversation_id']==conversation['conversation_id']]
        for action in actions:
            # No adapter secrets or arbitrary service headers belong in a ticket.
            action.pop('preconditions',None)
        diagnostics={'logs':[],'facts':{},'context_status':'not_available'}
        if hasattr(bridge,'escalation_context'):
            try:diagnostics=bridge.escalation_context(ctx,[e['id'] for e in evidence.values()],actions)
            except Exception:diagnostics['context_status']='unavailable'
        users=[m['text'] for m in conversation['messages'] if m['role']=='user']
        now=datetime.now(timezone.utc).isoformat()
        ticket=redact({'ticket_id':ticket_id,'tenant_id':ctx.tenant_id,'actor_id':ctx.actor_id,'conversation_id':conversation['conversation_id'],'prompt_id':prompt_id,'status':'open','title':conversation['title'],'description':comment.strip() or 'Клієнт підтвердив, що проблему не вирішено після запропонованих кроків.','original_request':users[0] if users else '', 'analysis':conversation.get('analysis'),'evidence':list(evidence.values()),'actions':actions,'diagnostics':diagnostics,'history':[{'role':m['role'],'text':m['text'][:4000],'created_at':m['created_at']} for m in conversation['messages'][-24:]],'created_at':now})
        ticket['delivery']={'targets':{target:{'status':'pending'} for target in self.sender.targets()}}
        self.save(ticket)
        return ticket

    def save(self,ticket):self.store.put('ticket',ticket['ticket_id'],ticket['tenant_id'],ticket)

    def deliver(self,ticket):
        # Never resend a successful or uncertain send. Telegram has no idempotency key.
        for target in self.sender.targets():ticket['delivery']['targets'].setdefault(target,{'status':'pending'})
        for target,receipt in ticket['delivery']['targets'].items():
            if receipt['status'] in ('sent','sending','unknown'):continue
            receipt['status']='sending';self.save(ticket)
            try:
                receipt.update(status='sent',message_id=self.sender.send(target,ticket))
            except DeliveryRejected:receipt.update(status='failed')
            except Exception:receipt.update(status='unknown')
            self.save(ticket)
        return self.summary(ticket)

    @staticmethod
    def summary(ticket):
        targets=list(ticket['delivery']['targets'].values())
        delivered=sum(t['status']=='sent' for t in targets)
        uncertain=any(t['status'] in ('sending','unknown') for t in targets)
        status='sent' if targets and delivered==len(targets) else 'partial' if delivered else 'unknown' if uncertain else 'failed' if targets else 'pending'
        return {'ticket_id':ticket['ticket_id'],'status':ticket['status'],'delivery':{'status':status,'delivered':delivered,'recipients':len(targets),'uncertain':uncertain}}

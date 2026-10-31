"""Priority follows reported operational impact, never emotion or model authority."""
import re

from .models import CustomerTone, TicketAnalysis


PRIORITY_ORDER={'urgent':0,'high':1,'normal':2,'low':3}


def rule_tone(text):
    text=text.lower()
    patterns=[
        ('angry',r'бісить|обурен|неприпустимо|знущає|жахливо|furious|unacceptable','negative','У повідомленні є явне обурення.'),
        ('frustrated',r'набрид|дратує|вкотре|втретє|знову не|frustrat','negative','Клієнт висловлює роздратування через повторну або тривалу проблему.'),
        ('worried',r'хвилю|боюс|боюся|переживаю|worried|afraid','negative','У тексті є занепокоєння щодо ситуації.'),
        ('confused',r'не розумію|не зрозумі|заплутав|confused|don.t understand','neutral','Клієнту потрібне зрозуміле пояснення.'),
        ('positive',r'дякую|чудово|супер|thank|great','positive','Клієнт висловлює вдячність або задоволення.'),
    ]
    for emotion,pattern,sentiment,rationale in patterns:
        if re.search(pattern,text):
            return CustomerTone(emotion=emotion,sentiment=sentiment,rationale=rationale)
    return CustomerTone(emotion='neutral',sentiment='neutral',rationale='Явних емоційних сигналів у повідомленні не виявлено.')


def assess(messages, model_tone=None):
    users=[m['text'].lower() for m in messages if m['role']=='user']
    latest=users[-1] if users else ''
    # Preserve the reported issue through short clarification replies.
    text=' '.join(users[-4:])
    resolved=bool(re.search(r'вже працює|все працює|питання вирішено|все добре|fixed now',latest))
    blocked=bool(re.search(r'продажі зупини|не можемо обслуговувати|не можемо приймати оплат|каси не працюють|каса не працює|бізнес зупини|sales stopped|cannot accept payments',text)) and not resolved
    multiple=bool(re.search(r'всіх заклад|всі заклади|усіх заклад|усі заклади|всій мережі|all venues',text)) and not resolved
    queue=bool(re.search(r'клієнти чекають|черга на касі|стоїть черга|customers waiting',text)) and not resolved
    urgent=bool(re.search(r'терміново|негайно|прямо зараз|urgently|immediately',latest)) and not re.search(r'не\s+терміново|not urgent',latest) and not resolved
    billing=bool(re.search(r'подвійн.{0,20}спис|двічі.{0,30}спис|двічі.{0,20}зня|списали.{0,20}двічі|double charg',text)) and not resolved
    howto=bool(re.search(r'створ.{0,30}промокод|як.{0,20}промокод',text))
    if blocked and (multiple or queue):
        priority='urgent';reason='За повідомленням клієнта, робота зупинилася й зачеплено мережу або клієнтів у черзі.'
    elif blocked or billing or (multiple and urgent):
        priority='high';reason='Потрібна швидка перевірка: клієнт повідомляє про зупинку роботи або фінансову проблему.' if blocked or billing else 'Клієнт повідомляє про термінову проблему в кількох закладах.'
    elif howto and not urgent:
        priority='low';reason='Консультаційний запит без повідомлення про зупинку роботи.'
    else:
        priority='normal';reason='Немає повідомлення про критичний вплив на роботу або подвійне списання.'
    if resolved:
        priority='low';reason='Клієнт повідомив, що проблему вирішено.'
    impact='multiple_venues' if multiple else 'business_blocked' if blocked else 'none' if howto or resolved else 'limited'
    lexical=rule_tone(latest)
    # A neutral/unknown model answer must not erase an explicit phrase such as "не розумію".
    use_model=model_tone is not None and (model_tone.emotion not in ('neutral','unknown') or lexical.emotion=='neutral')
    tone=model_tone if use_model else lexical
    return TicketAnalysis(priority=priority,urgency='high' if urgent or queue or blocked else 'low' if priority=='low' else 'normal',impact=impact,priority_reason=reason,customer_tone=tone,tone_source='model' if use_model else 'rules')

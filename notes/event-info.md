# Hacktoberfest Hack Day Lviv — Gemma MVP kit

- Event: PolyTech Code Fest x SKELAR, Sat 2026-10-31. **Venue (per organizers' Telegram, supersedes the MLH page):**
  Viking Business Center (SKELAR office), Zelena St 151, Lviv - https://share.google/gbr6awJSYOCn2y4dK
- 30 teams (already formed, solo included). Team list + **confirm attendance** in the sheet:
  https://docs.google.com/spreadsheets/d/1R4PCwX641ki-goUFiDHjSg1fHrhxmkNirdz-UlymkvA/edit?usp=sharing
- Contact: @alinaskelar (Telegram). Bring laptop + charger. Challenge revealed at the briefing; no pre-built solutions needed.

## Schedule (organizers' Telegram - the MLH page times are outdated)
| Time | What |
|---|---|
| 09:00 | Registration, breakfast |
| 11:15-17:00 | Build MVP |
| 12:00-16:30 | Mentor sessions (20 min, max 2 per team; sign-up sheet posted on the day) |
| **17:00** | **MVP submission deadline** (format given on the day) |
| 17:55 | TOP-15 announced (pizza + networking while judged) |
| 18:00 | Finalist pitches: 5 min + 2-3 min Q&A (non-finalists can watch) |
| 21:00 | Awards |

## SKELAR scholarship (separate from results)
10,000 UAH/month x 10 months. **Must fill the form** (link will be posted in the chat). Reviewed 2-3 weeks after
the event using profile + MVP; winning / TOP-15 does not guarantee it. Keep your GitHub profile and MVP repo tidy.

Calendar: import `hackday-lviv-2026.ics` (Europe/Kyiv time zone).

## Why Gemma?
Gemma is Google's open-weight model family; MLH has a "Build with Gemma" partner page and the
event lists it as a recommended resource. No Gemma-specific prize/requirement is stated on the
event page — it is a suggested toolkit, not a mandate. Confirm at the opening ceremony.

## Quick start (5 min)
1. Get a key: https://aistudio.google.com/apikey → copy `.env.example` to `.env`, paste it.
2. `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt`
3. `python src/hello_gemma.py` (hosted, Gemini API)
4. Optional local/offline: install Ollama, `ollama pull gemma3:4b` (or a Gemma 4 tag if available),
   then `python src/hello_local.py`.

## Layout
- `src/hello_gemma.py` – hosted call via Gemini API
- `src/hello_local.py` – local call via Ollama
- `src/tools_demo.py` – function-calling skeleton
- `notes/gemma-cheatsheet.md` – models, IDs, links
- `notes/mvp-playbook.md` – hour-by-hour plan + pitch template

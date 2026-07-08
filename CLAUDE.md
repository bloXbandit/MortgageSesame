# CLAUDE.md — MortgageSesame Operating Manual

AI mortgage acquisition OS for a solo mortgage banker (NMLS #1454510, MD/DC).
Architecture, API reference, and campaign-engine walkthrough live in [README.md](README.md) — read it before backend work. This file covers what the README doesn't: conventions, tripwires, quality bars, and when to stop and ask.

**One rule above all others: nothing sends externally without human approval.** Email, SMS, direct mail, social posts, agent actions — everything queues for review. Never write code that bypasses the approval queue, the suppression check, or the compliance service. This is a regulated industry (TCPA, RESPA, NMLS advertising rules); a "helpful shortcut" here is a legal violation.

## Environment facts (verified, don't trust the README on these)

- **Python is 3.9.6** (`backend/.venv`), not 3.11+ as the README claims. No `match` statements, no `X | None` unions — use `Optional[X]`. `list[dict]` builtin generics are OK (3.9+).
- **The live database is `backend/mortgagesesame.db`** (no underscore). `backend/mortgage_sesame.db` is an empty stale artifact — never read or write it. The live DB contains real data; never delete it without asking.
- **There are no tests.** Verification means running the thing (see quality bars below), not `pytest`.
- Run everything with `make dev` (backend :8000, public-site :5173, admin-app :5174). API docs at `localhost:8000/docs` in dev.

## Backend conventions (FastAPI, `backend/`)

- **No `schemas/` files, no `response_model`.** The `app/schemas/` dir is empty on purpose. Request bodies are inline Pydantic `BaseModel` classes at the top of each router; responses are plain dicts built by a module-level `_thing_dict(obj)` serializer (see `app/routers/listings.py` for the canonical shape). Follow this — don't introduce a schemas layer.
- Async SQLAlchemy 2.0 everywhere: `select()` + `await db.execute()` + `.scalar_one_or_none()` / `.scalars().all()`. `db: AsyncSession = Depends(get_db)`.
- Datetimes serialize as `obj.created_at.isoformat() if obj.created_at else None`.
- Auth is a deliberate three-way choice per endpoint: public (no dep), `get_current_user` (admin JWT), or `require_agent_key` (agent API key OR admin JWT — see `app/middleware/auth.py`). State which one you chose and why.
- New routers: `APIRouter(prefix="/x", tags=["x"])`, then register in `backend/main.py` with `prefix="/api/v1"`. Only the QR redirect `/r/{code}` lives at root.
- Config: every external key or mode switch is a field in `app/config.py` (pydantic Settings) with a safe default (`""` or `"mock"`), plus a line in `backend/.env.example`. Never read `os.environ` directly, never hardcode a key or URL.
- External services go through the provider layer (`app/services/providers/`: base interface → implementation → `registry.py`), selected by env var, **mock by default**. Never call a provider SDK/API directly from a router.
- Logging: `structlog`, dotted event names — `log.info("admin_seed.created", email=...)`, not f-strings.

## Frontend conventions (`admin-app/`, `public-site/`)

- React 18 + JSX (no TypeScript), Tailwind v4, `lucide-react` icons, `react-hot-toast` for errors/success, react-router 6.
- **All HTTP goes through `admin-app/src/utils/api.js`** (`api.get/post/patch/del`). Never use raw `fetch` or hardcode `localhost:8000` in a component — the base URL is resolved at runtime differently for Electron, iOS/Capacitor, and browser dev, and hardcoding breaks two of the three targets.
- The admin app renders in **three targets: browser, Electron, iOS WebView**. No Node APIs in `src/` (Node is allowed only in `admin-app/electron/`). No browser APIs that don't exist in a WKWebView. Assume the backend may be on another machine (iOS talks to the Mac over WiFi).
- New pages: component in `src/pages/`, route in `App.jsx`, nav entry where the other pages have one.

## Named mistakes and the rule that prevents each

1. **"I added a column to the model but the API 500s."** Dev startup uses `Base.metadata.create_all`, which creates missing *tables* but never alters existing ones. After any model change: apply the column to the live SQLite DB (`ALTER TABLE` or an alembic migration), then verify with `sqlite3 backend/mortgagesesame.db "PRAGMA table_info(<table>);"`.
2. **Writing Python 3.10+ syntax.** The venv is 3.9. If you use `X | None` in an annotation that's evaluated at runtime (Pydantic models, FastAPI signatures), the server won't boot.
3. **Bypassing `api.js`.** A raw `fetch('http://localhost:8000/...')` works in browser dev and silently breaks the Electron and iOS builds. Always `import { api } from '../utils/api'`.
4. **Sending without the gate.** Any code path that emits content externally must (a) check DNC/suppression, (b) pass `services/compliance.py`, (c) land in the approval queue as a draft — in that order. If a task seems to require skipping one, it doesn't; ask instead.
5. **Calling a provider directly.** New integration = new provider class behind the `base.py` interface + registry entry + `mock` default + config fields. A router importing `resend` or `twilio` directly is wrong even if it works.
6. **Inventing a schemas/ layer or `response_model`s.** Matches FastAPI tutorials, doesn't match this repo. Inline request models + `_dict()` serializers.
7. **Forgetting registration.** A new router that isn't added to `main.py` (or a page not added to `App.jsx`) fails silently — no error, just a 404. Registration is part of the change, not a follow-up.
8. **Editing generated output instead of the generator.** Outreach HTML/scripts come from `campaign_writer.py` and `mail_templates.py`. Fix the template/generator, not a stored draft.
9. **Dropping the compliance boilerplate.** Every outward-facing template needs: NMLS #1454510, Equal Housing Lender, rates labeled *illustrative*; direct mail additionally needs the ADVERTISEMENT header and NOT A CHECK disclaimer. Copying a template to make a new one and trimming "clutter" removes legally required text.

## Quality bar — a change is done when (checkable, per deliverable)

**Any backend change**
- [ ] `uvicorn main:app` boots with zero errors/warnings-you-caused (imports, model conflicts).
- [ ] The specific endpoint was exercised against the running server (curl or `/docs`) and the actual JSON response was inspected — not assumed.
- [ ] Bad input returns a 4xx with a useful `detail`, not a 500.

**New/changed model**
- [ ] `PRAGMA table_info` on the live DB confirms the columns exist.
- [ ] Serializer (`_dict()`) updated to include new fields.

**New/changed admin page or component**
- [ ] Renders at `localhost:5174` with real backend data (not just "compiles").
- [ ] Errors surface as toasts, not silent console noise.
- [ ] No raw `fetch`, no Node APIs, no hardcoded URLs.

**Anything generating outreach/marketing content**
- [ ] Compliance boilerplate present (rule 9 above).
- [ ] `services/compliance.py` check passes on sample output.
- [ ] Output lands as a draft in the approval queue; nothing auto-sends.

**Agent API changes**
- [ ] Endpoint documented in `agent/tool_contracts.md` (that file is the contract the external agent reads).
- [ ] Action logged to `AgentAction`/`AuditLog`; outbound effects queue for approval.

## When uncertain — exact escalation rules

**Stop and ask before:**
- Switching any provider off `mock`, or any change that could cause a real email/SMS/mail/social post to leave the system.
- Deleting or regenerating `backend/mortgagesesame.db`.
- Weakening anything in `services/compliance.py` or removing required disclosures, even if asked to "clean up" a template.
- Changing auth (JWT logic, `require_agent_key`, token lifetimes) or CORS beyond adding a dev origin.
- Alembic migrations intended for production.

**Proceed without asking:** new endpoints/pages following the conventions above, bug fixes, mock-provider work, refactors that keep behavior, dev-DB column additions.

**When the README and the code disagree, the code wins** — note the discrepancy in your summary. When a convention is ambiguous, find the most recently touched similar file and copy its pattern.

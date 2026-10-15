# Directory Refactoring Blueprint — Course FIT HCMUS Notification Bot

> **Status:** Proposal (no code moved yet) · **Date:** 2026-10-14
> **Scope:** Python backend (`src/`, `api/`, `scripts/`, `tests/`), repo root hygiene, and light-touch changes to `frontend/`.

## 0. Project Context

| Item | Value |
|---|---|
| Backend | Python 3.10, no web framework. It uses `http.server.BaseHTTPRequestHandler` on Vercel, and `requests` + `psycopg2` against Supabase PostgreSQL. |
| Frontend | React 18 + TypeScript + Vite 6 + Tailwind 3 in `frontend/` |
| Runtimes | **(A) Scheduled jobs:** `python main.py --<mode>` run by GitHub Actions cron, Termux cron and Termux widgets. **(B) Serverless HTTP:** Vercel calls `api/index.py` for slash commands, the dashboard API and the external API. |
| Scope | Personal/small-group production tool, ~4.3k LOC Python and ~30 TSX files |
| Import style | Absolute `from src.<module> import ...`. Every entry point (`api/*`, `scripts/*`, `tests/*`) adds the repo root with `sys.path.insert(0, ...)`. No package install. |
| Tests | Dedicated `tests/` root. Pytest unit tests are mixed with interactive or live-token scripts. |
| Target architecture | Layered shared core, plus **runtime-oriented entry modules** (`jobs/` for cron, `web/` for Vercel). Inside the layers, files are grouped by integration or feature. |

**The main design insight:** the real boundary in this system is the **deployment target**, not the business feature. Vercel must bundle only what HTTP handlers need. Cron jobs can import everything. Today that boundary is kept by a hand-maintained file list in `.vercelignore`, and it is already broken (see A1). The new structure makes the boundary a **directory**.

---

## 1. Current State Audit

### 1.1 Architectural issues

| # | Issue | Evidence | Impact |
|---|---|---|---|
| **A1** | **Vercel bundle boundary is broken.** `.vercelignore` excludes `src/moodle_parser.py`, but the HTTP API imports it. | `api/index.py:82` lazy-imports `get_current_semester` from `src.moodle_parser` | `GET /api/stats` very likely raises `ModuleNotFoundError` in production. |
| **A2** | **God module.** `src/app.py` (816 lines) holds 8 unrelated jobs: notify, crawl, summary, progress, announcements, sync-channels, Notion, GCal and dedup. | `src/app.py:51-816` | Every change risks unrelated jobs, and the file is hard to test. |
| **A3** | **God query module.** `src/db_queries.py` (483 lines) holds the SQL for all 7 tables. | `src/db_queries.py` | It merges often and has no ownership per table. |
| **A4** | **Mixed responsibilities in `moodle_parser.py`.** It combines network I/O (`fetch_and_parse_events` downloads the ICS) with pure domain logic (`slugify_channel_name`, `get_current_semester`, `extract_display_name`). | `src/moodle_parser.py` | Pure helpers can't be imported anywhere without dragging in I/O. This is the root cause of A1. |
| **A5** | **Duplicated channel-resolution logic.** Both places do "slugify → fall back to old name → resolve the `kì N` category → create the channel". | `src/app.py:151-180` and `src/announcement_tracker.py:245-270` | The two copies can drift, causing duplicate channels or the wrong category. |
| **A6** | **Duplicated manual-deadline creation.** Normalising, parsing the date, `get_or_create_course` and `insert_deadline_manual` are repeated in 3 places. | `api/index.py:149-190`, `src/interactions.py:91+`, `src/external_api.py:30+` | Validation rules (length limits, sanitisation) differ per entry point. |
| **A7** | **Dead or duplicate entry points.** `api/interactions.py` and `api/add_deadline.py` repeat routes that `api/index.py` already handles. | `api/*.py` | It's unclear which handler Vercel actually runs, because the filesystem match beats the rewrite. |
| **A8** | **`src` used as a package name.** The import path `src.x` is meaningless and only works because of `sys.path` hacks. | 9 `sys.path.insert` calls across `api/`, `scripts/` and `tests/` | The code is fragile to the working directory and can't be installed or type-checked cleanly. |
| **A9** | **Import-time side effects.** `config.py` calls `logging.basicConfig` on import. `interactions.py` reads `DISCORD_PUBLIC_KEY` at import, and `api/index.py` reads `DATABASE_URL` at import. | `src/config.py:5`, `src/interactions.py:23`, `api/index.py:39` | Tests must set env vars before importing, and moving files can silently change import order. |
| **A10** | **Test folder pollution.** `test_firewall.py` calls `input()`. `test_bot.py` and `test_moodle.py` need live tokens. `test_extract{,2,3}.py` are scratch scripts with copied code. | `tests/` | `python -m pytest tests` hangs or errors, so the real tests can't run in CI. |
| **A11** | **Root clutter.** It has `test_out*.txt`, 4 planning docs at the root (`CAU_TRUC_DU_AN.md` duplicates `docs/cau-truc-du-an.md`), a folder name with a space (`UI 13TPro/`), and the legacy `data/state.json` (replaced by the DB). | repo root | Onboarding noise and broken shell paths. |
| **A12** | **Dependency drift.** `pyproject.toml` lists 3 dependencies, while `requirements.txt` lists 6. `pytest` isn't declared anywhere. | `pyproject.toml`, `requirements.txt` | Environments differ between Vercel, Actions and Termux. |
| **A13** | **Migration gap.** The numbering skips `003`. | `migrations/` | It's unclear whether a migration was lost. |
| **A14 (frontend)** | `App.tsx` (426 lines) owns all data fetching and state. There are 28 `../../` relative imports and no path alias. | `frontend/src/App.tsx`, `tsconfig.json` | Minor. The frontend is already feature-based. |

### 1.2 Current dependency graph (simplified)

```text
main.py ──► app.py ──► announcement_tracker ──► db_queries, discord_api, moodle_api, moodle_parser
                  ├──► moodle_deadline_crawler ──► db_queries, moodle_api, moodle_parser
                  ├──► event_tracker ──► db_queries, discord_api
                  ├──► notion_sync, google_calendar_sync
                  └──► config, database, utils, discord_api, moodle_parser, moodle_api

api/index.py ──► config, database, db_queries, utils, interactions, external_api, moodle_parser(!)
db_queries ──► database, utils (lazy import inside a function)
```

**Circular-dependency risk:** there are no cycles today, because everything fans out from `app.py`. The risk appears **during** migration. If you extract `services/channel_resolver.py` and it imports from `jobs/`, or a repository imports a service, you create a cycle. Section 3.3 sets a strict import direction to prevent this.

### 1.3 Migration hot spots (things that break when paths change)

| Hot spot | Why it matters |
|---|---|
| **`python main.py --<mode>` CLI contract** | It is called by `.github/workflows/notify.yml`, `daily_summary.yml`, `scripts/setup_termux.sh:75-76`, the 10 Termux widget scripts **already installed on the phone** (`~/.shortcuts/tasks/*`) and `TERMUX_WORKSTATION.md`. **`main.py` must stay at the root with identical flags.** |
| **`api/index.py` path** | Vercel only deploys Python functions from `/api`. `vercel.json` rewrites `/api/(.*)` to `/api/index.py`. The Discord Interactions endpoint URL points to `/api/interactions`. |
| **`.vercelignore`** | It lists individual source files. Every move invalidates it silently. |
| **`sys.path.insert` hacks** | There are 9 call sites. They break if a file moves to a different depth (for example `scripts/debug/x.py`). |
| **Test patch targets** | Any `mock.patch("src.discord_api.X")` stops working once code imports from the new location. Even with shims, patching the shim doesn't affect the real module. |
| **Private-name imports** | `tests/test_add_deadline_review.py` imports `_public` and `_handle_add_deadline`. `from x import *` shims **don't re-export `_names`**. |
| **Doc links** | `README.md`, `CAU_TRUC_DU_AN.md`, `docs/context-pack/*` and `TERMUX_WORKSTATION.md` all reference `src/...` paths. |
| **Frontend** | `vite.config.ts` and `tsconfig.json` must agree on any `@/` alias. `vercel.json` hard-codes `frontend/` and `frontend/dist`. |

---

## 2. Proposed Target Structure

### 2.1 Directory tree

```text
.
├── main.py                          # STABLE CLI shim: `from course_bot.cli import main; main()`
├── api/
│   └── index.py                     # Vercel entry ONLY: `from course_bot.web.router import handler`
│
├── course_bot/                      # The Python package (replaces `src/`)
│   ├── __init__.py
│   ├── cli.py                       # argparse; maps --summary/--progress/... → jobs.*
│   │
│   ├── core/                        # Leaf layer: no imports from anywhere else in course_bot
│   │   ├── config.py                # load_env(), constants (DISCORD_API_BASE); NO logging side effect
│   │   ├── logging_setup.py         # configure_logging(), called explicitly by cli.py / web/router.py
│   │   └── time_utils.py            # LOCAL_TZ, ensure_tz, parse_due_time   (← src/utils.py)
│   │
│   ├── domain/                      # Pure logic: no I/O, no DB, no HTTP. Safe for Vercel.
│   │   ├── course_naming.py         # extract_subject, extract_display_name, slugify_channel_name
│   │   ├── semester.py              # get_current_semester, parse_moodle_semester_code, extract_semester_index
│   │   ├── reminders.py             # decide NEW / 3_DAYS / 1_DAY from (deadline row, now)
│   │   └── messages.py              # Discord message templates (deadline, summary, progress bar)
│   │
│   ├── db/
│   │   ├── connection.py            # get_db, execute, fetch_one, fetch_all   (← src/database.py)
│   │   └── repositories/            # SQL only, one file per aggregate   (← split src/db_queries.py)
│   │       ├── courses.py
│   │       ├── deadlines.py
│   │       ├── moodle_content.py    # course_modules + forum_discussions + announcements
│   │       ├── notifications.py
│   │       └── error_logs.py
│   │
│   ├── integrations/                # Thin API clients: HTTP in → dicts out. No DB, no business rules.
│   │   ├── discord/
│   │   │   ├── rest.py              # channels, messages, reactions, scheduled events (← src/discord_api.py)
│   │   │   └── signature.py         # verify_signature (Ed25519), used by web/
│   │   ├── moodle/
│   │   │   ├── webservice.py        # ← src/moodle_api.py
│   │   │   └── ics_feed.py          # fetch_and_parse_events (← I/O half of src/moodle_parser.py)
│   │   ├── notion/client.py         # ← src/notion_sync.py
│   │   └── google_calendar/client.py# ← src/google_calendar_sync.py
│   │
│   ├── services/                    # Reusable use-cases shared by ≥2 entry points
│   │   ├── manual_deadlines.py      # add_manual_deadline(), toggle_completed()  (fixes A6)
│   │   ├── channel_resolver.py      # resolve_course_channel()                   (fixes A5)
│   │   └── external_sync.py         # push a deadline to Notion + GCal, swallowing errors
│   │
│   ├── jobs/                        # Runtime A: cron/CLI only. NEVER imported by web/.
│   │   ├── notify.py                # ← run_main_bot
│   │   ├── crawl_deadlines.py       # ← src/moodle_deadline_crawler.py + crawl_deadlines_standalone
│   │   ├── announcements.py         # ← src/announcement_tracker.py + check_announcements
│   │   ├── completions.py           # ← src/event_tracker.py (✅ reactions)
│   │   ├── reports.py               # ← send_daily_summary, send_progress_report
│   │   ├── sync_channels.py
│   │   ├── sync_external.py         # ← sync_notion, sync_google_calendar
│   │   └── dedup.py                 # ← run_deduplicate_messages
│   │
│   └── web/                         # Runtime B: Vercel HTTP. May import core/domain/db/services/integrations.discord.signature
│       ├── router.py                # BaseHTTPRequestHandler + route table (← body of api/index.py)
│       ├── http_utils.py            # _send_json, CORS, json_serializer, read_body
│       └── routes/
│           ├── dashboard.py         # /courses /deadlines /deadlines/toggle /stats /announcements
│           ├── discord_interactions.py  # /interactions (← src/interactions.py)
│           └── external.py          # /add_deadline with X-API-Key (← src/external_api.py)
│
├── migrations/                      # Unchanged names; add a note about the 003 gap in NOTES.md
├── scripts/
│   ├── ops/                         # One-off admin actions against production
│   │   ├── register_commands.py
│   │   ├── rename_all_channels.py
│   │   ├── set_category.py
│   │   ├── clean_bot_messages.py
│   │   └── discord_auto_channel.py
│   ├── dev/
│   │   ├── run_server.py            # local API + built frontend on :8000
│   │   ├── dump_moodle_data.py
│   │   ├── check_url.py
│   │   └── notion_helper.py
│   ├── debug/                       # Interactive / live-token scripts (← misplaced tests)
│   │   ├── live_bot_check.py        # ← tests/test_bot.py
│   │   ├── live_moodle_check.py     # ← tests/test_moodle.py
│   │   └── moodle_firewall_check.py # ← tests/test_firewall.py
│   └── termux/
│       └── setup_termux.sh
│
├── tests/
│   ├── conftest.py                  # shared fixtures, fake env vars, fake DB connection
│   ├── unit/                        # no network, no DB
│   │   ├── domain/test_semester.py          # ← test_semester_calculation.py
│   │   ├── domain/test_course_naming.py     # ← merge test_extract*.py (assertions only)
│   │   ├── services/test_manual_deadlines.py# ← test_add_deadline_review.py
│   │   ├── jobs/test_dedup.py               # ← test_deduplication.py
│   │   └── integrations/test_google_calendar.py
│   └── integration/                 # needs a real/disposable Postgres (opt-in: `-m integration`)
│       └── test_module_timezone.py
│
├── frontend/                        # Path unchanged (vercel.json depends on it)
│   └── src/
│       ├── app/                     # App.tsx, main.tsx, layout/ (Header, Sidebar, BottomNav)
│       ├── features/                # unchanged: announcements, courses, dashboard, deadlines, settings
│       │   └── deadlines/useDeadlines.ts   # NEW: data hooks pulled out of App.tsx
│       ├── shared/
│       │   ├── ui/                  # ← components/ui (Badge, Button, Modal, ...)
│       │   ├── api/client.ts
│       │   ├── types/index.ts
│       │   └── utils/dateUtils.ts
│       └── index.css
│
├── docs/
│   ├── architecture/                # cau-truc-du-an.md (merged with root CAU_TRUC_DU_AN.md), technical-specification.md, refactoring-blueprint.md
│   ├── guides/                      # termux-workstation.md, google-calendar-integration.md, notion-todo-list-integration.md
│   ├── planning/                    # roadmap.md, ke-hoach-may-tram.md, lo-trinh-*.md, yeu-cau-du-an.md
│   ├── design/
│   │   ├── figma-design-specification.md
│   │   └── mobile-13t-pro/          # ← "UI 13TPro/" (no spaces)
│   └── context-pack/
│
├── data/                            # runtime-only, gitignored (calendar.ics); delete legacy state.json
├── .github/workflows/               # notify.yml, daily_summary.yml (+ optional ci.yml running pytest)
├── README.md
├── pyproject.toml                   # single source of deps + [tool.pytest.ini_options]
├── requirements.txt                 # generated from / kept identical to pyproject deps (Vercel + Actions read it)
├── vercel.json
└── .vercelignore                    # directory-based: course_bot/jobs/, integrations/notion/, ...
```

### 2.2 Folder responsibilities and placement rules

| Folder | Responsibility | A file goes here if… | It must NOT… |
|---|---|---|---|
| `core/` | Configuration, time and logging | It is needed by almost everything and has no domain meaning. | Import any other `course_bot` module. |
| `domain/` | Pure business rules (naming, semesters, reminder windows, message text) | It is a function of its inputs only, and tests need no mocks. | Do I/O, import `requests` or `psycopg2`, or read env vars. |
| `db/repositories/` | SQL for one table or aggregate | It contains a SQL string. | Call Discord or Moodle, or contain decision logic beyond the query. |
| `integrations/<vendor>/` | Talking to one external API | It builds a request for, or parses a response from, a third party. | Touch the DB or make business decisions (for example "should we remind?"). |
| `services/` | Use-cases reused by ≥2 entry points | Two or more `jobs/` or `web/` modules need the same orchestration. | Import from `jobs/` or `web/`. |
| `jobs/` | One file per CLI mode (cron runtime) | It is triggered by `main.py --<flag>`. | Be imported by `web/` (this is enforced by `.vercelignore`). |
| `web/` | HTTP routing and handlers (Vercel runtime) | It parses an HTTP request or builds a response. | Import `jobs/`, `integrations/notion` or `integrations/google_calendar`. |
| `scripts/` | Human-run tools; never imported by the package | A person runs it by hand. | Be imported by `course_bot` or collected by pytest. |
| `tests/unit` | Fast, hermetic tests | It runs with no network or DB. | Call `input()` or need real tokens. |

### 2.3 Fixes that the structure provides

- **A1:** `web/routes/dashboard.py` imports `domain.semester`, which is pure and inside the bundle. `.vercelignore` then excludes whole directories, not single files.
- **A2 and A3:** `app.py` becomes 8 files under `jobs/`, and `db_queries.py` becomes 5 repositories.
- **A5 and A6:** the duplicated logic moves into `services/channel_resolver.py` and `services/manual_deadlines.py`.
- **A7:** `api/` keeps a single file.
- **A10:** interactive scripts move to `scripts/debug/`.

---

## 3. Classification Rules and Naming Conventions

### 3.1 Shared or local? (decision procedure)

Ask these questions in order and stop at the first "yes":

1. **Does it read env vars, configure logging, or handle time zones generically?** Put it in `core/`.
2. **Is it a pure function about courses, deadlines or semesters (no I/O)?** Put it in `domain/`.
3. **Does it contain SQL?** Put it in `db/repositories/<table>.py`.
4. **Does it only wrap one vendor's HTTP API?** Put it in `integrations/<vendor>/`.
5. **Is it orchestration used by ≥2 entry points (jobs or web routes)?** Put it in `services/`.
6. **Otherwise, it is local.** Keep it as a private `_helper` inside the single `jobs/<x>.py` or `web/routes/<x>.py` that uses it.

**Promotion rule:** start local. When a second caller appears, promote the code to `services/` (or `domain/` if it's pure) **in the same PR**. Never copy and paste it.

**Demotion rule:** if a `services/` module has had only one caller for a full semester, inline it back.

**Frontend equivalent:** code used by one feature stays in `features/<name>/`. Code used by ≥2 features moves to `shared/`. Features never import from each other. Shared code they need goes through `shared/`.

### 3.2 Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Python package or folder | `snake_case`, singular for layers | `course_bot/`, `integrations/google_calendar/` |
| Python module | `snake_case`, a noun for what it holds | `channel_resolver.py`, `time_utils.py` |
| Job module | Named after the CLI flag, with `-` replaced by `_` | `--sync-channels` → `jobs/sync_channels.py` |
| Job entry function | `run(...)` in every job module | `jobs.reports.run_summary()`, `jobs.notify.run()` |
| Repository functions | `get_*`, `list_*`, `insert_*`, `update_*`, `upsert_*`, `mark_*` | `deadlines.list_pending_manual()` |
| Private helpers | Leading `_`, never imported across modules | `_build_event_url` |
| Tests | `tests/unit/<layer>/test_<module>.py` mirrors the source path | `tests/unit/domain/test_semester.py` |
| Scripts | `snake_case.py` describing the action | `register_commands.py` |
| Migrations | `NNN_snake_case.sql`, never renumber existing files | `006_add_reminder_offsets.sql` |
| Docs | `kebab-case.md`, ASCII only, no spaces (Vietnamese content is fine) | `termux-workstation.md` |
| React component file | `PascalCase.tsx`, one component per file | `DeadlineItemCard.tsx` |
| React hook | `useCamelCase.ts` | `useDeadlines.ts` |
| TS util or module | `camelCase.ts` | `dateUtils.ts`, `client.ts` |
| TS feature folder | `kebab-case` (lowercase) | `features/deadlines/` |
| Identifiers | English in code. Vietnamese is allowed in user-facing strings, comments and API JSON keys that already exist (`mon`, `ten`, `han_chot`). | — |

### 3.3 Import direction (enforced)

```text
  cli.py / main.py          web/router.py (api/index.py)
         │                          │
       jobs/                   web/routes/
         └──────────┬───────────────┘
                 services/
           ┌────────┴─────────┐
   db/repositories      integrations/
           └────────┬─────────┘
                 domain/            (pure: no I/O)
                    │
                  core/
```

- **Amended 2026-10-15 (Phase 4):** `domain/` sits *below* `db/` and `integrations/`, not beside them. `integrations/moodle/ics_feed.py` needs `domain.course_naming.extract_subject`, and `domain/` is pure, so this direction can't create an import cycle. `domain/` must never import `db/`, `integrations/`, `services/`, `jobs/` or `web/`.
- **Temporary exception 2026-10-15 (Phase 6):** `jobs/notify.py` imports `jobs.completions.check_completions`, `jobs.crawl_deadlines.crawl_moodle_deadlines` and `jobs.announcements.check_moodle_updates`, and `jobs/reports.py` imports `check_completions`. These are direct `jobs/` → `jobs/` imports. Phase 8 moves those three functions into `services/` and removes the exception.
- Arrows point downward only. A module may import from any layer **below** it, never from a layer beside or above it. The exceptions are `jobs/` ↔ `jobs/` and `routes/` ↔ `routes/`, which are allowed only through `services/`.
- Optional enforcement: add [`import-linter`](https://pypi.org/project/import-linter/) with a `layers` contract to `pyproject.toml` and run it in CI.

---

## 4. Execution Roadmap and Checklist

### 4.1 Guiding principles

- **One phase = one PR (or commit).** Each phase must leave `main` deployable.
- **Move first, refactor second.** Use `git mv` plus import rewrites in one commit (pure moves keep `git log --follow` working). Behaviour changes, like deduplicating A5 and A6, come in a **separate** commit.
- **Use a staging environment for smoke tests.** Running `python main.py` sends real `@everyone` messages, so set up a test Discord server and a Supabase branch database, and put their values in `.env.staging`.

### 4.2 Phases

| Phase | Steps | Verification gate |
|---|---|---|
| **0. Baseline** | 1. Create branch `refactor/structure`. 2. Write `tests/test_imports_smoke.py` that imports every module plus `api.index`. 3. Record the current `pytest tests/<real unit tests>` results. 4. Fix **A1** now with a one-line hotfix: remove `src/moodle_parser.py` from `.vercelignore`. It's a production bug and shouldn't wait for the refactor. | All existing unit tests are green, and `GET /api/stats` works on a Vercel preview. |
| **1. Tooling and config** | 1. Add `[tool.pytest.ini_options] pythonpath = ["."]`, `testpaths = ["tests"]` and `markers = ["integration"]` to `pyproject.toml`. 2. Sync the `pyproject.toml` dependencies with `requirements.txt` and add the `dev` extra `pytest`. 3. Add `tests/conftest.py` with fake env vars. 4. Frontend: add `"baseUrl": "."` and `"paths": {"@/*": ["src/*"]}` to `tsconfig.json`, plus `resolve.alias` in `vite.config.ts`. | `pytest` runs without any `sys.path.insert` in tests, and `npm run build` passes. |
| **2. Non-code hygiene** | 1. Delete `test_out*.txt` and `data/state.json` (after confirming no code reads it: `grep -rn state.json`). 2. `git mv` the docs into `docs/{architecture,guides,planning,design}` and merge the two `cau-truc-du-an` files. 3. `git mv "UI 13TPro" docs/design/mobile-13t-pro`. 4. Move `test_bot.py`, `test_moodle.py` and `test_firewall.py` to `scripts/debug/`, delete the scratch `test_extract*.py` (keep their assertions for Phase 4), and group `scripts/` into `ops/`, `dev/`, `debug/` and `termux/`. 5. Fix every doc link. | `pytest` collects no interactive files, and a link checker (or `grep -rn "](.*\.md)"`) finds no dead links. |
| **3. Create the package and the leaf layer** | 1. `git mv src course_bot`. 2. Rewrite imports with `from src.` → `from course_bot.` (one sed pass across `course_bot/`, `api/`, `scripts/`, `tests/` and `main.py`). 3. Split `core/`: `config.py`, `time_utils.py` (from `utils.py`), `logging_setup.py`, and remove the import-time `basicConfig`. 4. Move `database.py` to `db/connection.py`. | `grep -rn "from src\." .` returns 0, the smoke test passes, and `python main.py --bogus` prints usage. |
| **4. Domain and integrations** | 1. Split `moodle_parser.py` into `domain/course_naming.py`, `domain/semester.py` and `integrations/moodle/ics_feed.py`. 2. `git mv` `moodle_api` → `integrations/moodle/webservice.py`, `discord_api` → `integrations/discord/rest.py` (with `verify_signature` moved to `signature.py`), and the Notion and GCal files into their folders. 3. Move the tests to `tests/unit/...` and **update every `mock.patch` target string in the same commit**. | Unit tests are green, and `grep -rn "patch(\"src\." tests` returns 0. |
| **5. Repositories** | Split `db_queries.py` into `db/repositories/*.py` by table. Update callers. Keep the function names unchanged in this phase. | Unit tests and the smoke test pass. Run `python main.py --crawl-deadlines` against **staging**. |
| **6. Jobs and CLI** | 1. Split `app.py` into `jobs/*.py`. 2. Move `moodle_deadline_crawler`, `announcement_tracker` and `event_tracker` into `jobs/`. 3. Add `cli.py` with argparse that accepts **exactly** the current flags (`--summary`, `--progress`, `--announcements`, `--sync-channels`, `--sync-notion`, `--sync-gcal`/`--sync-google-calendar`, `--crawl-deadlines`, `--dedup [--channel] [--limit] [--dry-run]`). 4. Reduce `main.py` to a 2-line shim. | Run each `main.py` mode against staging, and run `workflow_dispatch` for each mode on GitHub Actions with the staging secrets. |
| **7. Web layer** | 1. Move the body of `api/index.py` into `web/router.py` and `web/routes/*`, and reduce `api/index.py` to a 1-line re-export. 2. Move `interactions.py` and `external_api.py` into `web/routes/`. 3. Delete `api/interactions.py` and `api/add_deadline.py`. 4. Rewrite `.vercelignore` as directories (`main.py`, `course_bot/cli.py`, `course_bot/jobs/`, `course_bot/integrations/notion/`, `course_bot/integrations/google_calendar/`, `scripts/`, `tests/`, `docs/`, `migrations/`). | On the Vercel preview: `GET /api/health` and `/api/stats`, `POST /api/deadlines`, a Discord PING to `/api/interactions` (the portal's "Save" re-verifies it), `/deadline` and `/add_deadline` in the test server, and `POST /api/add_deadline` with an API key. |
| **8. Behavioural dedup** | 1. Extract `services/channel_resolver.py` (A5) and `services/manual_deadlines.py` (A6), and use them from all callers. 2. Extract `domain/reminders.py` and `domain/messages.py` from `jobs/notify.py`, and add unit tests for them. | New unit tests cover the reminder windows and the sanitisation rules. Staging gets no duplicate channels across 2 consecutive `--sync-channels` runs. |
| **9. Frontend** | 1. `git mv components/ui shared/ui`, then move `api/`, `types/` and `utils/` under `shared/`, and `components/layout` to `app/layout`. 2. Replace `../../` with `@/`. 3. Pull the fetching logic out of `App.tsx` into `features/*/use*.ts` hooks. | `npm run build` passes, `grep -rn "\.\./\.\./" frontend/src` returns 0, and a manual click-through works on a phone-width viewport. |
| **10. Rollout** | 1. Merge to `main`. 2. On the phone: `git pull`, rerun `bash scripts/termux/setup_termux.sh`, then test 2 widgets. 3. Watch the next 2 scheduled `Notification Bot` runs and the 06:55 `Daily Summary`. 4. Update `README.md` and the `docs/context-pack/*` trees. | No errors in the Actions logs, the Termux log is clean, and no duplicate Discord messages appear. |

**Rollback:** each phase is a single revertible commit. Because `main.py` and `api/index.py` keep their paths and flags, reverting never requires changing GitHub secrets, Vercel settings, the Discord portal or the phone.

### 4.3 Configuration audit checklist

Tick each item after the final phase:

- [ ] **`main.py`**: still at the root, and the flags and exit codes are unchanged.
- [ ] **`api/index.py`**: it is the only file in `api/` and exports `handler`.
- [ ] **`vercel.json`**: the rewrites still target `/api/index.py`, and `buildCommand`/`outputDirectory` still use `frontend/`.
- [ ] **`.vercelignore`**: directory-based, and it does **not** exclude anything that `web/` imports. Verify with a preview deploy hitting every route.
- [ ] **`pyproject.toml`**: dependencies match `requirements.txt`. It has the pytest config (`pythonpath`, `testpaths`, `markers`) and the optional `import-linter` contract. `[tool.vercel] entrypoint` still matches `api.index:handler`.
- [ ] **`requirements.txt`**: identical runtime dependencies (Vercel and Actions install from it).
- [ ] **`.github/workflows/notify.yml` and `daily_summary.yml`**: the commands are unchanged (`python main.py ...`). Optionally add `ci.yml` running `pytest -m "not integration"` and `npm run build` on pull requests.
- [ ] **`.gitignore`**: the `!data/*.json` exception is still needed (remove it if `state.json` is deleted). `service_account*.json` and `.env` are still ignored.
- [ ] **`scripts/termux/setup_termux.sh`**: its self-reference (`scripts/setup_termux.sh`, currently line 126) is updated, and the generated widget scripts still call `main.py`.
- [ ] **`docs/guides/termux-workstation.md`**: the paths and commands are updated.
- [ ] **`scripts/ops/register_commands.py`**: it still loads env through `course_bot.core.config`.
- [ ] **All `scripts/**`**: no `sys.path.insert` remains. Run them as `python -m scripts.ops.x`, or keep a single bootstrap helper.
- [ ] **`tests/`**: `grep -rn "sys.path\|from src\.\|patch(\"src\." tests` returns 0.
- [ ] **`frontend/tsconfig.json` and `frontend/vite.config.ts`**: the `@/*` alias is defined in **both**.
- [ ] **`README.md`**: the directory table, the test command and the script paths are updated.
- [ ] **`docs/context-pack/*` and `docs/architecture/cau-truc-du-an.md`**: the trees are regenerated.
- [ ] **`migrations/NOTES.md`**: it documents the missing `003`.
- [ ] **External systems (no change expected; confirm only)**: the Discord Interactions Endpoint URL, the Vercel environment variables, the GitHub Actions secrets and the Termux `.env`.

### 4.4 Final verification commands

```bash
grep -rn "from src\.\|import src\b" --include=*.py .        # expect 0
grep -rn "sys.path.insert" --include=*.py .                 # expect 0 (or only one bootstrap)
python -m pytest -m "not integration"                       # green, and no stdin prompts
python main.py --bogus                                      # prints usage
python -c "import api.index"                                # web bundle imports cleanly
cd frontend && npm run build                                # passes
grep -rn "\.\./\.\./" frontend/src                          # expect 0
```

---

## 5. Phase 4 Carry-over

### 5.1 `extract_display_name` samples (from the deleted `tests/test_extract*.py`)

The Phase 2 cleanup deleted the scratch scripts `tests/test_extract{,2,3}.py`. Their inputs are kept here so Phase 4 can turn them into `tests/unit/domain/test_course_naming.py`. The **Current output** column was recorded on 2026-10-15 by running the real `src.moodle_parser.extract_display_name`. The **Expected** column is the scratch scripts' goal, taken from `test_out3.txt` for the experimental `smart_extract_display_name`.

| Input | Current output | Expected | Status |
|---|---|---|---|
| `CQ2526HK2_CSC10014_CQ2024/2 - Nhập Môn Trí Tuệ Nhân Tạo` | `'Nhập Môn Trí Tuệ Nhân Tạo'` | `'Nhập Môn Trí Tuệ Nhân Tạo'` | ✅ |
| `Tư duy tính toán - CQ2024/2` | `'Tư duy tính toán'` | `'Tư duy tính toán'` | ✅ |
| `Cơ sở dữ liệu - CSC10006` | `'CSC10006'` | `'Cơ sở dữ liệu'` | ⚠️ Probable bug |
| `CSC10014` | `'CSC10014'` | `None` (scratch) | Needs a decision: callers may rely on the code being returned |
| `CSC10006_CQ2024/2` | `'CSC10006_CQ2024/2'` | — (not in scratch lists) | Needs a decision |
| `[CQ2024/2] Mạng Máy Tính` | `'[CQ2024/2] Mạng Máy Tính'` | `'Mạng Máy Tính'` | ⚠️ Probable bug |
| `CSC13102 - Hệ điều hành (TH)` | `'Hệ điều hành (TH)'` | `'Hệ điều hành'` | ⚠️ Probable bug |

**Phase 4 rule:** first add the tests as **characterization tests** that pin the *current output*, so moving the function doesn't change behaviour. Fix the ⚠️ rows later, in a separate behaviour-change commit, and update those tests in that commit.

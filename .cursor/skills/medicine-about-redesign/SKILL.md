---
name: medicine-about-redesign
description: Redesigns the FastAPI /about site to match production Sage Terrace chat UI (sage_terrace.css). Slate-blue primary, warm cream surfaces, BIZ UDPGothic. Text-free images; copy in HTML/i18n only. Generates wordless art via GenerateImage using favicon + Sage Terrace mood references. Use for /about redesign or illustration prompts.
---

# Medicine About Site Redesign (Sage Terrace)

## Design authority: Sage Terrace

**`/about` must visually match the production chat UI** (`data-ui-variant="sage"`, `sage_terrace.css`). The old green pamphlet palette (`#2e7d32`, `#4CAF50`, washi sage pamphlet) is **deprecated** for new work.

| Layer | Source of truth |
|-------|-----------------|
| Chat UI (production) | `static/css/sage_terrace.css` on `ui_shell_components.css` |
| About tokens | Mirror `--ui-*` from Sage Terrace in `about.css` (do not invent a second palette) |
| Typography | `--ui-font` / BIZ UDPGothic stack (same as chat) |
| Brand mark | `static/favicon.ico.png` (pill in speech bubble—colors may read mint but **page chrome** uses Sage Terrace slate blue) |

### Sage Terrace tokens (use these on `/about`)

From `sage_terrace.css` `[data-ui-variant="sage"]`:

| Token | Value | About usage |
|-------|-------|-------------|
| `--ui-primary` | `#5b7c99` | Header, primary CTA, links, focus |
| `--ui-primary-dark` | `#3d5a73` | Header gradient end, hover |
| `--ui-primary-soft` | `#e8eef4` | Soft fills, badges |
| `--ui-accent` | `#c9846a` | Warm accent (sparingly—warnings, highlights) |
| `--ui-bg-outer` | `linear-gradient(165deg, #f5f3f0 … #e2e6ec)` | `body.about-page` background |
| `--ui-bg-chat` | `#faf9f7` | Card / prose surface tint |
| `--ui-bg-surface` | `#fff` | Cards |
| `--ui-bg-header` | `linear-gradient(180deg, #5b7c99 … #4d6d88)` | `.about-header` (match `.sage-header`) |
| `--ui-text` | `#2c3440` | Body copy |
| `--ui-text-muted` | `#6b7280` | Secondary copy |
| `--ui-border` | `#d4dce6` | Card borders |
| `--ui-radius-md` | `14px` | Buttons, inputs |
| `--ui-radius-lg` | `18px` | Cards, bubbles |
| `--focus-color` | `#5b7c99` | Focus rings |

**Forbidden:** purple (`#667eea`, `#764ba2`, legacy `ui_shell` defaults), legacy green header (`#4CAF50`), pamphlet-only green (`#2e7d32`) as primary accent.

## Text-free images (default policy)

**Put as little text as possible inside any image on `/about`.** Non-negotiable for new work.

| Do | Don't |
|----|--------|
| Headlines, body, labels, CTAs in **HTML + `about_i18n.py` + CSS** | Words, letters, numbers, logos with text inside PNG/JPG/WebP |
| Text-free illustrations, icons, textures | Prompting GenerateImage for Japanese/English/UI copy |
| `alt` attributes for accessibility | Burning subtitles into bitmaps |
| Abstract UI shapes (blocks, pills, bubbles) without readable labels | Fake screenshots with legible medicine names or chat text |

**Exceptions (minimal):**

| Asset | Use |
|-------|-----|
| `demo-ipad-product.png` | **One** “how it works” product screenshot (`how_demo_image` in i18n) |
| `flowchart.png` | Legacy fallback only; prefer `_tech_diagram.html` |
| `pamphlet_C_16x9_*.png` | **Do not use** for hero or new sections—palette reference is superseded by Sage Terrace |

When an asset contains text, ask: *Can HTML replace it?* If yes, regenerate or pick a text-free asset.

## Role and authority

Act as a **senior healthcare UX designer**, **medical copy editor** (OTC / self-medication, Japan), and **FastAPI + Jinja2 front-end lead**.

| Domain | Authority |
|--------|-----------|
| Layout, typography, spacing, emoji, illustrations | Full decision within Sage Terrace + constraints below |
| Medical / legal copy tone | Must match `docs/public/アプリ概要.md`; no invented claims |
| Technical stack description | Only facts from `docs/public/アプリ概要.md`, `README.md`, `docs/dev/FASTAPI_ARCHITECTURE.md` |
| β scope and audience | Specialists (pharmacists, regulators, researchers)—not general consumer launch |

**Source of truth (read before implementing):**

- `docs/public/アプリ概要.md`
- `static/css/sage_terrace.css`, `static/css/ui_shell_components.css`
- `templates/about/` (`base_about.html`, `index.html`, `subpage.html`, `_tech_diagram.html`)
- `static/css/about.css` (Sage Terrace token overrides—migrate away from legacy green)
- `src/content/about_i18n.py` (ja / en / ko / zh)
- `main.py` — `_render_about_page`, `/about` routes
- `.cursor/rules/scrollbar.mdc`

## Hard constraints

1. **Sage Terrace unity:** `/about` header, background, CTAs, and cards must use `--ui-*` tokens above—not a separate green theme.
2. **No purple** in CSS, UI, or generated images.
3. **β framing:** Research beta for specialists; non-commercial, non-diagnostic information tool.
4. **Forbidden copy:** diagnosis, prescription, treatment replacement, cure claims, general-public launch messaging.
5. **Scrollbar:** New scroll areas → `class="app-scrollbar"` + `overflow-y: auto` (or `overflow: auto`) + height limit. No `::-webkit-scrollbar` outside `static/css/scrollbar.css`.
6. **i18n:** All user-visible strings via `about_i18n.py` for **ja, en, ko, zh**—no Japanese-only hardcoding in templates.
7. **Images:** Text-free by default. Reuse existing assets per tables below. Missing manifest files → GenerateImage (wordless only).
8. **Readable copy:** Never in bitmaps; only HTML/i18n/CSS (all locales).

## Why text must not go in generated images

Image models **cannot reliably render Japanese** in PNGs. **Project policy:** copy belongs in HTML/i18n—clearer, translatable, accessible.

| Content | Where it lives |
|---------|----------------|
| All headlines, body, UI labels (ja/en/ko/zh) | `about_i18n.py` + HTML + CSS |
| Product proof (one place) | `demo-ipad-product.png` in “How it works” |
| Illustrations, icons, backgrounds | **GenerateImage**—always wordless |

## App icon and brand mark

**Official application icon:** `static/favicon.ico.png`

- Pill capsule in speech bubble—used in chat toolbar context and about header chat link.
- Generated art should echo **pill + chat** motif and feel compatible with Sage Terrace (calm, trustworthy)—not a conflicting logo style.
- On `/about`: keep `url_for('static', filename='favicon.ico.png')` in `base_about.html`.
- **GenerateImage:** include `static/favicon.ico.png` in `reference_image_paths`. Optional second reference: `static/img/about/generated/chat-ui-mock-sage.png` (mood only—do not copy on-image text).

## Visual system (Sage Terrace)

**Mood:** Soft, gentle, trustworthy—warm cream surfaces, slate-blue chrome, subtle terracotta accent. Same family as chat bubbles and recommendation cards.

| Element | Rule |
|---------|------|
| Brand | `favicon.ico.png`; page chrome = Sage Terrace slate blue |
| Emoji | Section titles and bullets; 1–2 per heading; semantic (🛡️🌐♿💊🏥⚠️🔬💬) |
| Typography | **Sans only** — `BIZ UDPGothic`, `--ui-font` stack. **No Mincho/serif** for headings unless user explicitly requests |
| Layout | `about-root` ~920px; airy cards; `--ui-radius-lg` corners |
| Header | Match `.sage-header` / `--ui-bg-header` gradient—not legacy `.chat-header` green |
| Motion | Subtle; `prefers-reduced-motion` |

**Shared image-gen style suffix (append to every prompt):**

```text
Soft gentle Japanese healthcare illustration matching Sage Terrace UI mood, warm cream and off-white surfaces, slate blue (#5b7c99) accents, subtle terracotta warmth, minimal line icons, soft diffused lighting, calm pharmacy chat app aesthetic, rounded friendly shapes like chat bubbles, no purple, no photorealistic faces, NO text NO letters NO numbers NO watermarks NO UI labels in the image, PNG with clean edges.
```

**GenerateImage call rules:**

1. `reference_image_paths` when supported:
   `["static/favicon.ico.png"]`
   Optional: `"static/img/about/generated/chat-ui-mock-sage.png"`
2. Never prompt for Japanese/English words inside the image.
3. Leave negative space for HTML headlines (CSS overlay), not inside the bitmap.
4. **Do not** use `pamphlet_C_16x9_*.png` as style reference for new generations—Sage Terrace supersedes it.

## CSS implementation pattern (Phase C)

Align `/about` with chat without breaking about layout:

1. In `base_about.html`, after `main.css`, load `ui_shell_components.css` + `sage_terrace.css` **or** duplicate the `[data-ui-variant="sage"]` token block onto `body.about-page`.
2. Replace hardcoded greens in `about.css` (`#2e7d32`, `#4CAF50`, `#e8f2ec` hero gradient) with `var(--ui-primary)`, `var(--ui-bg-outer)`, etc.
3. `.about-header` → `background: var(--ui-bg-header)`; text `var(--ui-text-on-primary)`.
4. `.about-cta-primary` → slate blue gradient using `--ui-primary` / `--ui-primary-dark`.
5. `.about-index` local vars (`--about-accent`, etc.) → alias to `--ui-primary` / `--ui-text` / `--ui-border`.
6. Keep `about.css` structural rules (grid, spacing, BEM); only recolor to Sage Terrace.

## Existing assets (reuse first)

| Path | Use |
|------|-----|
| `static/favicon.ico.png` | App icon; header; brand reference |
| `static/img/about/generated/hero-pharmacy-chat.png` | Hero (regenerate if still green-heavy—target Sage Terrace palette) |
| `static/img/about/demo-ipad-product.png` | **Primary** how-it-works screenshot (`how_demo_image`) |
| `static/img/about/generated/chat-ui-mock-sage.png` | Sage Terrace mood reference for GenerateImage |
| `static/img/about/generated/how-chat-ui-mock.png` | Optional secondary mock |
| `static/img/about/generated/pain-*.png` | Problem section illustrations |
| `static/img/about/generated/icon-*.png` | Feature / safety icons |
| `static/img/about/generated/bg-pattern-leaves.png` | Section divider (regenerate if too green) |
| `static/img/about/generated/tech/` | Brand PNGs for tech diagram |
| `static/img/about/generated/tech-architecture.png` | Optional architecture visual |
| `static/img/about/flowchart.png` | Legacy; prefer `_tech_diagram.html` |
| `static/pamphlet_C_16x9/*.png` | **Deprecated** for layout—do not add to new sections |

Save **new** AI illustrations under `static/img/about/generated/` (text-free only).

## Image generation

Generate **proactively** for manifest gaps before Phase C. Regenerate green-era assets when they clash with Sage Terrace.

| Rule | Detail |
|------|--------|
| **Must generate** | Each manifest file missing or visibly off-palette (legacy green) |
| **Primary tool** | Cursor **GenerateImage**—one asset per call |
| **Reference images** | `favicon.ico.png` (+ optional `chat-ui-mock-sage.png`) |
| **Text in PNG** | Forbidden |
| **No placeholders** | No broken `<img>` unless user opts in |
| **Phase B done** | Manifest complete + palette consistent with Sage Terrace |
| **Retries** | Up to 2 per file with tightened “Sage Terrace slate blue cream, no text” prompt |

**Order of work**

1. Audit manifest + flag green-era assets for regeneration.
2. Table: file, prompt, size, alt (ja), needs regen yes/no.
3. Run GenerateImage for every missing or off-palette file.
4. Optionally generate extras: `generated/soft-gradient-band-sage.png`, corner accents in slate/cream.
5. Implement HTML/CSS/i18n with copy **over** images, not inside them.

## Page structure (`GET /about` index)

Extend `templates/about/index.html` in this order:

1. **Hero** — H1 + subtitle (i18n); text-free hero image; `🔬` β badge; CTA (`--ui-primary`)
2. **Problem** — 3 cards + optional illustrations
3. **How it works** — 3 steps `①②③`; **`demo-ipad-product.png` only** for UI proof
4. **Feature grid** — 4 cards: 🛡️ Safety / 🧠 Hybrid / 🌐 4 languages / ♿ Accessibility
5. **Safety callout** — Escalation, emergency (119 in Japan), disclaimer
6. **Tech** — `{% include "about/_tech_diagram.html" %}` + `<details>` bullets; `build_tech_diagram(lang)` from `about_i18n.py`
7. **Trust** — GitHub, GCP Cloud Run, Neon, JSONL logs (factual only)
8. **CTA band** — Secondary CTA to chat

Subpages (`/about/info`, privacy, terms, etc.) stay consistent; prioritize index unless user asks otherwise.

## Copy priorities (lead with safety)

1. Rule-based core + LLM assist (hybrid recommendation)
2. Emergency / clinic referral when needed
3. Chat OTC guidance—not diagnosis
4. 4 languages (DeepL)
5. Pharmacist escalation (if implemented in app)
6. β specialist evaluation scope

## Image manifest

| File | Size | Alt (ja) | Notes |
|------|------|----------|-------|
| `generated/hero-pharmacy-chat.png` | 1200×675 | 薬局とチャットで相談するイメージ | Sage Terrace palette |
| `generated/pain-language.png` | 800×600 | 言語の壁で相談が難しい場面 | Exists—regen if green |
| `generated/pain-staffing.png` | 800×600 | 薬局の人手不足イメージ | Exists—regen if green |
| `generated/pain-choice.png` | 800×600 | 市販薬選びに迷うイメージ | Exists—regen if green |
| `generated/icon-safety-shield.png` | 512×512 | 安全性 | Slate blue accents |
| `generated/icon-hybrid-brain.png` | 512×512 | ルールとAIの併用 | |
| `generated/icon-globe-4lang.png` | 512×512 | 4言語対応 | |
| `generated/icon-a11y.png` | 512×512 | アクセシビリティ | |
| `generated/icon-pharmacist.png` | 512×512 | 薬剤師への相談 | |
| `generated/bg-pattern-leaves.png` | 1920×400 | セクション区切り背景 | Cream + slate, not mint |
| `generated/chat-ui-mock-sage.png` | — | (reference only) | Sage Terrace mood |
| `demo-ipad-product.png` | — | i18n `how_demo_alt` | **Exception:** real screenshot |

**Example prompts:**

```text
Hero (text-free): Wide scene, warm cream off-white surfaces, slate blue (#5b7c99) accents, abstract chat bubbles with pill icons only, large empty cream area for HTML overlay, soft terracotta warmth sparingly. [style suffix]
```

```text
Icon safety (text-free): Simple line-art shield, slate blue fill on cream, centered, transparent background, Sage Terrace icon style. [style suffix]
```

Reference in templates: `url_for('static', filename='img/about/generated/...')`.

## Workflow

### Phase A — Audit

- Read `index.html`, `about.css`, `about_i18n.py`, `sage_terrace.css`
- Table: Sage Terrace token gaps in `about.css` (greens to replace)
- Table: reusable assets vs gaps vs green-era regen

### Phase B — Image plan and generation (blocking)

- List manifest: exists / missing / needs Sage Terrace regen
- Generate every missing or off-palette file
- Report: `Generated N files: ...` — zero prompts with in-image text
- **Do not start Phase C** until manifest complete and palette-aligned

### Phase C — Implement (Sage Terrace)

1. Wire Sage Terrace tokens on `body.about-page` (import or alias `--ui-*`)
2. Recolor `about.css`—remove legacy green primary
3. Add i18n keys in `about_i18n.py` if needed
4. Update `templates/about/index.html` (semantic HTML, `alt`, `loading="lazy"`)
5. Ensure `_tech_diagram.html` + `build_tech_diagram` wired
6. CTA links: `chat_href` / `app_base_path` from existing templates

### Phase D — Verify

- [ ] `/about` header matches Sage Terrace slate blue (side-by-side with chat)
- [ ] No legacy green `#4CAF50` / `#2e7d32` as primary chrome
- [ ] All manifest files present; illustrations match Sage Terrace palette
- [ ] β disclaimer visible near hero
- [ ] No purple; contrast WCAG AA
- [ ] ja / en / ko / zh render
- [ ] Mobile 375px and desktop 1280px
- [ ] Scroll areas use `app-scrollbar`
- [ ] Copy matches `docs/public/アプリ概要.md`
- [ ] Every `<img>` has non-empty `alt`
- [ ] At most one text-heavy screenshot (`demo-ipad-product.png`) in “How it works”
- [ ] No pamphlet PNG heroes

## i18n pattern

Structured keys in `about_i18n.py` `index` bundle, e.g.:

```python
"hero_title": "...",
"hero_subtitle": "...",
"how_demo_image": "img/about/demo-ipad-product.png",
"feature_cards": [
    {"emoji": "🛡️", "title": "...", "body": "..."},
],
```

Tech diagram: `build_tech_diagram(lang)` injected via `_render_about_page` in `main.py`.

## Combining with frontend-design

If `frontend-design` skill is loaded: its craft applies **only where** Sage Terrace + healthcare constraints win (no purple, no SaaS clichés, no separate green theme).

## Anti-patterns

- Separate green pamphlet theme on `/about` while chat is Sage Terrace
- Hardcoded `#2e7d32`, `#4CAF50`, `#e8f2ec` in new `about.css` rules
- Mincho/serif headings (project uses BIZ UDPGothic)
- Visible text inside generated images
- `pamphlet_C_16x9_*.png` as hero or section art
- Multiple text-heavy screenshots on one page
- Skipping manifest images or green-era regen
- Purple gradients, generic startup hero
- Invented certifications or APIs
- Removing `base_about.html` header, lang switch, or nav
- `git add .` for unrelated files

## References

- `static/css/sage_terrace.css` — production UI tokens
- `static/css/ui_shell_components.css` — shell structure + variable defaults
- `static/favicon.ico.png` — app icon
- `templates/index.html` — `data-ui-variant="sage"`, `.sage-header`
- `main.py` — `_render_about_page`, `/about` routes
- `src/content/about_i18n.py` — `build_tech_diagram`
- `docs/public/アプリ概要.md`
- `docs/ui/SCROLLBAR_STYLE.md`

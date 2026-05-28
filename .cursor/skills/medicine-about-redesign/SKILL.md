---
name: medicine-about-redesign
description: Redesigns the Flask /about site with soft sage pamphlet-style visuals aligned to static/favicon.ico.png (app icon). Text-free images; copy in HTML/i18n only. Generates wordless art via GenerateImage using favicon + pamphlet as style references. Use for /about redesign or illustration prompts.
---

# Medicine About Site Redesign

## Text-free images (default policy — user requirement)

**Put as little text as possible inside any image on `/about`.** This is non-negotiable for new work.

| Do | Don't |
|----|--------|
| Headlines, body, labels, CTAs in **HTML + `about_i18n.py` + CSS** | Words, letters, numbers, logos with text inside PNG/JPG/WebP |
| Text-free illustrations, icons, textures, patterns | Prompting GenerateImage for Japanese/English/UI copy |
| `alt` attributes for accessibility (not visible on-image text) | Burning subtitles or titles into bitmaps |
| Abstract UI shapes (blocks, pills, bubbles) without readable labels | Fake screenshots with legible medicine names or chat text |

**Exceptions (use only when necessary, prefer alternatives):**

- `Demo.png` — single “how it works” slot; prefer cropping or placing small; do not duplicate text-heavy screenshots elsewhere.
- `flowchart.png` — tech `<details>` only; no second diagram with labels if a simpler wordless icon set exists.
- Legacy pamphlets (`pamphlet_C_16x9_*.png`) — **style reference for GenerateImage only**; do **not** embed as large hero `<img>` unless the user explicitly requests that asset. Prefer `generated/hero-pharmacy-chat.png` + HTML title instead.

When an asset contains text, ask: *Can HTML replace it?* If yes, regenerate or pick a text-free asset.

## Role and authority

Act as a **senior healthcare UX designer**, **medical copy editor** (OTC / self-medication, Japan), and **Flask + Jinja2 front-end lead**.

| Domain | Authority |
|--------|-----------|
| Layout, typography, spacing, emoji, illustrations | Full decision within constraints below |
| Medical / legal copy tone | Must match `docs/アプリ概要.md`; no invented claims |
| Technical stack description | Only facts from `docs/アプリ概要.md`, `README.md`, `docs/FASTAPI_ARCHITECTURE.md` |
| β scope and audience | Specialists (pharmacists, regulators, researchers)—not general consumer launch |

**Source of truth (read before implementing):**

- `docs/アプリ概要.md`
- `templates/about/` (`base_about.html`, `index.html`, `subpage.html`)
- `static/css/about.css` (extends chat header; **no purple**)
- `src/content/about_i18n.py` (ja / en / ko / zh)
- `.cursor/rules/scrollbar.mdc`

## Hard constraints

1. **No purple** in CSS, UI, or generated images.
2. **Palette:** mint/sage green (`#e8f2ec`, `#2e7d32`, white cards)—extend `about.css`; do not break `base_about.html` header/nav contract.
3. **β framing:** Research beta for specialists; non-commercial, non-diagnostic information tool.
4. **Forbidden copy:** diagnosis, prescription, treatment replacement, cure claims, general-public launch messaging.
5. **Scrollbar:** New scroll areas → `class="app-scrollbar"` + `overflow-y: auto` (or `overflow: auto`) + height limit. No `::-webkit-scrollbar` outside `static/css/scrollbar.css`.
6. **i18n:** All user-visible strings via `about_i18n.py` for **ja, en, ko, zh**—no Japanese-only hardcoding in templates.
7. **Images:** **Text-free by default** (see Text-free images). Reuse existing assets only per Existing assets table. Every **Image manifest** file missing on disk **must** be created with generative AI—wordless only.
8. **Readable copy:** Never in bitmaps; only HTML/i18n/CSS (all locales).

## Why text must not go in generated images

Image models used by Cursor **GenerateImage** (and most diffusion models) **cannot reliably render Japanese text** in PNGs. Typical failures:

| Symptom | Cause |
|---------|--------|
| English only | Prompts are English-only; model defaults to Latin letters |
| Garbled / wrong kanji | Models lack glyph-level control for 日本語 |
| Blurry fake UI text | “Screenshot with Japanese labels” in prompt → illegible blobs |
| No text at all | Correct for generated art; copy belongs in HTML |

Image models cannot render Japanese reliably. **Project policy:** do not put text in images at all—not only because the model fails, but because HTML/i18n is clearer, translatable, and accessible.

**Required split:**

| Content | Where it lives |
|---------|----------------|
| All headlines, body, UI labels (ja/en/ko/zh) | `about_i18n.py` + HTML + CSS |
| Product proof (optional, one place) | `Demo.png` in “How it works” only |
| Pamphlet PNGs with embedded Japanese | **Style reference for GenerateImage only**—not default hero |
| Illustrations, icons, backgrounds | **GenerateImage**—always wordless |

## App icon and brand mark

**Official application icon:** `static/favicon.ico.png`

- Mint-green speech bubble with a **pill capsule** (line icon)—used in chat header, about header, and favicon.
- Treat this as the **canonical brand mark**: generated icons and illustrations should echo the same motif (pill + chat/communication) and mint/sage greens—**not** a different logo style.
- On `/about`: reuse via existing templates (`url_for('static', filename='favicon.ico.png')` in `base_about.html`)—do not replace with a new mark unless the user asks.
- **GenerateImage:** include `static/favicon.ico.png` in `reference_image_paths` together with the pamphlet (wordless output only; do not redraw readable text from the pamphlet).

## Visual system (pamphlet-aligned)

**Style references (mood/colors/motif—not for copying on-image text):**

1. `static/favicon.ico.png` — brand icon (pill in speech bubble, mint green)
2. `static/pamphlet_C_16x9/pamphlet_C_16x9_v01_sage_mic.png` — layout mood, sage/cream

**Text-free background pattern:** `static/pamphlet_gentle/pamphlet_gentle_pattern_A_cream_mint.png` (no words; safe to use as CSS background).

| Element | Rule |
|---------|------|
| Brand | Pill-in-bubble icon consistent with `favicon.ico.png` |
| Emoji | Section titles and bullets; 1–2 per heading; semantic (🛡️🌐♿💊🏥⚠️🔬💬) |
| Mood | **Soft, gentle, trustworthy**—sage green + cream washi paper, botanical accents |
| Palette | Mint/sage from favicon + pamphlet: ~`#8fa89a`, cream `#f5f0e6`, accent `#2e7d32`, dark navy only as small contrast if needed—**no purple** |
| Typography (web) | Elegant Japanese **Mincho/serif** for headings in CSS to echo pamphlet; sans for body |
| Layout | `about-root` ~920px; airy cards; optional leaf/pattern dividers from generated assets |
| Motion | Subtle; `prefers-reduced-motion` |

**Shared image-gen style suffix (append to every prompt):**

```text
Soft gentle Japanese healthcare pamphlet illustration, match sage-green and cream washi paper aesthetic, subtle botanical leaf accents, minimal line icons, soft diffused lighting, calm pharmacy mood, rounded friendly shapes, no purple, no photorealistic faces, NO text NO letters NO numbers NO watermarks NO UI labels in the image, PNG with clean edges.
```

**GenerateImage call rules:**

1. Pass `reference_image_paths` on every generation when supported:
   `["static/favicon.ico.png", "static/pamphlet_C_16x9/pamphlet_C_16x9_v01_sage_mic.png"]`
2. Never prompt for Japanese/English words inside the image.
3. Leave negative space for HTML headlines beside or over the image (CSS), not inside the bitmap.

## Existing assets (reuse first)

| Path | Use |
|------|-----|
| `static/favicon.ico.png` | **Official app icon**; header/favicon; brand reference for generated art |
| `static/pamphlet_C_16x9/pamphlet_C_16x9_v01_sage_mic.png` | **GenerateImage style reference only**—do not use as default hero (contains text) |
| `static/pamphlet_gentle/pamphlet_gentle_pattern_A_cream_mint.png` | Soft **text-free** background texture (OK) |
| `static/img/about/Demo.png` | **One** “how it works” exception; minimize size/crops elsewhere |
| `static/img/about/medicine_recommended.png` | Chat UI fallback |
| `static/img/about/flowchart.png` | Architecture (tech section) |
| `static/img/about/language.png` | Multilingual feature |
| `static/img/about/recommend.png` | Recommendation flow |
| `docs/未踏/docs/image/` | Trust / demo references if appropriate |

Save **new** AI illustrations under `static/img/about/generated/` (text-free only).

## Image generation (mandatory and aggressive)

Generate **proactively and in volume**—do not wait for the user to ask per file. Before **Phase C**, complete all manifest items plus any extra soft illustrations that improve the page (section backgrounds, small botanical corners).

| Rule | Detail |
|------|--------|
| **Must generate** | Each manifest file missing under `static/img/about/generated/` |
| **Primary tool** | Cursor **GenerateImage**—**one asset per tool call**; copy output into `static/img/about/generated/<filename>` |
| **Reference images** | Always attach `static/favicon.ico.png` + pamphlet v01 sage via `reference_image_paths` when supported |
| **Text in PNG** | **Forbidden** for all new/generated assets and new layout choices |
| **Pamphlet PNGs** | Mood reference only; hero = text-free `generated/hero-pharmacy-chat.png` + HTML title |
| **Fallback** | External gen only if GenerateImage fails—same path, same no-text rule |
| **No placeholders** | No broken `<img>` unless user opts in |
| **Phase B done** | All manifest files on disk + pamphlet assets wired in templates |
| **Retries** | Up to 2 retries per file with tightened “no text, sage cream pamphlet style” prompt |

**Order of work**

1. Audit manifest + pamphlet reuse (hero may be pamphlet, not generated).
2. Table: file, prompt, size, alt (ja), reference image yes/no.
3. **Run GenerateImage for every missing manifest file**—report count (e.g. 8/8).
4. Optionally generate extras: `generated/leaf-corner-left.png`, `generated/leaf-corner-right.png`, `generated/soft-gradient-band.png`.
5. Implement HTML/CSS/i18n with Japanese text **over** images, not inside them.

If generation fails after retry, stop and report which file failed—do not silently skip the section.

## Page structure (`GET /about` index)

Extend `templates/about/index.html` in this order:

1. **Hero** — HTML: H1 + subtitle (i18n); image: text-free `generated/hero-pharmacy-chat.png` (or pattern background only); **no** text-heavy pamphlet as hero; `🔬` β badge; CTA
2. **Problem** — 3 cards with generated text-free illustrations + Japanese titles in HTML
3. **How it works** — 3 steps `①②③`; **`Demo.png` only** for UI (no generated UI mock with text)
4. **Feature grid** — 4 cards: 🛡️ Safety / 🧠 Hybrid / 🌐 4 languages / ♿ Accessibility
5. **Safety callout** — Escalation, emergency (119 in Japan), disclaimer—visible, not alarmist
6. **Tech** — `<details>` collapsible; simplified stack from アプリ概要; `flowchart.png`
7. **Trust** — GitHub, GCP Cloud Run, Neon, JSONL logs (factual only)
8. **Subpages** — Existing nav links + secondary CTA

Subpages (`/about/info`, privacy, terms) stay consistent; prioritize index unless user asks otherwise.

## Copy priorities (lead with safety)

1. Rule-based core + LLM assist (hybrid recommendation)
2. Emergency / clinic referral when needed
3. Chat OTC guidance—not diagnosis
4. 4 languages (DeepL)
5. Pharmacist escalation (if implemented in app)
6. β specialist evaluation scope

## Image manifest (create prompts if missing)

| File | Size | Alt (ja) |
|------|------|----------|
| `generated/hero-pharmacy-chat.png` | 1200×675 | 薬局とチャットで相談するイメージ |
| `generated/pain-language.png` | 800×600 | 言語の壁で相談が難しい場面 |
| `generated/pain-staffing.png` | 800×600 | 薬局の人手不足イメージ |
| `generated/pain-choice.png` | 800×600 | 市販薬選びに迷うイメージ |
| `generated/icon-safety-shield.png` | 512×512 | 安全性 |
| `generated/icon-hybrid-brain.png` | 512×512 | ルールとAIの併用 |
| `generated/icon-globe-4lang.png` | 512×512 | 4言語対応 |
| `generated/icon-a11y.png` | 512×512 | アクセシビリティ |
| `generated/icon-pharmacist.png` | 512×512 | 薬剤師への相談 |
| `generated/bg-pattern-leaves.png` | 1920×400 | セクション区切り背景 |

**Example prompts (no text in image):**

```text
Hero (text-free): Wide scene, sage green and cream washi mood, soft pharmacy interior silhouette, abstract chat bubbles with pill icons only (no words), large empty cream area on the right for HTML overlay, botanical leaf corner accents. [style suffix]
```

```text
Icon safety (text-free): Simple line-art shield with soft green fill, pamphlet icon style, centered, transparent background. [style suffix]
```

**Bad prompt (causes “no Japanese” complaints):**

```text
❌ Poster with title チャット型医薬品相談ツール and Japanese medicine names in the screenshot
```

Reference saved files via `url_for('static', filename='img/about/generated/...')` in templates or `about_i18n` image keys.

## Workflow

### Phase A — Audit

- Read current `index.html`, `about.css`, `about_i18n.py` index bundle
- Table: reusable assets vs gaps

### Phase B — Image plan and generation (blocking)

- List manifest files: exists / missing; note pamphlet reuse for hero
- For each **missing** file: prompt (style suffix + **no text**), size, alt (ja), reference pamphlet yes
- **Generate every missing file** with GenerateImage—execute all calls in this phase without asking per image
- Report: `Generated N files: ...` and confirm **zero** prompts requested Japanese inside PNG
- en/ko/zh strings only in `about_i18n.py` (Phase C)
- **Do not start Phase C** until manifest complete

### Phase C — Implement

1. Add i18n keys in `about_i18n.py` (`index` page: `hero_*`, `features`, `safety`, `tech`, etc.)
2. Update `templates/about/index.html` (semantic HTML, `alt`, `loading="lazy"`)
3. Add CSS in `about.css` (BEM-like: `about-hero`, `about-feature-grid`, …)
4. Wire images; ensure CTA links use `chat_href` / `app_base_path` patterns from existing templates

### Phase D — Verify

- [ ] All Image manifest files present under `static/img/about/generated/`
- [ ] β disclaimer visible near hero
- [ ] No purple; contrast WCAG AA
- [ ] ja / en / ko / zh render
- [ ] Mobile 375px and desktop 1280px
- [ ] Scroll areas use `app-scrollbar`
- [ ] Copy matches `docs/アプリ概要.md` (no invented stack)
- [ ] Every `<img>` has non-empty `alt` (localized via i18n where applicable)
- [ ] No new images contain visible text; at most one `Demo.png` in “How it works”
- [ ] Hero does not use pamphlet PNG with embedded Japanese (unless user explicitly requested)

## i18n pattern

Add structured keys to `index` bundle in `about_i18n.py`, e.g.:

```python
"hero_title": "...",
"hero_subtitle": "...",
"feature_cards": [
    {"emoji": "🛡️", "title": "...", "body": "...", "image": "img/about/generated/icon-safety-shield.png"},
],
```

Pass lists/dicts through `_render_about_page` context unchanged; keep templates logic minimal.

## Combining with frontend-design

If `frontend-design` skill is loaded: use its typography and layout craft **only where** this skill's healthcare constraints win (no purple, no SaaS clichés, images required).

## Anti-patterns

- Any visible text inside generated or newly placed images (including English logos)
- Using `pamphlet_C_16x9_*.png` as full-width hero when HTML + text-free art suffices
- Prompting for Japanese, kanji, hiragana, or UI labels inside PNGs
- Multiple text-heavy screenshots (`Demo`, `medicine_recommended`, pamphlet) on one page
- Skipping manifest images or waiting for user permission on each file
- Proceeding to Phase C with missing `generated/*.png` files
- Purple gradients, generic startup hero, syringe close-ups
- Text walls without images
- Emoji-only sections (💊💊💊🔥)
- Invented certifications or APIs
- Removing `base_about.html` header, lang switch, or nav
- `git add .` for unrelated files

## References

- `static/favicon.ico.png` — official app icon (pill in speech bubble)
- `static/pamphlet_C_16x9/pamphlet_C_16x9_v01_sage_mic.png` — pamphlet mood (wordless gen targets this palette)
- `static/pamphlet_gentle/pamphlet_gentle_pattern_A_cream_mint.png` — background pattern
- `docs/アプリ概要.md`
- `docs/プライバシーポリシー.md`, `docs/免責事項・利用規約.md`
- `docs/SCROLLBAR_STYLE.md`
- `main.py` — `_render_about_page`, `/about` routes

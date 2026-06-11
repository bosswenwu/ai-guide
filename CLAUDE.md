# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a VuePress 1.x static documentation site — **鱼皮 AI 知识库** — a Chinese-language AI knowledge base and tutorial platform hosted at https://ai.codefather.cn. Content is primarily Markdown files organized into topical directories.

## Common Commands

```bash
# Development server (hot-reload)
npm run docs:dev

# Production build (outputs to .vuepress/dist/)
npm run docs:build

# Regenerate sidebar config from directory structure (run before build when content changes)
npm run generate:sidebar

# Regenerate README.md from directory content
npm run generate:readme

# Full pre-build pipeline (sidebar + README)
npm run pre-docs:build

# Serve built output locally
npm run serve

# Count total Markdown files
npm run getMdNumber
```

There are no tests in this repository.

## Architecture

### Content → Sidebar Pipeline

The sidebar is **not hand-authored** — it is generated automatically from the filesystem:

1. `.vuepress/scripts/generateSidebar.js` walks content directories recursively, sorts files by creation time (newest first), and writes output to `.vuepress/sidebars/ai.ts`.
2. `.vuepress/config.ts` imports `sidebars/ai.ts` and assigns routes `/AI/` and `/Vibe Coding 零基础教程/` to auto-generated sidebars.
3. **Run `npm run generate:sidebar` after adding, removing, or renaming content files** so the sidebar reflects the change.

The script has special-case logic to pin the "🔥DeepSeek 小白快速上手指南" item to the top.

### Content Structure

- `/AI/` — Main knowledge base (DeepSeek guides, tool comparisons, industry news, application scenarios)
- `/Vibe Coding 零基础教程/` — Flagship tutorial series covering tools, projects, advanced techniques, and monetization
- `/OpenClaw 保姆级教程/` — OpenClaw integration guide
- `/translations/` — English and Traditional Chinese versions of selected content
- `/产品服务/` — Product/service directory

All content files are Markdown. The default sort order in generated sidebars is **newest file first** (by `birthtime`).

### VuePress Config Files (`.vuepress/`)

| File | Purpose |
|---|---|
| `config.ts` | Main VuePress config — title, domain, plugins, sidebar routing |
| `navbar.ts` | Top navigation bar items and links |
| `sidebar.ts` | Sidebar route assignments (imports generated sidebars) |
| `footer.ts` | Footer links and ICP copyright |
| `theme/` | Custom VuePress theme (Vue components, layouts, styles) |
| `scripts/` | Build automation scripts (sidebar gen, README gen, email notify) |
| `sidebars/` | **Auto-generated** — do not edit by hand |

### CI/CD

Two GitHub Actions workflows in `.github/workflows/`:

- **`deploy.yml`** — Triggered on push to `main`. Runs `npm run docs:build`, then uploads `.vuepress/dist/` to Tencent Cloud COS via `coscmd`. Sends an email notification on completion. Requires secrets: `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`, `COS_BUCKET`, `COS_REGION`, `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_TO`.
- **`sync-vibe-coding-course.yml`** — Triggered on push to `main`. Diffs changed files and POSTs a JSON payload to a backend endpoint to notify it of content additions/modifications/deletions. Requires secrets: `SYNC_AI_GUIDE_URL`, `SYNC_AI_COURSE_TOKEN`.

Both workflows use Node.js 16. The sync workflow disables git path escaping (`core.quotepath=false`) to handle Chinese filenames correctly.

## Key Conventions

- **Chinese-first content**: all documentation and filenames use Simplified Chinese. File/directory names with spaces are URL-encoded in auto-generated links.
- **Do not manually edit `.vuepress/sidebars/ai.ts`** — it is overwritten by `generate:sidebar`.
- **Do not manually edit `README.md`** — it is overwritten by `generate:readme`.
- The `formatMdContent.js` script can normalize Markdown formatting and inject missing top-level headings; run it on new content directories if needed.
- VuePress plugins configured: back-to-top, Google Analytics, medium-zoom (image zoom), Baidu autopush, feed, SEO, sitemap, tags, code-copy, img-lazy.

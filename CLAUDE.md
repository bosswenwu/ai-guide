# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is **鱼皮 AI 知识库** — a VuePress v1 static documentation site serving as an open-source AI knowledge base. Content is primarily in Chinese and covers AI tools (DeepSeek, GPT, etc.), Vibe Coding tutorials, application scenarios, and industry news. The live site is deployed to Tencent Cloud COS at https://ai.codefather.cn.

## Commands

```bash
# Install dependencies (Node 16 required)
npm install

# Start local dev server with hot reload
npm run docs:dev

# Regenerate sidebar config for the /AI/ section from filesystem
npm run generate:sidebar ./AI

# Regenerate README.md index files for the /AI/ section
npm run generate:readme ./AI

# Pre-build step: regenerates both sidebar and READMEs for /AI/
npm run pre-docs:build

# Build static site to .vuepress/dist/
npm run docs:build

# Serve the built dist locally
npm run serve

# Count total markdown files
npm run getMdNumber
```

There is no test framework — this is a documentation-only project. The build step (`docs:build`) acts as the validation gate.

## Architecture

### Configuration layer (`/.vuepress/`)

All VuePress configuration lives here:

- **`config.ts`** — main site config (title, plugins, theme options). Plugins include SEO, sitemap, Google Analytics, Baidu autopush, code-copy, image lazy-load, and RSS feed.
- **`navbar.ts`** — top navigation bar links.
- **`sidebar.ts`** — sidebar routing. The `/AI/` and `/AI项目教程/` routes use the auto-generated `sidebars/ai.ts`; all other routes fall back to `"auto"` (VuePress derives sidebar from page headings).
- **`sidebars/ai.ts`** — **auto-generated file**, do not edit manually. Regenerate with `npm run generate:sidebar ./AI`.
- **`footer.ts`** — footer friend links.
- **`extraSideBar.ts`** — right sidebar with social QR codes and resource download links.
- **`theme/`** — custom Vue 2 theme components and Stylus styles.
- **`scripts/`** — Node.js utility scripts (see below).

### Sidebar generation (`/.vuepress/scripts/generateSidebar.js`)

This is the key automation script. It recursively walks a target directory, collects `.md` files (excluding `README.md`), and **sorts entries by filesystem `birthtime` descending** (newest first). The one hardcoded exception is that any file whose path includes `"🔥DeepSeek 小白快速上手指南"` is always prepended to the top. Output is written to `.vuepress/sidebars/ai.ts` as an ES module export. Run this whenever you add, remove, or rename files/directories under `/AI/`.

### Content sections

- **`/AI/`** — main AI knowledge base. Sidebar is auto-generated. Adding new content here requires re-running `generate:sidebar` and `generate:readme`.
- **`/Vibe Coding 零基础教程/`** — large tutorial series with numbered files (00, 01, 10, 20 … prefix determines display order). Sidebar falls back to `"auto"` mode.
- **`/translations/`** — English (`en/`) and Traditional Chinese (`zh-TW/`) translations.

### Deployment (CI/CD)

Two GitHub Actions workflows trigger on push to `main`:

1. **`deploy.yml`** — installs deps → builds site → uploads `.vuepress/dist/` to Tencent COS via `coscmd` → sends email notification. Requires repository secrets: `TENCENT_SECRET_ID`, `TENCENT_SECRET_KEY`, `COS_BUCKET`, `COS_REGION`, `EMAIL_USER`, `EMAIL_PASS`, `EMAIL_TO`.
2. **`sync-vibe-coding-course.yml`** — diffs the push and POSTs added/modified/deleted file lists to a backend service. Requires secrets: `SYNC_AI_GUIDE_URL`, `SYNC_AI_COURSE_TOKEN`.

## Content Conventions

- **File naming:** Numeric prefixes control display order within `"auto"` sidebar sections (e.g., `00 intro.md`, `01 quickstart.md`, `10 tools/`). The `generateSidebar.js` script ignores these prefixes and sorts by `birthtime` instead, so for `/AI/` content, creation time on the server determines order — not filename prefixes.
- **Directories vs flat files:** `/AI/` uses deeply nested subdirectories; each directory gets a collapsible group in the sidebar. `/Vibe Coding/` mixes top-level files with numbered subdirectories.
- **`README.md` in content dirs:** These are auto-generated index pages for `/AI/` subdirectories via `genReadme.js`. Do not manually edit them in the `/AI/` tree.
- **Markdown frontmatter:** Frontmatter fields `description`, `tags`, `date`, and `image` are consumed by the SEO plugin. `tags` falls back to the global tag list in `config.ts` if unset.
- **Permalinks:** `config.ts` sets `permalink: "/:slug"` — VuePress derives URL slugs from filenames. Chinese filenames produce percent-encoded URLs.

# 🤖 CHAT HAY: AI CODING GUIDELINES & PROJECT RULES

This document contains critical rules and architectural guidelines. **Any AI assistant modifying this codebase MUST read and strictly follow these rules.**

## 1. 🏗️ Tech Stack & Environment
- **Core:** React 18, TypeScript, Vite.
- **UI Framework:** Zalo Mini App UI (zmp-ui), custom SCSS.
- **Routing:** React Router v6 (via `ZMPRouter` and `AnimationRoutes`).
- **Environment:** Runs within a Zalo Mini App Wrapper (port 3000 proxies port 2999).

## 2. 🚨 CRITICAL FIXES (DO NOT OVERWRITE)
These specific implementations exist to fix fatal Zalo wrapper bugs. **NEVER modify or remove them:**
1. **SPA Fallback Plugin:** In `vite.config.mts`, the `spaFallback()` plugin MUST remain as the first plugin. It fixes the `404 Not Found` black screen issue by rewriting `/` to `/src/index.html`.
2. **Index Path:** In `src/index.html`, the script src MUST be `<script type="module" src="/src/app.tsx"></script>`. Do not change to relative `./app.tsx`.
3. **Catch-All Route:** In `src/components/layout.tsx`, `<Route path="*" element={<Navigate to="/" replace />} />` MUST remain at the bottom of `<AnimationRoutes>` to catch Vite rewrite artifacts.
4. **Bottom Navigation Fixed:** `<BottomNavigation fixed ...>` MUST have the `fixed` prop to prevent it from rendering at the top of the screen and breaking the layout.

## 3. 🗺️ Application Architecture
The app follows a strict **2-Tab Layout** structure. Do not invent new parent tabs unless explicitly requested.
- **Tab 1: Xử lý File (`/file-processing`)** - Handles document uploads, vault, and PDF processing.
- **Tab 2: AI Learning (`/ai-learning`)** - Handles flashcards, quizzes, and coin wallet.
- **Sub-pages:** Flashcards (`/flashcard`), Quiz (`/quiz`), Vault (`/vault`) are SUB-PAGES. They must include a "Back" button to return to their parent tab.

## 4. 🎨 UI & Styling Standards
- **No Tailwind CSS:** We use a custom, highly curated SCSS design system (`src/css/app.scss`). Do not inject Tailwind utility classes into JSX (e.g., avoid `className="flex mt-4 text-center"`).
- **Glassmorphism & Gradients:** Use predefined CSS variables from `:root` in `app.scss`.
- **Card Usage:** Always use `<Box className="ch-card">` or `<Box className="ch-card ch-card-interactive">` for UI components.

## 5. 💻 Coding Practices
- **Typescript:** Use strong typing. Avoid `any` where possible.
- **No Orphaned Imports:** Clean up unused imports after refactoring.
- **Atomic Commits:** When asked to create a feature, focus ONLY on the specific files required. Do not "clean up" or format unrelated files like `layout.tsx` or `vite.config.mts` unless instructed.

---
*By reading this, the AI confirms it understands the critical constraints of the Zalo Mini App environment and will preserve the stability of the project.*

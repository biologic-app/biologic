# Repository Guidelines

## Project Structure & Module Organization

This is a Vite + Vue 3 dashboard app using TypeScript, Nuxt UI, Pinia, Vue Router, and Tailwind CSS. Bootstrap code lives in `src/main.ts` and `src/app/`. Route-level pages are in `src/pages/`; feature areas are grouped under `src/modules/` such as `auth`, `customers`, `dashboard`, `inbox`, `settings`, and `user-types`. Shared reusable code belongs in `src/shared/`, split by purpose: `ui`, `composables`, `api`, `types`, `utils`, `i18n`, `tour`, `config`, and `constants`. Static assets are in `public/`.

## Build, Test, and Development Commands

Use Bun, as pinned by `packageManager` and `bun.lock`.

- `bun install`: install dependencies.
- `bun run dev`: start the Vite dev server on port `5177`.
- `bun run build`: create a production build.
- `bun run preview`: serve the production build locally.
- `bun run lint`: run ESLint against `src`.
- `bun run typecheck`: run `vue-tsc` with `tsconfig.app.json`.

## Coding Style & Naming Conventions

Follow `.editorconfig`: 2-space indentation, LF endings, UTF-8, final newline, and trimmed trailing whitespace except in Markdown. Use TypeScript with strict checks. Prefer the `@/` alias for imports from `src`, for example `@/shared/utils/format`.

Name Vue components in PascalCase (`UserMenu.vue`, `SettingsMembersList.vue`). Name composables with the `useX` pattern (`useAuth.ts`, `useLocale.ts`). Keep feature-specific code inside its module and move reusable UI, types, and utilities into `src/shared/`.

ESLint uses `typescript-eslint` recommended rules and `eslint-plugin-vue` flat recommended rules. Vue multi-word component names are allowed, and Vue templates should keep single-line attributes to no more than three per line.

## Testing Guidelines

No automated test framework or `test` script is currently configured. For now, validate changes with:

```bash
bun run lint
bun run typecheck
bun run build
```

When adding tests, place them near the code they cover or in a clearly named test directory, use `*.test.ts` or `*.spec.ts`, and add a `bun run test` script to `package.json`.

## Commit & Pull Request Guidelines

Recent history mostly uses Conventional Commit prefixes such as `feat:`, `fix:`, `refactor:`, and `chore:`. Keep commits focused and use an imperative summary, for example `fix: correct customer filter reset`.

Pull requests should include a concise description, linked issue or task when available, validation commands run, and screenshots or short recordings for UI changes. Note any configuration changes, new dependencies, or missing test coverage.

## Security & Configuration

Keep environment values out of git. Use `.env.example` as the template for required variables, including `VITE_API_BASE_URL`. Do not commit build output, secrets, or local editor files.

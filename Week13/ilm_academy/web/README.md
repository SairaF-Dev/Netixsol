# Ilm Academy web app

React + Vite + TypeScript. Student and teacher areas in one app; the server decides the role
(httpOnly session cookie from the FastAPI backend in `../ilm/api`).

```powershell
npm install
npm run dev      # http://localhost:5173, proxies /api to http://localhost:8010 (set ILM_API to change)
npm run build    # type-check + production build into dist/
```

- Design rules and screens: `../docs/design/ui_ux_plan.md`. Colours, type and spacing live
  only in `src/styles/tokens.css`.
- No UI kit: components are plain React + CSS using those tokens.
- The code editor (CodeMirror 6) is loaded only on the exercise page.
- Hidden tests never reach the browser: the API sends visible tests and a hidden-test count only.

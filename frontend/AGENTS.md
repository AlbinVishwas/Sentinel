# Frontend Developer Notes

This frontend uses **Next.js App Router** (not the Pages Router).

- All routes live under `src/app/`
- Server components are the default; mark client components with `"use client"`
- The API proxy route at `src/app/api/agent/stream/route.ts` forwards SSE to the FastAPI backend
- Styling uses CSS custom properties defined in `src/app/globals.css` (dark monochrome palette)

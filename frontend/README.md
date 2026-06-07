# Sentinel — Frontend

Next.js (App Router) chat interface for the Sentinel autonomous SRE agent.

## Stack

| Layer | Technology |
|-------|------------|
| Framework | Next.js 15 (App Router) |
| Language | TypeScript |
| Styling | Geist font + custom CSS variables (dark monochrome) |
| Deployment | Google Cloud Run (standalone output) |

## Local Development

```bash
# 1. Install dependencies
npm install

# 2. Set the backend URL (copy from backend/.env.example)
cp .env.local.example .env.local
# NEXT_PUBLIC_BACKEND_URL=http://localhost:8000

# 3. Start the dev server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The root path redirects to `/chat`.

The frontend proxies agent requests through the Next.js API route at
`/api/agent/stream` → `${BACKEND_URL}/agent/stream`, so the GitLab PAT
never reaches the browser.

## Key Files

| File | Purpose |
|------|---------|
| `src/components/chat.tsx` | Main chat UI — SSE streaming, message list, composer |
| `src/components/agency-log.tsx` | Collapsible real-time tool call timeline |
| `src/components/markdown.tsx` | GitHub-flavored Markdown renderer for agent replies |
| `src/app/api/agent/stream/route.ts` | Next.js proxy route → FastAPI SSE stream |
| `src/lib/types.ts` | Shared TypeScript event/message types |

## Production Build

```bash
npm run build   # outputs a standalone bundle (.next/standalone)
```

The [Dockerfile](Dockerfile) uses the standalone output for minimal image size.

# Sentinel

> **AI-Powered CI/CD Overwatch and Autonomous SRE for GitLab**

Sentinel is an autonomous AI agent that monitors GitLab repositories, triages
open issues, investigates broken CI/CD pipelines, and programmatically generates
secure, verified code patches via Merge Requests — keeping the human engineer
safely in the loop.

Built for the **GitLab Track** of the Google Cloud Rapid Agent Hackathon.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Orchestration | Google Cloud Vertex AI Agent Development Kit (ADK) |
| Core Model | Gemini 3.5 Flash |
| Backend | FastAPI (async Python) |
| Integration | GitLab Model Context Protocol (MCP) Server |
| Frontend | Next.js (App Router) + Tailwind CSS + TypeScript |
| Deployment | Google Cloud Run |
| Secrets | Google Cloud Secret Manager |

## Repository Layout

```
/backend    FastAPI service + ADK agent orchestration
/frontend   Next.js chat interface
```

## License

[MIT](LICENSE)

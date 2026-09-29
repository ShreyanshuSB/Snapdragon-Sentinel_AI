# SENTINEL Frontend

This is the presentation layer for **SENTINEL: Your private AI that sees, understands, and remembers**.

## Technology Stack
- **Framework**: Next.js 16.3 (App Router with Turbopack)
- **UI Library**: React 19
- **Type System**: TypeScript (strict mode)
- **Styling**: Tailwind CSS v4
- **Icons**: Lucide Icons (`lucide-react`)
- **API Client**: Centralized typed client in `lib/api.ts`

## Page Routes
- `/`: **Home** — System readiness indicators, multimodal pipeline overview, quick action shortcuts.
- `/vision`: **Vision (DESKAI)** — Physical camera WebRTC feed, frame capture, file upload, truthful analysis results.
- `/memory`: **Memory (MEMORA)** — Searchable SQLite knowledge store, category filtering, Add/Edit/View modals, purge confirmation.
- `/chat`: **Ask SENTINEL** — Multimodal reasoning console, conversation session drawer, visual snapshot and memory citation context.
- `/ai-lab`: **AI Lab** — Reviewer console detailing model registry, execution providers, host hardware detection, and live baseline benchmark testing.
- `/settings`: **Settings & Privacy** — Hardware ingestion permissions (camera/mic toggles), persistent memory lock, storage inspect/purge.

## Running Locally

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Run production build validation
npm run build
```
Frontend runs at `http://localhost:3000` and communicates with the FastAPI backend at `http://localhost:8000`.

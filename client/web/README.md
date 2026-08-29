# Watchtower Web UI

A clean, professional browser client for the watchtower motion recorder, built
with **Next.js** (App Router), **React 19**, and **Tailwind CSS 4**.

It talks to the backend **only over HTTP/JSON** through the FastAPI layer in
`src/watchtower/api.py` — so the UI is fully decoupled and can be swapped or
rebuilt without touching the recorder.

## Views

- **Timeline** (`/`) — grid of recorded clips with play, download, delete, and
  category filter.
- **Live** (`/live`) — watch cameras in real time (MJPEG stream, browser-playable).
- **Settings** (`/settings`) — motion sensitivity, detector + categories,
  pre/post-roll, retention, notifications, snapshot toggle.

## Responsive

The UI is fully responsive:

- **Desktop** — fixed sidebar with vertical navigation.
- **Mobile / tablet** — the sidebar collapses to a top bar with horizontal,
  scrollable navigation; grids and headers stack vertically.

## Run it

```bash
# 1. Start the backend (from the repo root)
python -m watchtower.api --config config.json

# 2. Start the frontend (from this folder)
npm install
npm run dev
```

Open http://localhost:3000. The frontend calls the API at
`http://localhost:8000` by default — override with `NEXT_PUBLIC_API_URL`.

## Build for production

```bash
npm run build
npm start
```

## Structure

```
src/
├── app/
│   ├── layout.tsx        # root layout (dark theme)
│   ├── page.tsx          # Timeline view
│   ├── live/page.tsx     # Live view (MJPEG)
│   └── settings/page.tsx # Settings view
├── components/
│   └── Shell.tsx         # responsive sidebar/top-bar navigation shell
└── lib/
    ├── api.ts            # API client (only place that talks to the backend)
    └── format.ts         # date/duration/motion helpers
```

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

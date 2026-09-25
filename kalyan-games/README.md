# Kalyan Games

Satta-Matka style gaming app — rebranded build matching the client's Figma design.

```
kalyan-games/
├── web/          Front-end prototype (single-file, Figma-matched UI)
│   └── index.html
└── server/       Backend API — Express + Prisma + PostgreSQL
    └── README.md  (setup + Railway deploy + API reference)
```

## What's here

- **web/index.html** — clickable mobile app prototype: login (no OTP), live
  markets, games grid with the real 3D icons, two-digit betting grid with live
  total, wallet, add-fund/withdraw, results. Runs standalone in any browser.
- **server/** — REST API for auth, wallet, markets, bids, results, and an admin
  API with **Google Authenticator (TOTP)** 2-step login. Deploys to Railway.

## Status

| Piece | State |
|---|---|
| Web app UI (user) | ✅ Prototype done, matched to Figma |
| Backend API | ✅ Scaffolded & deployable (mock wallet) |
| Web app ↔ API wiring | ⏳ To do (prototype still uses in-memory data) |
| Admin panel UI | ⏳ To do (API is ready) |
| Download site | ⏳ To do |
| Real payments | ⛔ Blocked — see server/README §Payments |

See `server/README.md` for how to run and deploy.

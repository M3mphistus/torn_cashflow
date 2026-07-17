# Render-Deployment — Torn Cashflow (React + FastAPI)

Anleitung für den Release von `main-v2` auf Render.com (Hobby-Account). Enthält keine Secrets —
die tatsächlichen Werte stehen in deiner lokalen, nicht committeten `GO_LIVE_CHECKLIST.md`.

Zwei Render-Services aus demselben Repo: ein **Web Service** (Backend) und eine **Static Site**
(Frontend). Beide zeigen auf denselben Branch (`main-v2`, oder erst nach weiterem Review `main`).

---

## 1. Backend — Web Service

1. Render Dashboard → **New → Web Service** → dieses GitHub-Repo verbinden.
2. Branch: `main-v2`.
3. **Root Directory**: `backend`
4. **Runtime**: Python 3
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
7. **Health Check Path**: `/health`
8. **Environment Variables** (Werte aus deiner `GO_LIVE_CHECKLIST.md`):
   - `DATABASE_URL`
   - `DEV_TORN_PLAYER_ID`
   - `XANAX_ITEM_ID`
   - `DEV_TORN_PLAYER_NAME`
   - `JWT_SECRET`
   - `API_KEY_ENCRYPTION_SECRET`
   - `FRONTEND_ORIGIN` — trag hier erstmal irgendeinen Platzhalter ein (z. B.
     `http://localhost:5173`), du korrigierst ihn in Schritt 3, sobald die Frontend-URL feststeht.
9. Deploy auslösen.
10. Nach erfolgreichem Deploy:
    - Backend-URL notieren (z. B. `https://torn-cashflow-backend.onrender.com`)
    - `https://<backend-url>/health` → sollte `ok` liefern
    - `https://<backend-url>/docs` → Swagger UI sollte alle Endpunkte zeigen

**Wichtig:** Der erste Start läuft automatisch `init_db()` — legt alle Tabellen in der
bestehenden Supabase-DB an, sofern sie nicht schon existieren (idempotent, verändert nichts an
vorhandenen Daten).

---

## 2. Frontend — Static Site

1. Render Dashboard → **New → Static Site** → dasselbe Repo verbinden.
2. Branch: derselbe wie beim Backend.
3. **Root Directory**: `frontend`
4. **Build Command**: `npm ci && npm run build`
5. **Publish Directory**: `dist`
6. **Environment Variable**:
   - `VITE_API_BASE_URL` = die Backend-URL aus Schritt 1 (ohne `/api` am Ende)
7. Deploy auslösen.
8. Frontend-URL notieren (z. B. `https://torn-cashflow.onrender.com`).

Kein Cold-Start bei Static Sites — nur das Backend schläft nach Inaktivität ein.

---

## 3. Backend und Frontend verdrahten

1. Zurück zum Backend-Service in Render → Environment → `FRONTEND_ORIGIN` auf die echte
   Frontend-URL aus Schritt 2 setzen (exakt, inkl. `https://`, ohne trailing Slash).
2. Backend neu deployen (Render macht das i.d.R. automatisch bei Env-Var-Änderungen, sonst
   manuell "Manual Deploy" anstoßen).
3. Frontend-URL im Browser öffnen, mit einem echten Torn-API-Key einloggen.
4. Seite neu laden → Login sollte erhalten bleiben (Cross-Site-Cookie funktioniert).

Falls der Login nach Reload verloren geht: meistens `FRONTEND_ORIGIN` falsch/veraltet, oder
Safari-spezifisches Cookie-Verhalten (siehe `frontend/README.md`, bekanntes Risiko, kein Bug).

---

## 4. Golden Path (auf der echten Live-URL testen, nicht lokal)

- [ ] Login mit echtem Torn-API-Key
- [ ] Reload → Session bleibt erhalten
- [ ] Dashboard: "Sync now" → Daten erscheinen
- [ ] Dashboard: Zeitraum-Filter (Today/Yesterday/Last 7/30/90/Custom/All time) durchklicken
- [ ] War Mode umschalten (Settings)
- [ ] Checklist: Task anlegen, abhaken, bearbeiten, löschen
- [ ] Settings: Premium-Status korrekt, Danger Zone sichtbar
- [ ] Falls Premium: "Get all Data" (Full History Sync) — Fortschritt pollt sichtbar
- [ ] Falls Premium: Categories — Kategorie anlegen, Einträge umsortieren, Sign-Korrektur testen
- [ ] Logout → wirklich ausgeloggt

## 5. Bekannte, akzeptierte Einschränkungen

- **Cold Start**: Backend schläft nach ~15 Min. Inaktivität ein, erster Request danach
  braucht 30-60s. Frontend zeigt dafür einen "waking up…"-Zustand statt hängenzubleiben.
- **Safari Cross-Site-Cookies**: siehe `frontend/README.md` — bekanntes Risiko, kein Fix geplant
  außer über eine eigene Domain (nicht Teil des Free-Tier-Setups).

## 6. Nach dem Go-Live

- Render-Logs (Backend) nach dem ersten echten Traffic kurz auf unerwartete 500er prüfen.
- Entscheiden: alte Streamlit-App (`torn-cashflow.streamlit.app`) als Fallback online lassen
  oder abschalten, und ob Nutzer über die neue URL informiert werden (siehe `forum_post.md`).

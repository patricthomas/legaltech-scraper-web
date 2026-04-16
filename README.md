# LegalTech News Scraper — Web Edition v3

Flask web app that scrapes 20+ legal tech sources, scores articles for NetDocuments relevance by market segment, and generates a ready-to-send `.eml` email draft — all from a browser. Deployable via Docker/Portainer.

---

## What's New in v3

### Segment-Based Scoring
Four segments with separate scoring modifiers and badge colours:

| Segment | Focus | Badge colour |
|---|---|---|
| **Strategic** | Enterprise DMS, workflow, AI adoption | Blue |
| **SML** | Small/mid-size firm practice management | Purple |
| **International** | Cross-border, GDPR, regional compliance | Sky |
| **Corporate** | In-house counsel, CLM, legal ops, GC | Teal |

### Corporate Segment — Dedicated Sources
When **Corporate** is selected, six additional sources appear in the News Sources grid (teal, pre-checked) and are scraped automatically:

- **Corporate Counsel** (Law.com)
- **ACC Docket**
- **CCBJ** (Corporate Counsel Business Journal)
- **Bloomberg Law — Legal Ops & Tech**
- **Bloomberg Law Pro — Technology**
- **CLOC**

These sources are hidden and unchecked for all other segments.

### Harvey & Legora Coverage
Both Harvey and Legora are first-tier signals (+18 pts) in every segment, with dedicated sales angles surfaced in the email blast.

### CSV Export
After any scraper run, a **Download All Articles (.csv)** button appears alongside the `.eml` button. The CSV includes every scraped article (not just the curated top-N) with columns: `source`, `title`, `url`, `desc`, `score`, `competitor`.

### Custom RSS Feeds
Add any RSS feed via the UI — persisted in `data/custom_sites.json` across restarts.

---

## Deploy with Docker / Portainer

### Portainer Stack (Git Repository)

1. In Portainer → **Stacks → Add Stack**
2. Choose **Git Repository**
3. Repository URL: `https://github.com/NetDocuments/legaltech-scraper-web`
4. Compose path: `docker-compose.yml`
5. Click **Deploy the stack**

To pick up new changes: **Recreate** the stack (or pull + restart the container).

### Nginx Reverse Proxy

Add to your nginx config to expose at `/scraper/`:

```nginx
location /scraper/ {
    proxy_pass http://localhost:5050/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_buffering off;
    proxy_cache off;
}
```

---

## Run Locally (Windows)

```bash
pip install flask requests beautifulsoup4 feedparser
python web_app.py
# Opens http://localhost:5050 automatically
```

---

## How It Works

1. Select a **Segment** — scoring weights and available sources adjust automatically
2. Choose **News Sources** and **Competitor Watch** sources (Corporate sources appear/disappear with the segment)
3. Optionally set an **Investigate Term** (+30 pts, ranks same as NetDocuments mentions)
4. Set a **Lookback Window** (7 / 14 / 30 days)
5. Click **▶ Run Scraper** — live log streams progress via SSE
6. Preview the curated email in the iframe
7. **Download Email Draft (.eml)** — double-click to open in Outlook
8. **Download All Articles (.csv)** — full raw dump for further analysis

---

## Source Architecture

| File | Purpose |
|---|---|
| `web_app.py` | Flask routes, job state, SSE stream, CSV/EML endpoints |
| `generate_blast.py` | Scoring engine, HTML builder, `SCORE_RULES`, `SEGMENT_SCORE_MODIFIERS`, `SALES_ANGLES` |
| `sites_config.py` | `SITES` (all segments), `COMPETITOR_SITES`, `CORPORATE_SITES` |
| `templates/index.html` | Single-page UI |
| `data/custom_sites.json` | User-added RSS feeds (auto-created) |

---

## Related

- [LegalTech News Scraper (desktop)](https://github.com/NetDocuments/legaltechnewsscraper) — v1 and v2 desktop EXE versions

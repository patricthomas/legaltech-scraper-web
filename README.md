# LegalTech News Scraper — Web Edition

Flask web app version of the LegalTech News Scraper. Scrapes 20+ legal tech sources, scores articles for NetDocuments relevance, and generates a `.eml` email draft for download — all from a browser.

## Deploy with Docker / Portainer

### Portainer Stack (Git Repository)

1. In Portainer → **Stacks → Add Stack**
2. Choose **Git Repository**
3. Repository URL: `https://github.com/NetDocuments/legaltech-scraper-web`
4. Compose path: `docker-compose.yml`
5. Click **Deploy the stack**

### Nginx reverse proxy

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

## Run locally (Windows)

```bash
pip install flask requests beautifulsoup4 feedparser
python web_app.py
# Opens http://localhost:5050 automatically
```

## How it works

1. Pick segment, competitors, and optional investigate term
2. Click **Run Scraper** — live log shows progress
3. Preview the email in the page
4. Click **Download Email Draft** — double-click the `.eml` to open in Outlook

## Related

- [LegalTech News Scraper (desktop)](https://github.com/NetDocuments/legaltechnewsscraper) — v1 and v2 desktop EXE versions

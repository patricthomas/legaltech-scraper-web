"""
web_app.py  -  Flask web interface for LegalTech News Scraper
"""

import datetime
import io
import json
import logging
import os
import sys
import threading
import webbrowser
from collections import Counter
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from flask import (Flask, Response, jsonify, render_template,
                   request, send_file, stream_with_context)

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
CUSTOM_SITES_FILE = DATA_DIR / "custom_sites.json"

app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))

sys.path.insert(0, str(BASE_DIR))
import generate_blast as gb
from sites_config import COMPETITOR_SITES, SITES

# ---------------------------------------------------------------------------
# Custom sites persistence
# ---------------------------------------------------------------------------
def load_custom_sites() -> list[dict]:
    if CUSTOM_SITES_FILE.exists():
        try:
            return json.loads(CUSTOM_SITES_FILE.read_text())
        except Exception:
            pass
    return []


def save_custom_sites(sites: list[dict]):
    CUSTOM_SITES_FILE.write_text(json.dumps(sites, indent=2))


# ---------------------------------------------------------------------------
# Job state
# ---------------------------------------------------------------------------
_job = {"running": False, "log": [], "html": None, "error": None}
_job_lock = threading.Lock()


def _reset_job():
    with _job_lock:
        _job["running"] = True
        _job["log"] = []
        _job["html"] = None
        _job["error"] = None


def _push_log(msg: str):
    with _job_lock:
        _job["log"].append(msg)


def _finish_job(html=None, error=None):
    with _job_lock:
        _job["running"] = False
        _job["html"] = html
        _job["error"] = error


# ---------------------------------------------------------------------------
# Scrape worker
# ---------------------------------------------------------------------------
def _scrape_worker(segment, investigate_term, selected_news,
                   selected_competitors, max_age_days=7):
    try:
        class SSEHandler(logging.Handler):
            def emit(self, record):
                _push_log(self.format(record))

        handler = SSEHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        gb.log.addHandler(handler)
        gb.log.setLevel(logging.INFO)

        _push_log(f"🔍 Fetching articles (last {max_age_days} days)…")
        news_articles, competitor_articles = gb.fetch_all_articles(
            max_age_days=max_age_days,
            segment=segment
        )

        # Scrape custom RSS feeds
        custom = load_custom_sites()
        for site in custom:
            try:
                custom_articles = gb.scrape_rss(site, max_age_days=max_age_days)
                _push_log(f"  Custom feed '{site['name']}': {len(custom_articles)} articles")
                news_articles.extend(custom_articles)
            except Exception as e:
                _push_log(f"  Custom feed '{site['name']}' error: {e}")

        # Per-source breakdown
        src_counts = Counter(a["source"] for a in news_articles)
        if src_counts:
            parts = [f"{src} ({cnt})"
                     for src, cnt in sorted(src_counts.items(), key=lambda x: -x[1])]
            _push_log("📊 Per source: " + ",  ".join(parts))

        _push_log(f"✅ {len(news_articles)} total articles across {len(src_counts)} sources")

        # Filter to selected news sources (always include custom feeds +
        # Corporate-specific sources when that segment is active)
        if selected_news:
            custom_names = {s["name"] for s in custom}
            corp_names: set[str] = set()
            if segment == "Corporate":
                try:
                    sys.path.insert(0, str(Path(__file__).parent))
                    from sites_config import CORPORATE_SITES
                    corp_names = {s["name"] for s in CORPORATE_SITES}
                except Exception:
                    pass
            news_articles = [
                a for a in news_articles
                if a.get("source", "") in selected_news
                or a.get("source", "") in custom_names
                or a.get("source", "") in corp_names
            ]
            _push_log(f"   → {len(news_articles)} after source filter")

        # Filter competitors
        if selected_competitors:
            competitor_articles = [
                a for a in competitor_articles
                if any(sel.lower() in a.get("source", "").lower()
                       for sel in selected_competitors)
            ]

        _push_log(f"📝 Scoring and curating top {gb.TOP_N} articles…")
        top = gb.curate(news_articles, segment=segment,
                        investigate_term=investigate_term)
        _push_log(f"✅ Selected {len(top)} top articles")

        _push_log("📧 Building email HTML…")
        html = gb.build_html(top, news_articles,
                             competitor_articles=competitor_articles,
                             segment=segment)
        _push_log("✅ Done! Email draft ready to download.")
        _finish_job(html=html)

    except Exception as exc:
        _push_log(f"❌ Error: {exc}")
        _finish_job(error=str(exc))
    finally:
        gb.log.handlers = [h for h in gb.log.handlers
                           if not isinstance(h, SSEHandler)]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    news_sites = []
    seen = set()
    for s in SITES:
        if s["name"] not in seen:
            seen.add(s["name"])
            news_sites.append(s["name"])

    competitors = []
    seen = set()
    for s in COMPETITOR_SITES:
        if s["name"] not in seen:
            seen.add(s["name"])
            competitors.append(s["name"])

    custom_sites = load_custom_sites()

    return render_template("index.html",
                           news_sites=news_sites,
                           competitors=competitors,
                           custom_sites=custom_sites,
                           default_email=gb.RECIPIENTS)


@app.route("/run", methods=["POST"])
def run_scraper():
    if _job["running"]:
        return jsonify({"error": "Already running"}), 409
    data = request.get_json(force=True)
    _reset_job()
    threading.Thread(
        target=_scrape_worker,
        args=(data.get("segment", "Strategic"),
              data.get("investigate_term", ""),
              data.get("news_sites", []),
              data.get("competitors", []),
              int(data.get("days", 7))),
        daemon=True
    ).start()
    return jsonify({"started": True})


@app.route("/add-site", methods=["POST"])
def add_site():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    url  = data.get("url", "").strip()
    if not name or not url:
        return jsonify({"error": "Name and URL are required"}), 400
    sites = load_custom_sites()
    if any(s["url"] == url for s in sites):
        return jsonify({"error": "Feed URL already exists"}), 409
    sites.append({"name": name, "url": url, "rss": url,
                  "article_sel": None, "title_sel": None,
                  "link_sel": None, "desc_sel": None, "base_url": ""})
    save_custom_sites(sites)
    return jsonify({"ok": True, "sites": sites})


@app.route("/remove-site", methods=["POST"])
def remove_site():
    data = request.get_json(force=True)
    url = data.get("url", "")
    sites = [s for s in load_custom_sites() if s["url"] != url]
    save_custom_sites(sites)
    return jsonify({"ok": True, "sites": sites})


@app.route("/stream")
def stream():
    def generate():
        import time
        sent = 0
        while True:
            with _job_lock:
                logs = list(_job["log"])
                running = _job["running"]
            while sent < len(logs):
                yield f"data: {json.dumps({'type': 'log', 'msg': logs[sent]})}\n\n"
                sent += 1
            if not running:
                with _job_lock:
                    err = _job["error"]
                if err:
                    yield f"data: {json.dumps({'type': 'error', 'msg': err})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            time.sleep(0.4)
    return Response(stream_with_context(generate()),
                    mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


@app.route("/get-html")
def get_html():
    with _job_lock:
        html = _job.get("html")
    if not html:
        return jsonify({"error": "No HTML ready"}), 400
    return jsonify({"html": html})


@app.route("/download-eml", methods=["POST"])
def download_eml():
    data = request.get_json(force=True)
    email_to = data.get("email_to", gb.RECIPIENTS).strip() or gb.RECIPIENTS
    with _job_lock:
        html = _job.get("html")
    if not html:
        return jsonify({"error": "No email ready yet"}), 400
    now = datetime.datetime.now()
    subject = gb.EMAIL_SUBJECT.format(date=now.strftime(f"%B {now.day}, %Y"))
    msg = MIMEMultipart("alternative")
    msg["To"] = email_to
    msg["Subject"] = subject
    msg["MIME-Version"] = "1.0"
    msg.attach(MIMEText(html, "html", "utf-8"))
    return send_file(
        io.BytesIO(msg.as_bytes()),
        mimetype="message/rfc822",
        as_attachment=True,
        download_name="LegalTech_News_Blast.eml",
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    if not os.environ.get("DOCKER_ENV"):
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    print(f"LegalTech News Scraper running at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)

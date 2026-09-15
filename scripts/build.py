"""Build the static site and refresh its public TechLaw Watch feed."""
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import argparse
import json
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://pooyash.com"
FEED = "https://www.techlaw.watch/feed"


class ArticleHTML(HTMLParser):
    """Keep readable public article markup, never executable feed content."""
    allowed = {"p", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "strong",
               "em", "b", "i", "pre", "code", "a", "br", "hr", "sup", "sub"}
    blocked = {"script", "style", "iframe", "object", "svg", "form", "figure"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.blocked:
            self.depth += 1
        if self.depth or tag not in self.allowed:
            return
        suffix = ""
        if tag == "a":
            href = dict(attrs).get("href", "")
            if urlparse(href).scheme in {"https", "http", "mailto"}:
                suffix = f' href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer"'
        self.output.append(f"<{tag}{suffix}>")

    def handle_endtag(self, tag):
        if tag in self.blocked:
            self.depth = max(0, self.depth - 1)
            return
        if not self.depth and tag in self.allowed and tag not in {"br", "hr"}:
            self.output.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.depth:
            self.output.append(escape(data))


def sanitize(value):
    parser = ArticleHTML()
    parser.feed(value)
    return "".join(parser.output)


def plain(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", value)).strip()


def date_key(post):
    return datetime.strptime(post["date"], "%B %d, %Y")


def get_posts(refresh):
    cached = json.loads((ROOT / "content/posts.json").read_text())
    posts = {p["slug"]: p for p in cached}
    if refresh:
        request = Request(FEED, headers={"User-Agent": "PooyaShoghiWebsite/1.0 (+https://pooyash.com)"})
        with urlopen(request, timeout=30) as response:
            data = response.read(10_000_001)
        if len(data) > 10_000_000:
            raise ValueError("Feed exceeded the expected size")
        items = ET.fromstring(data).findall("./channel/item")
        if not items:
            raise ValueError("Feed contained no posts; preserving the currently deployed site")
        for item in items:
            url = item.findtext("link", "")
            parsed = urlparse(url)
            slug = parsed.path.rstrip("/").split("/")[-1]
            if parsed.hostname != "www.techlaw.watch" or not re.fullmatch(r"[a-z0-9-]+", slug):
                continue
            body = item.findtext("{http://purl.org/rss/1.0/modules/content/}encoded", "")
            if not body:
                body = item.findtext("description", "")
            date = parsedate_to_datetime(item.findtext("pubDate")).strftime("%B %d, %Y").replace(" 0", " ")
            posts[slug] = {"title": item.findtext("title"), "date": date, "url": url,
                           "slug": slug, "body": sanitize(body)}
        if len(posts) == 0:
            raise ValueError("No usable posts")
        (ROOT / "content/posts.json").write_text(json.dumps(list(posts.values()), ensure_ascii=False, indent=2) + "\n")
    for post in posts.values():
        post["body"] = sanitize(post["body"])
    return sorted(posts.values(), key=date_key, reverse=True)


def fill(template, values):
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", str(value))
    return template


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh-feed", action="store_true")
    args = parser.parse_args()
    posts = get_posts(args.refresh_feed)
    publications = json.loads((ROOT / "content/publications.json").read_text())
    dest = ROOT / "_site"
    dest.mkdir(exist_ok=True)
    shutil.copytree(ROOT / "assets", dest / "assets", dirs_exist_ok=True)
    shutil.copy2(ROOT / "CNAME", dest / "CNAME")
    (dest / ".nojekyll").touch()
    urls = []

    def write(path, view, title, description, content, og_type="website"):
        template = (ROOT / "templates/site.html").read_text()
        selected = "writing" if view == "reader" else view
        template = template.replace(f'data-page="{selected}"', f'data-page="{selected}" aria-current="page"')
        html = fill(template, {"CONTENT": content, "TITLE": escape(title),
                              "DESCRIPTION": escape(description, quote=True),
                              "CANONICAL": ORIGIN + path, "VIEW": view, "OG_TYPE": og_type,
                              "YEAR": datetime.now(timezone.utc).year})
        if re.search(r"\{\{[A-Z_]+\}\}", html):
            raise ValueError("Unresolved template field in " + path)
        target = dest / path.lstrip("/") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)
        urls.append(ORIGIN + path)

    descriptions = {
        "tech-law-and-policy-briefing-november": "What I have lately found interesting in the world of tech law & policy.",
        "beyond-copyright-reddit-v-anthropic": "Five legal theories beyond copyright.",
        "republican-unity-on-ai-moratorium": "A closer look at the debate over federal and state AI rules.",
    }
    cards = []
    for post in posts[:3]:
        title = post["title"].replace(" (November 11, 2025)", "")
        excerpt = descriptions.get(post["slug"], plain(post["body"])[:180].rsplit(" ", 1)[0] + "…")
        cards.append(f'<article class="ps-post"><div class="ps-label">TechLaw Watch / {escape(post["date"])}</div>'
                     f'<a class="ps-post-link" href="/writing/{post["slug"]}/"><h3>{escape(title)}</h3>'
                     f'<p>{escape(excerpt)}</p><span class="ps-link">Read here →</span></a></article>')
    home = fill((ROOT / "templates/home.html").read_text(), {"LATEST_POSTS": "\n".join(cards)})
    write("/", "home", "Pooya Shoghi | IP & Technology Attorney",
          "IP and technology attorney with experience in prosecution and litigation. Writing, research, and software tools at the intersection of law and technology.", home)

    entries = []
    all_writing = publications + [dict(p, kind="newsletter", source="TechLaw Watch", author="Pooya Shoghi") for p in posts]
    for item in sorted(all_writing, key=date_key, reverse=True):
        internal = item["kind"] == "newsletter"
        url = "/writing/" + item["slug"] + "/" if internal else item["url"]
        attrs = "" if internal else ' target="_blank" rel="noopener noreferrer"'
        action = "Read on this site →" if internal else "Read preprint ↗" if item["kind"] == "research" else "Read at publisher ↗"
        entries.append(f'<article class="ps-entry" data-kind="{item["kind"]}"><div class="ps-meta">{escape(item["date"])}</div>'
                       f'<div><div class="ps-label">{escape(item["source"])}</div><a href="{escape(url, quote=True)}"{attrs}>'
                       f'<h3>{escape(item["title"])}</h3></a><p class="ps-meta">{escape(item["author"])} · {action}</p></div></article>')
    library = fill((ROOT / "templates/writing.html").read_text(), {"LIBRARY": "\n".join(entries)})
    write("/writing/", "writing", "Writing | Pooya Shoghi", "Publications, research, and TechLaw Watch articles by Pooya Shoghi.", library)
    for view, title, description in [
        ("tools", "Software Tools", "Software for invention disclosure, patent analysis, and legal research."),
        ("about", "About & Speaking", "Pooya Shoghi’s legal practice, professional leadership, and speaking topics."),
    ]:
        write("/" + view + "/", view, title + " | Pooya Shoghi", description, (ROOT / f"templates/{view}.html").read_text())
    for post in posts:
        article = fill((ROOT / "templates/reader.html").read_text(), {
            "POST_TITLE": escape(post["title"]), "POST_BODY": post["body"],
            "POST_META": "Pooya Shoghi · " + escape(post["date"]) + " · Originally published in TechLaw Watch",
            "POST_URL": escape(post["url"], quote=True),
        })
        write("/writing/" + post["slug"] + "/", "reader", post["title"] + " | Pooya Shoghi",
              descriptions.get(post["slug"], plain(post["body"])[:155]), article, "article")
    (dest / "newsletter").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "newsletter/index.html", dest / "newsletter/index.html")
    (dest / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: https://pooyash.com/sitemap.xml\n")
    (dest / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(f"<url><loc>{escape(url)}</loc></url>" for url in urls) + "\n</urlset>\n")
    print(f"Built {len(urls)} pages with {len(posts)} TechLaw Watch posts.")


if __name__ == "__main__":
    main()

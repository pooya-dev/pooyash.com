# Pooya Shoghi

Personal website at https://pooyash.com, hosted by GitHub Pages.

The approved editorial design uses plain HTML, CSS, and JavaScript. Python 3 generates static pages, including a permanent URL for each imported TechLaw Watch post. No third-party Python packages are needed.

## Updating the site

- Biography and page content: `templates/`.
- Publication and research references: `content/publications.json`.
- Portrait and appearance: `assets/`.
- Cached public newsletter content: `content/posts.json`.

Run `python3 scripts/build.py` to build from the saved content, or add `--refresh-feed` to refresh https://www.techlaw.watch/feed. Preview the generated `_site` directory with a local HTTP server.

The Publish website workflow builds and deploys on every push to main, on manual dispatch, and daily at 11:23 UTC. New public RSS content is imported and sanitized. It preserves previously imported articles in an Actions cache and the committed starting archive. If a feed refresh fails, the current live deployment remains in place. Subscription and discussion links lead to TechLaw Watch; third-party publications link to their publishers.

Domain: `pooyash.com`, with HTTPS and a www-to-apex redirect managed by GitHub Pages. DNS is managed at GoDaddy.

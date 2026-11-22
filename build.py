#!/usr/bin/env python3
"""Build the website from the Markdown files in content/.

    python3 build.py           # write the site to public/
    python3 build.py --serve   # build, serve on http://localhost:8000, rebuild on every save

Only the Python standard library is needed. The Markdown conventions are described in README.md.
"""
import argparse
import html
import re
import shutil
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT, SRC, ASSETS, PUBLIC = (ROOT / name for name in ("content", "src", "assets", "public"))

# Sections below About, in page order: content/<name>.md becomes <section id="<name>"> and a nav link
SECTIONS = ["publications", "projects", "blog"]

LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
VENUE = re.compile(r"\*(?!\*)(.+?)(?<!\*)\*")


def fail(message):
    raise SystemExit(f"build.py: {message}")


# ---- Inline Markdown: [links](url), **bold**, *italic* ----

def emphasis(text):
    text = html.escape(text, quote=False)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)


def anchor(url, text, css_class=None):
    """External links open in a new tab; mailto links do not."""
    css = f' class="{css_class}"' if css_class else ""
    target = ' target="_blank"' if url.startswith("http") else ""
    return f'<a{css} href="{html.escape(url)}"{target}>{text}</a>'


def inline(text, link_class=None):
    parts, last = [], 0
    for match in LINK.finditer(text):
        parts.append(emphasis(text[last:match.start()]))
        parts.append(anchor(match.group(2), emphasis(match.group(1)), link_class))
        last = match.end()
    parts.append(emphasis(text[last:]))
    return "".join(parts)


# ---- Block structure ----

def paragraphs(text):
    """Blank-line separated paragraphs, each joined onto a single line."""
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]


def is_links(paragraph):
    """A line made only of links, e.g. [paper](...) · [code](...)."""
    return bool(LINK.search(paragraph)) and not re.sub(r"[·|\s]", "", LINK.sub("", paragraph))


def read(name):
    """Return the '# Title' of content/<name>.md and the text after it."""
    path = CONTENT / f"{name}.md"
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    title, _, body = path.read_text(encoding="utf-8").strip().partition("\n")
    if not title.startswith("# "):
        fail(f"{path.relative_to(ROOT)} must start with a '# Title' line")
    return title[2:].strip(), body


def links_bar(paragraph, css_class, indent):
    links = "\n".join(f"{indent}  {anchor(url, emphasis(text))}" for text, url in LINK.findall(paragraph))
    return f'{indent}<div class="{css_class}">\n{links}\n{indent}</div>'


# ---- Page parts ----

def render_about():
    name, body = read("about")
    paras = paragraphs(body)
    photo = next((IMAGE.fullmatch(p) for p in paras if IMAGE.fullmatch(p)), None)
    social = next((p for p in paras if is_links(p)), None)
    text = [p for p in paras if not IMAGE.fullmatch(p) and p != social]
    if not text:
        fail("content/about.md needs a contact line below the name")
    contact, bio = text[0], text[1:]

    lines = [
        '    <section id="about">',
        '      <div class="about-text">',
        f"        <h2>{emphasis(name)}</h2>",
        f'        <p style="margin-top: 0em; margin-bottom: 2em;">{inline(contact)}</p>',
        *(f"        <p>{inline(p, 'inline')}</p>" for p in bio),
        "      </div>",
    ]
    if photo:
        alt, src = photo.groups()
        lines += [
            '      <div class="about-photo">',
            f'        <img src="{html.escape(src)}" alt="{html.escape(alt)}">',
            "      </div>",
        ]
    lines.append("    </section>")
    if social:
        lines += ["", links_bar(social, "about-links", "    ")]
    return "\n".join(lines)


def render_entry(where, heading, paras):
    """One '## [Title](url)' entry. Before its links line come the image, authors, and *venue*;
    every paragraph after the links line is the description."""
    title_link = LINK.fullmatch(heading)
    title, url = title_link.groups() if title_link else (heading, None)
    at = next((i for i, p in enumerate(paras) if is_links(p)), None)
    if at is None:
        fail(f"{where}: '{title}' needs a line of links, e.g. [paper](https://...)")

    thumb = authors = venue = None
    for p in paras[:at]:
        if IMAGE.fullmatch(p):
            thumb = IMAGE.fullmatch(p).groups()
        elif VENUE.fullmatch(p):
            venue = VENUE.fullmatch(p).group(1)
        else:
            authors = p
    url = url or LINK.search(paras[at]).group(2)

    lines = ['      <article class="entry">']
    if thumb:
        alt, src = thumb
        lines += [
            f'        <a class="entry-thumb" href="{html.escape(url)}" target="_blank">',
            f'          <img src="{html.escape(src)}" alt="{html.escape(alt)}" loading="lazy">',
            "        </a>",
        ]
    lines += [
        '        <div class="entry-body">',
        f"          <h3>{anchor(url, emphasis(title))}</h3>",
    ]
    if authors:
        lines.append(f'          <p class="authors">{inline(authors)}</p>')
    if venue:
        lines.append(f'          <p class="venue">{inline(venue)}</p>')
    lines.append(links_bar(paras[at], "entry-links", "          "))
    lines += [f'          <p class="desc">{inline(p)}</p>' for p in paras[at + 1:]]
    lines += ["        </div>", "      </article>"]
    return "\n".join(lines)


def render_section(name):
    title, body = read(name)
    entries = []
    for chunk in re.split(r"^##\s+", body, flags=re.M)[1:]:
        heading, _, text = chunk.partition("\n")
        entries.append(render_entry(f"content/{name}.md", heading.strip(), paragraphs(text)))
    return "\n\n".join([
        f'    <section id="{name}" class="list-section">',
        f'      <h2 class="section-title">{emphasis(title)}</h2>',
        *entries,
    ]) + "\n    </section>"


def build(clean=True):
    nav = ['        <li><a href="#about">About</a></li>']
    nav += [f'        <li><a href="#{name}">{emphasis(read(name)[0])}</a></li>' for name in SECTIONS]
    main = "\n\n".join([render_about(), *(render_section(name) for name in SECTIONS)])
    page = (SRC / "template.html").read_text(encoding="utf-8")
    page = page.replace("{{ nav }}", "\n".join(nav)).replace("{{ main }}", main)

    if clean and PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(exist_ok=True)
    skip = shutil.ignore_patterns(".DS_Store")
    for item in SRC.iterdir():
        if item.name == "template.html" or item.name.startswith("."):
            continue
        if item.is_dir():
            shutil.copytree(item, PUBLIC / item.name, dirs_exist_ok=True, ignore=skip)
        else:
            shutil.copy2(item, PUBLIC / item.name)
    shutil.copytree(ASSETS, PUBLIC / "assets", dirs_exist_ok=True, ignore=skip)
    (PUBLIC / ".nojekyll").touch()  # Serve files as they are, without GitHub's Jekyll processing
    (PUBLIC / "index.html").write_text(page, encoding="utf-8")


# ---- Local preview ----

class PreviewHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # Always show the latest build
        super().end_headers()

    def log_message(self, *args):
        pass


def watched_files():
    return {p: p.stat().st_mtime for folder in (CONTENT, SRC, ASSETS) for p in folder.rglob("*") if p.is_file()}


def serve(port):
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(PreviewHandler, directory=str(PUBLIC)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Serving http://localhost:{port}/ and rebuilding on changes (Ctrl+C to stop)")
    seen = watched_files()
    try:
        while True:
            time.sleep(0.5)
            if (current := watched_files()) != seen:
                seen = current
                try:
                    build(clean=False)
                    print(time.strftime("%H:%M:%S"), "rebuilt")
                except SystemExit as error:
                    print(error)
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the website from content/*.md.")
    parser.add_argument("--serve", action="store_true", help="serve locally and rebuild on changes")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    build()
    print(f"Built {PUBLIC.relative_to(ROOT)}/index.html")
    if args.serve:
        serve(args.port)

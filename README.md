# konradszafer.github.io

The page is written in Markdown, one file per section, and built into `public/` by `build.py`.
Pushing to `main` builds and deploys it automatically.

## Editing

```
content/about.md          name, contact line, bio, photo, social links
content/publications.md   one "## " entry per paper
content/projects.md       one "## " entry per project
content/blog.md           one "## " entry per post
```

Preview while you edit; the page rebuilds on every save:

```bash
python3 build.py --serve
```

Then open http://localhost:8000.

## Writing an entry

Each paragraph (separated by a blank line) has a fixed role:

```markdown
## [Title](https://link-for-title-and-thumbnail)

![Alt text for the thumbnail](../assets/thumbs/figure.png)

**Konrad Szafer**, Co-Author, Co-Author

*Venue · Year*

[paper](https://...) · [code](https://...)

Description, one or more paragraphs.
```

- The links line is required. Everything after it is the description.
- The image, authors, and *italic* venue lines are optional. Projects, for example, skip the authors.
- Supported formatting: `[links](url)`, `**bold**`, and `*italic*`.

In `content/about.md`, the first paragraph after the name is the contact line, the image is the photo, the links line is the social bar, and every other paragraph is the bio.

## Layout and styling

- `src/template.html`: page head, navigation, and scripts
- `src/styles.css`: all styling, including dark mode
- `assets/`: images and figures
- New section: add `content/<name>.md` and its name to `SECTIONS` in `build.py`. It gets its own nav link.

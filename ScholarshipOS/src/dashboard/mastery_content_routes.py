import os, json, re, html as html_mod
from fastapi import APIRouter, HTTPException


MASTERY_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'scholarship-mastery')

router = APIRouter(prefix="/api/mastery-content", tags=["mastery-content"])

def _ensure_dir():
    if not os.path.exists(MASTERY_DIR):
        raise HTTPException(status_code=404, detail="Mastery directory not found")

def _read_markdown(filepath):
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def _md_to_html(md):
    lines = md.split("\n")
    html = []
    in_list = False
    in_table = False
    table_html = []
    in_code = False
    code_lines = []
    in_blockquote = False
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Code block
        if stripped.startswith("```"):
            if in_code:
                code = html_mod.escape("\n".join(code_lines))
                html.append(f'<pre><code>{code}</code></pre>')
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Close list on non-list item
        if in_list and not stripped.startswith("- ") and not stripped.startswith("* ") and not re.match(r'^\d+\.\s', stripped) and stripped != "":
            html.append("</ul>")
            in_list = False

        # Close blockquote
        if in_blockquote and not stripped.startswith(">"):
            html.append("</blockquote>")
            in_blockquote = False

        # Empty line
        if stripped == "":
            if in_table:
                html.append('<div class="mastery-table-wrap"><table class="mastery-table">' + "".join(table_html) + "</table></div>")
                table_html = []
                in_table = False
            i += 1
            continue

        # Headings
        if stripped.startswith("###### "):
            html.append(f"<h6>{html_mod.escape(stripped[7:])}</h6>")
        elif stripped.startswith("##### "):
            html.append(f"<h5>{html_mod.escape(stripped[6:])}</h5>")
        elif stripped.startswith("#### "):
            html.append(f"<h4>{html_mod.escape(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            html.append(f"<h3>{html_mod.escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html.append(f"<h2>{html_mod.escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html.append(f"<h1>{html_mod.escape(stripped[2:])}</h1>")

        # Blockquote
        elif stripped.startswith("> "):
            if not in_blockquote:
                html.append("<blockquote>")
                in_blockquote = True
            html.append(f"<p>{_render_inline(stripped[2:])}</p>")

        # Table
        elif "|" in stripped and stripped.startswith("|"):
            in_table = True
            cells = [c.strip() for c in stripped.split("|") if c.strip()]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                pass  # separator row
            else:
                table_html.append("<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in cells) + "</tr>")

        # Ordered list
        elif re.match(r'^\d+\.\s', stripped):
            if not in_list:
                html.append("<ul>")
                in_list = True
            content = re.sub(r'^\d+\.\s', '', stripped)
            html.append(f"<li>{_render_inline(content)}</li>")

        # Unordered list
        elif stripped.startswith("- ") or stripped.startswith("* "):
            if not in_list:
                html.append("<ul>")
                in_list = True
            content = stripped[2:] if stripped.startswith("- ") else stripped[2:]
            # Handle checkbox
            if content.startswith("[ ] "):
                html.append(f'<li><input type="checkbox" disabled> {_render_inline(content[4:])}</li>')
            elif content.startswith("[x] ") or content.startswith("[X] "):
                html.append(f'<li><input type="checkbox" disabled checked> {_render_inline(content[4:])}</li>')
            else:
                html.append(f"<li>{_render_inline(content)}</li>")

        # HR
        elif re.match(r'^[-*_]{3,}$', stripped):
            html.append("<hr>")

        # Paragraph (with bold markers)
        else:
            html.append(f"<p>{_render_inline(stripped)}</p>")

        i += 1

    if in_list:
        html.append("</ul>")
    if in_blockquote:
        html.append("</blockquote>")
    if in_code:
        code = html_mod.escape("\n".join(code_lines))
        html.append(f'<pre><code>{code}</code></pre>')
    if in_table:
        html.append('<div class="mastery-table-wrap"><table class="mastery-table">' + "".join(table_html) + "</table></div>")

    return "".join(html)

def _render_inline(text):
    text = html_mod.escape(text)
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    # Code inline
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    return text

def _parse_program_meta(filepath):
    content = _read_markdown(filepath)
    if not content:
        return None
    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else os.path.basename(filepath).replace(".md", "")
    slug = os.path.basename(filepath).replace(".md", "")
    # Extract program code from title
    code_match = re.match(r'^([A-Za-z0-9-]+)\s*[—–-]\s*(.+)$', title)
    code = code_match.group(1) if code_match else slug
    subtitle = code_match.group(2) if code_match else ""
    return {
        "slug": slug,
        "title": title,
        "code": code,
        "subtitle": subtitle,
        "filename": os.path.basename(filepath),
    }

@router.get("/programs")
def list_programs():
    _ensure_dir()
    progs_dir = os.path.join(MASTERY_DIR, "programs")
    if not os.path.exists(progs_dir):
        return {"programs": []}
    files = sorted([f for f in os.listdir(progs_dir) if f.endswith(".md")])
    programs = []
    for f in files:
        if "other" in f.lower() or "other-scholarships" in f.lower():
            continue
        meta = _parse_program_meta(os.path.join(progs_dir, f))
        if meta:
            programs.append(meta)
    return {"programs": programs}

@router.get("/programs/{slug:path}")
def get_program(slug: str):
    _ensure_dir()
    # Support both numeric prefix and name-based slugs
    progs_dir = os.path.join(MASTERY_DIR, "programs")
    if not os.path.exists(progs_dir):
        raise HTTPException(status_code=404, detail="Programs directory not found")

    # Direct match
    filepath = os.path.join(progs_dir, f"{slug}.md")
    if os.path.exists(filepath):
        md = _read_markdown(filepath)
        return {"markdown": md, "html": _md_to_html(md), "slug": slug}

    # Search by partial name match
    for f in os.listdir(progs_dir):
        if f.endswith(".md"):
            base = f.replace(".md", "")
            if slug.lower() in base.lower() or base.lower() in slug.lower():
                filepath = os.path.join(progs_dir, f)
                md = _read_markdown(filepath)
                return {"markdown": md, "html": _md_to_html(md), "slug": base}

    raise HTTPException(status_code=404, detail=f"Program '{slug}' not found")

@router.get("/guides")
def list_guides():
    _ensure_dir()
    guides_dir = os.path.join(MASTERY_DIR, "guides")
    if not os.path.exists(guides_dir):
        return {"guides": []}
    files = sorted([f for f in os.listdir(guides_dir) if f.endswith(".md")])
    guides = []
    for f in files:
        filepath = os.path.join(guides_dir, f)
        content = _read_markdown(filepath)
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE) if content else None
        title = title_match.group(1).strip() if title_match else f.replace(".md", "").replace("-", " ").title()
        slug = f.replace(".md", "")
        # Estimate read time
        word_count = len(content.split()) if content else 0
        read_time = max(1, round(word_count / 200))
        guides.append({
            "slug": slug,
            "title": title,
            "filename": f,
            "read_time": read_time,
            "word_count": word_count,
        })
    return {"guides": guides}

@router.get("/guides/{slug:path}")
def get_guide(slug: str):
    _ensure_dir()
    guides_dir = os.path.join(MASTERY_DIR, "guides")
    if not os.path.exists(guides_dir):
        raise HTTPException(status_code=404)

    filepath = os.path.join(guides_dir, f"{slug}.md")
    if os.path.exists(filepath):
        md = _read_markdown(filepath)
        return {"markdown": md, "html": _md_to_html(md), "slug": slug}

    for f in os.listdir(guides_dir):
        if f.endswith(".md"):
            base = f.replace(".md", "")
            if slug.lower() in base.lower() or base.lower() in slug.lower():
                filepath = os.path.join(guides_dir, f)
                md = _read_markdown(filepath)
                return {"markdown": md, "html": _md_to_html(md), "slug": base}

    raise HTTPException(status_code=404, detail=f"Guide '{slug}' not found")

@router.get("/dashboard")
def get_dashboard_data():
    _ensure_dir()
    # Read from scholarship-data.js file
    js_path = os.path.join(MASTERY_DIR, "dashboard", "scholarship-data.js")
    if not os.path.exists(js_path):
        return {"timelines": {}, "programs": []}

    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()

    # Extract timelines
    timelines = {}
    tl_matches = re.finditer(r"(\w+):\s*\[([\s\S]*?)\]\s*\}", js_content)
    for m in tl_matches:
        key = m.group(1)
        if key in ("erasmus", "mbzuai", "daad", "fulbright", "chevening", "commonwealth", "all"):
            items_text = m.group(2)
            items = re.findall(r"\{d:'(.*?)',t:'(.*?)',c:'(.*?)'\}", items_text)
            timelines[key] = [{"date": d, "title": t, "description": c} for d, t, c in items]

    # Extract programs summary
    programs = []
    prog_blocks = re.findall(r"\{[^{}]*?id:'(.*?)'[\s\S]*?mp:(\d+)", js_content, re.DOTALL)
    seen_ids = set()
    for bid, match_str in prog_blocks:
        if bid in seen_ids:
            continue
        seen_ids.add(bid)
        # Extract fields from this block's region
        block_start = js_content.find(f"id:'{bid}'")
        block_end = js_content.find("},", block_start)
        if block_end == -1:
            block_end = block_start + 500
        block_text = js_content[block_start:block_end]
        n_match = re.search(r"n:'(.*?)'", block_text)
        f_match = re.search(r"f:'(.*?)'", block_text)
        cat_match = re.search(r"cat:'(.*?)'", block_text)
        programs.append({
            "id": bid,
            "name": n_match.group(1) if n_match else bid,
            "full_name": f_match.group(1) if f_match else "",
            "category": cat_match.group(1) if cat_match else "",
            "match": int(match_str),
        })

    return {
        "timelines": timelines,
        "programs": programs,
        "last_updated": "27 Jun 2026",
    }

@router.get("/readme")
def get_readme():
    _ensure_dir()
    filepath = os.path.join(MASTERY_DIR, "README.md")
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404)
    md = _read_markdown(filepath)
    return {"markdown": md, "html": _md_to_html(md)}

@router.get("/overview")
def get_overview():
    _ensure_dir()
    progs_dir = os.path.join(MASTERY_DIR, "programs")
    guides_dir = os.path.join(MASTERY_DIR, "guides")
    programs_count = len([f for f in os.listdir(progs_dir) if f.endswith(".md")]) if os.path.exists(progs_dir) else 0
    guides_count = len([f for f in os.listdir(guides_dir) if f.endswith(".md")]) if os.path.exists(guides_dir) else 0

    readme = _read_markdown(os.path.join(MASTERY_DIR, "README.md"))
    focus_areas = []
    if readme:
        for line in readme.split("\n"):
            if "**Focus:**" in line or "**focus:**" in line:
                focus_areas.append(line.strip())

    return {
        "programs_count": programs_count,
        "guides_count": guides_count,
        "focus_areas": focus_areas,
        "dashboard_files": sorted(os.listdir(os.path.join(MASTERY_DIR, "dashboard"))) if os.path.exists(os.path.join(MASTERY_DIR, "dashboard")) else [],
    }

import json, os, datetime, re, urllib.request
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from spellchecker import SpellChecker
from fpdf import FPDF
from io import BytesIO

app = Flask(__name__)
CORS(app)

ARTICLES_FILE = os.path.join(os.path.dirname(__file__), "articles.json")
spell = SpellChecker()

CATEGORIES = {
    "ielts_t1_ac":  {"label": "IELTS Academic Task 1",       "target": 150,  "color": "#6366f1"},
    "ielts_t2":     {"label": "IELTS Academic Task 2",       "target": 250,  "color": "#8b5cf6"},
    "gre_issue":    {"label": "GRE Issue Task",              "target": 500,  "color": "#ec4899"},
    "ielts_cue":    {"label": "IELTS Speaking Cue Cards",    "target": 150,  "color": "#f59e0b"},
    "general":      {"label": "General Practice",            "target": 0,    "color": "#6b7280"},
}

COMMON_WORDS = {
    "good","bad","nice","big","small","get","got","very","really","stuff","things","thing",
    "a lot","lots","pretty","kind of","sort of","basically","actually","just","maybe",
    "perhaps","probably","always","never","always","sure","yes","no","okay","well","so",
    "then","also","too","much","many","some","a little","a bit","like","really","really",
    "think","know","want","need","use","make","take","give","come","go","see","look",
    "find","tell","ask","try","leave","call","put","mean","keep","let","begin","seem",
    "help","turn","show","hear","play","run","move","live","believe","hold","bring",
    "happen","write","provide","sit","stand","lose","pay","meet","include","continue",
    "set","learn","change","lead","understand","watch","follow","stop","create","speak",
    "read","allow","add","spend","grow","open","walk","win","teach","offer","remember",
    "love","consider","appear","buy","wait","serve","die","send","expect","build",
    "stay","fall","cut","reach","kill","remain","suggest","raise","produce","eat",
    "contain","cover","ride","buy","choose","decide","hate","hope","wish","wonder",
}

def load_articles():
    if not os.path.exists(ARTICLES_FILE):
        return {}
    with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_articles(articles):
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)

def word_stats(text):
    words = text.strip().split()
    word_count = len(words)
    sentences = len([s for s in re.split(r'[.!?]+', text) if s.strip()])
    paragraphs = len([p for p in text.split("\n") if p.strip()])
    return {
        "word_count": word_count,
        "char_count": len(text),
        "char_no_space": len(text.replace(" ", "")),
        "sentences": max(sentences, 0),
        "paragraphs": max(paragraphs, 0),
        "avg_word_length": round(sum(len(w.strip(".,!?;:\"'()[]{}")) for w in words) / word_count, 1) if word_count else 0,
    }

def vocab_analysis(text):
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    basic = set()
    for w in words:
        if w in COMMON_WORDS:
            basic.add(w)
    unique_words = set(words)
    basic_count = sum(1 for w in words if w in COMMON_WORDS)
    advanced_count = len(words) - basic_count

    from collections import Counter
    freq = Counter(words)
    most_common = freq.most_common(1)
    most_frequent = {"word": most_common[0][0], "count": most_common[0][1]} if most_common else None
    top_words = [{"word": w, "count": c} for w, c in freq.most_common(10)]

    return {
        "total_words": len(words),
        "unique_words": len(unique_words),
        "basic_words": sorted(basic),
        "basic_count": basic_count,
        "advanced_count": advanced_count,
        "vocab_score": round((advanced_count / len(words)) * 100, 1) if len(words) else 0,
        "most_frequent": most_frequent,
        "top_words": top_words,
    }

def sentence_analysis(text):
    sents = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sents:
        return {"total":0,"avg_words":0,"simple":0,"compound":0,"complex":0,"passive":0,"short":0,"medium":0,"long":0}
    coord = {"and","but","or","so","yet","for","nor"}
    subord = {"because","although","while","since","if","when","unless","whereas","though","whereas","wherever","whenever","after","before","until","as","once","that","whether","which","who","whom","whose"}
    simple=compound=complex=passive=short=medium=long=0
    for s in sents:
        words = len(s.split())
        if words < 10: short+=1
        elif words <= 20: medium+=1
        else: long+=1
        low = s.lower()
        has_coord = any(c in low.split() for c in coord)
        has_sub = any(c in low.split() for c in subord)
        if has_sub: complex+=1
        elif has_coord: compound+=1
        else: simple+=1
        if re.search(r'\b(?:is|are|was|were|been|being|be)\s+\w+ed\b', low):
            passive+=1
    return {
        "total": len(sents),
        "avg_words": round(sum(len(s.split()) for s in sents)/len(sents),1),
        "simple": simple, "compound": compound, "complex": complex,
        "passive": passive,
        "short": short, "medium": medium, "long": long,
    }

GRAMMAR_RULES = [
    (r'\ba\s+[aeiou][a-z]*\b', lambda m: m.group().replace("a ","an ",1), "Article (a/an)"),
    (r'\ban\s+[^aeiou\s][a-z]*\b', lambda m: m.group().replace("an ","a ",1), "Article (a/an)"),
    (r'\bmore\s+better\b', "better", "Comparative"),
    (r'\bmore\s+worse\b', "worse", "Comparative"),
    (r'\bmore\s+bigger\b', "bigger", "Comparative"),
    (r'\btheirs\s+[a-z]+s\b', None, "Possessive"),
    (r"\bdon't\s+have\s+no\b", "don't have any", "Double Negative"),
    (r"\bcan't\s+hardly\b", "can hardly", "Double Negative"),
    (r"\bdepend\s+of\b", "depend on", "Preposition"),
    (r"\bdiscuss\s+about\b", "discuss", "Preposition"),
    (r"\bmention\s+about\b", "mention", "Redundancy"),
    (r"\breason\s+why\b", "reason", "Redundancy"),
    (r"\bbetter\s+then\b", "better than", "Then/Than"),
    (r"\bmore\s+then\b", "more than", "Then/Than"),
    (r"\bless\s+then\b", "less than", "Then/Than"),
    (r"\baccording\s+to\s+me\b", "in my opinion", "Formality"),
    (r"\bhe\s+don't\b", "he doesn't", "Subject-Verb"),
    (r"\bshe\s+don't\b", "she doesn't", "Subject-Verb"),
    (r"\bit\s+don't\b", "it doesn't", "Subject-Verb"),
    (r"\bthey\s+doesn't\b", "they don't", "Subject-Verb"),
    (r"\bhe\s+go\b", "he goes", "Subject-Verb"),
    (r"\bshe\s+go\b", "she goes", "Subject-Verb"),
    (r"\bhe\s+make\b", "he makes", "Subject-Verb"),
    (r"\bshe\s+make\b", "she makes", "Subject-Verb"),
    (r"\bhe\s+take\b", "he takes", "Subject-Verb"),
    (r"\bshe\s+take\b", "she takes", "Subject-Verb"),
    (r"\bis\s+are\b", "is", "Verb Form"),
    (r"\bare\s+is\b", "are", "Verb Form"),
]

def grammar_check(text):
    issues = []
    for pattern, replacement, rule_name in GRAMMAR_RULES:
        for m in re.finditer(pattern, text, re.IGNORECASE):
            orig = m.group()
            if callable(replacement):
                sug = replacement(m)
            else:
                sug = replacement
            ctx_start = max(0, m.start()-30)
            ctx_end = min(len(text), m.end()+30)
            context = text[ctx_start:ctx_end].strip()
            issues.append({
                "type": rule_name,
                "original": orig,
                "suggestion": sug,
                "context": context,
            })
    return issues

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config")
def get_config():
    return jsonify({"categories": CATEGORIES})

@app.route("/api/articles", methods=["GET"])
def get_articles():
    articles = load_articles()
    keyword_filter = request.args.get("keyword", "").strip().lower()
    items = []
    for key, val in articles.items():
        stats = word_stats(val.get("content", ""))
        item = {
            "id": key,
            "title": val["title"],
            "subtitle": val.get("subtitle", ""),
            "content": val.get("content", ""),
            "category": val.get("category", "general"),
            "keywords": val.get("keywords", []),
            "updated": val.get("updated", val.get("created", "")),
            "word_count": stats["word_count"],
            "reads": val.get("reads", 0),
        }
        if keyword_filter:
            item_keywords = [k.lower() for k in val.get("keywords", [])]
            if keyword_filter not in item_keywords:
                continue
        items.append(item)
    items.sort(key=lambda x: x["updated"], reverse=True)
    return jsonify(items)

@app.route("/api/articles/<article_id>", methods=["GET"])
def get_article(article_id):
    articles = load_articles()
    if article_id not in articles:
        return jsonify({"error": "not found"}), 404
    a = articles[article_id]
    result = dict(a)
    result.setdefault("reads", 0)
    result["stats"] = word_stats(a.get("content", ""))
    result["vocab"] = vocab_analysis(a.get("content", ""))
    return jsonify(result)

@app.route("/api/articles", methods=["POST"])
def create_article():
    data = request.json
    title = data.get("title", "").strip()
    content = data.get("content", "")
    category = data.get("category", "general")
    if not title:
        return jsonify({"error": "Title is required"}), 400
    articles = load_articles()
    article_id = str(int(datetime.datetime.now().timestamp() * 1000))
    now = datetime.datetime.now().isoformat()
    articles[article_id] = {
        "title": title,
        "subtitle": data.get("subtitle", ""),
        "content": content,
        "category": category if category in CATEGORIES else "general",
        "keywords": data.get("keywords", []),
        "reads": 0,
        "created": now,
        "updated": now,
    }
    save_articles(articles)
    return jsonify({"id": article_id}), 201

@app.route("/api/articles/<article_id>", methods=["PUT"])
def update_article(article_id):
    articles = load_articles()
    if article_id not in articles:
        return jsonify({"error": "not found"}), 404
    data = request.json
    if "title" in data:
        articles[article_id]["title"] = data["title"].strip()
    if "subtitle" in data:
        articles[article_id]["subtitle"] = data["subtitle"]
    if "content" in data:
        articles[article_id]["content"] = data["content"]
    if "category" in data and data["category"] in CATEGORIES:
        articles[article_id]["category"] = data["category"]
    if "keywords" in data:
        articles[article_id]["keywords"] = data["keywords"]
    articles[article_id]["updated"] = datetime.datetime.now().isoformat()
    save_articles(articles)
    return jsonify({"ok": True})

@app.route("/api/articles/<article_id>", methods=["DELETE"])
def delete_article(article_id):
    articles = load_articles()
    if article_id not in articles:
        return jsonify({"error": "not found"}), 404
    del articles[article_id]
    save_articles(articles)
    return jsonify({"ok": True})

@app.route("/api/articles/<article_id>/read", methods=["POST"])
def track_read(article_id):
    articles = load_articles()
    if article_id not in articles:
        return jsonify({"error": "not found"}), 404
    articles[article_id]["reads"] = articles[article_id].get("reads", 0) + 1
    save_articles(articles)
    return jsonify({"reads": articles[article_id]["reads"]})

@app.route("/api/spellcheck", methods=["POST"])
def spellcheck():
    data = request.json
    text = data.get("text", "")
    words = text.split()
    cleaned = [w.strip(".,!?;:\"'()[]{}") for w in words if w.strip(".,!?;:\"'()[]{}")]
    misspelled = spell.unknown(cleaned)
    suggestions = {}
    for word in misspelled:
        sug = spell.correction(word)
        suggestions[word] = sug if sug else None
    return jsonify({"misspelled": list(misspelled), "suggestions": suggestions})

@app.route("/api/analyze", methods=["POST"])
def analyze():
    data = request.json
    text = data.get("text", "")
    return jsonify({
        "stats": word_stats(text),
        "vocab": vocab_analysis(text),
        "structure": sentence_analysis(text),
    })

@app.route("/api/grammar", methods=["POST"])
def grammar():
    data = request.json
    text = data.get("text", "")
    return jsonify({"issues": grammar_check(text)})

@app.route("/api/progress")
def get_progress():
    articles = load_articles()
    items = []
    for aid, a in sorted(articles.items(), key=lambda x: x[1].get("updated", x[1].get("created",""))):
        v = vocab_analysis(a.get("content",""))
        s = sentence_analysis(a.get("content",""))
        wc = len(a.get("content","").strip().split())
        items.append({
            "date": (a.get("updated") or a.get("created",""))[:10],
            "word_count": wc,
            "vocab_score": v["vocab_score"],
            "avg_sentence_len": s["avg_words"],
        })
    return jsonify(items[-20:])

@app.route("/api/keywords")
def get_keywords():
    articles = load_articles()
    keyword_set = set()
    for a in articles.values():
        for kw in a.get("keywords", []):
            keyword_set.add(kw.strip())
    return jsonify(sorted(keyword_set))

@app.route("/api/stats")
def get_stats():
    articles = load_articles()
    total_articles = len(articles)
    total_words = 0
    by_category = {}
    for aid, a in articles.items():
        cat = a.get("category", "general")
        if cat not in by_category:
            by_category[cat] = {"count": 0, "words": 0}
        by_category[cat]["count"] += 1
        wc = len(a.get("content", "").strip().split())
        by_category[cat]["words"] += wc
        total_words += wc

    total_vocab_score = 0
    vocab_count = 0
    from collections import Counter
    all_basic = Counter()
    all_words = Counter()
    for a in articles.values():
        content = a.get("content", "")
        v = vocab_analysis(content)
        if v["total_words"] > 0:
            total_vocab_score += v["vocab_score"]
            vocab_count += 1
        for w in v["basic_words"]:
            all_basic[w] += 1
        for w in re.findall(r'\b[a-zA-Z]+\b', content.lower()):
            all_words[w] += 1

    avg_vocab_score = round(total_vocab_score / vocab_count, 1) if vocab_count else 0
    top_weak_words = [{"word": w, "count": c} for w, c in all_basic.most_common(5)]
    top_common_words = [{"word": w, "count": c} for w, c in all_words.most_common(10)]

    return jsonify({
        "total_articles": total_articles,
        "total_words": total_words,
        "by_category": by_category,
        "avg_vocab_score": avg_vocab_score,
        "top_weak_words": top_weak_words,
        "top_common_words": top_common_words,
    })

# ─── PDF font helpers ────────────────────────────────────────
_WIN_FONTS = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts")

def _setup_pdf_fonts(pdf):
    # Try Windows system fonts first (Arial, Times New Roman)
    wf = lambda name: os.path.join(_WIN_FONTS, name) if os.path.exists(os.path.join(_WIN_FONTS, name)) else None
    sans = wf("arial.ttf")
    bold = wf("arialbd.ttf")
    obli = wf("ariali.ttf")
    serif = wf("times.ttf")
    if all([sans, bold, obli, serif]):
        pdf.add_font("DJV", "", sans, uni=True)
        pdf.add_font("DJV", "B", bold, uni=True)
        pdf.add_font("DJV", "I", obli, uni=True)
        pdf.add_font("DJVS", "", serif, uni=True)
        return True
    # Fallback: try downloading DejaVu fonts
    FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
    _FONT_URLS = {
        "DejaVuSans.ttf": "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf": "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Bold.ttf",
        "DejaVuSans-Oblique.ttf": "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSans-Oblique.ttf",
        "DejaVuSerif.ttf": "https://raw.githubusercontent.com/dejavu-fonts/dejavu-fonts/master/ttf/DejaVuSerif.ttf",
    }
    def _font_path(name):
        p = os.path.join(FONTS_DIR, name)
        if os.path.exists(p):
            return p
        os.makedirs(FONTS_DIR, exist_ok=True)
        url = _FONT_URLS.get(name)
        if url:
            try:
                urllib.request.urlretrieve(url, p)
                return p
            except Exception:
                pass
        return None
    sans = _font_path("DejaVuSans.ttf")
    bold = _font_path("DejaVuSans-Bold.ttf")
    obli = _font_path("DejaVuSans-Oblique.ttf")
    serif = _font_path("DejaVuSerif.ttf")
    if all([sans, bold, obli, serif]):
        pdf.add_font("DJV", "", sans, uni=True)
        pdf.add_font("DJV", "B", bold, uni=True)
        pdf.add_font("DJV", "I", obli, uni=True)
        pdf.add_font("DJVS", "", serif, uni=True)
        return True
    return False

# ─── PDF Export ──────────────────────────────────────────────
@app.route("/api/export-pdf", methods=["GET", "POST"])
def export_pdf():
    articles = load_articles()
    selected_ids = []

    if request.method == "POST":
        data = request.json or {}
        selected_ids = data.get("ids", [])
    else:
        ids_param = request.args.get("ids", "")
        if ids_param:
            selected_ids = [i.strip() for i in ids_param.split(",") if i.strip()]

    if selected_ids:
        filtered_articles = {aid: articles[aid] for aid in selected_ids if aid in articles}
        download_name = "selected_essays.pdf"
    else:
        filtered_articles = articles
        download_name = "all_essays.pdf"

    if not filtered_articles:
        return jsonify({"error": "No essays to export"}), 400

    sorted_articles = sorted(
        filtered_articles.items(),
        key=lambda x: x[1].get("updated", x[1].get("created", "")),
        reverse=True
    )

    total = len(sorted_articles)
    total_wc = sum(len(a.get("content","").strip().split()) for _, a in sorted_articles)
    cats_used = set(a.get("category","general") for _, a in sorted_articles)

    # ── Font & helpers ──
    class _PDF(FPDF):
        def footer(self):
            if self.page_no() > 1:
                self.set_y(-15)
                self.set_font(self._fn, "", 8)
                self.set_text_color(148, 163, 184)
                self.cell(0, 10, self._sf(f"Page {self.page_no() - 1}"), align="C")

    pdf = _PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.set_left_margin(18)
    pdf.set_right_margin(18)
    pw = pdf.w - 36

    fonts_ok = _setup_pdf_fonts(pdf)
    pdf._fn = "DJV" if fonts_ok else "Helvetica"
    pdf._fns = "DJVS" if fonts_ok else "Helvetica"

    def sf(t):
        return t if fonts_ok else t.encode("latin-1","replace").decode("latin-1")
    pdf._sf = sf

    def crgb(k):
        c = CATEGORIES.get(k, {"color":"#6b7280"})
        h = c["color"].lstrip("#")
        return tuple(int(h[i:i+2],16) for i in (0,2,4))

    def clbl(k):
        return CATEGORIES.get(k, {"label":"General"})["label"]

    # ═══════════════════════════════════════════
    #  COVER PAGE
    # ═══════════════════════════════════════════
    pdf.add_page()

    # Simple, elegant top border line in a primary color
    pdf.set_fill_color(99, 102, 241)
    pdf.rect(18, 18, pw, 2, "F")

    # Title Block
    pdf.set_y(55)
    pdf.set_font(pdf._fn, "B", 36)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 16, sf("WRITING PORTFOLIO"), align="C", ln=True)

    pdf.set_font(pdf._fn, "", 14)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(0, 8, sf("IELTS & GRE Essay Collection"), align="C", ln=True)

    # Thin divider line
    pdf.ln(12)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.5)
    pdf.line(40, pdf.get_y(), pdf.w - 40, pdf.get_y())
    pdf.ln(12)

    # Metadata / Subtitle Block
    pdf.set_font(pdf._fn, "I", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, sf("Curated Practice & Analysis Platform"), align="C", ln=True)

    # Stats Container Box
    pdf.set_y(130)
    pdf.set_fill_color(248, 250, 252)
    pdf.set_draw_color(226, 232, 240)
    pdf.set_line_width(0.3)
    box_w = 120
    box_x = (pdf.w - box_w) / 2
    pdf.rect(box_x, pdf.get_y(), box_w, 45, "DF")

    # Stats Content
    pdf.set_xy(box_x, pdf.get_y() + 5)
    pdf.set_font(pdf._fn, "B", 11)
    pdf.set_text_color(71, 85, 105)
    pdf.cell(box_w, 6, sf("PORTFOLIO SUMMARY"), align="C", ln=True)

    pdf.ln(3)
    pdf.set_font(pdf._fn, "", 10)
    pdf.set_text_color(100, 116, 139)

    pdf.set_x(box_x + 10)
    pdf.cell(box_w - 20, 6, sf(f"Total Essays: {total}"), ln=True)

    pdf.set_x(box_x + 10)
    pdf.cell(box_w - 20, 6, sf(f"Total Word Count: {total_wc:,} words"), ln=True)

    pdf.set_x(box_x + 10)
    pdf.cell(box_w - 20, 6, sf(f"Categories Covered: {len(cats_used)}"), ln=True)

    # Date
    pdf.set_y(250)
    pdf.set_font(pdf._fn, "", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 5, sf(f"Document generated on {datetime.datetime.now().strftime('%B %d, %Y')}"), align="C")

    # ═══════════════════════════════════════════
    #  ESSAY PAGES
    # ═══════════════════════════════════════════
    for idx, (aid, article) in enumerate(sorted_articles):
        pdf.add_page()
        cat = article.get("category", "general")
        r, g, b = crgb(cat)
        title = article.get("title", "")
        subtitle = article.get("subtitle", "")
        content = article.get("content", "")
        wc = len(content.strip().split()) if content.strip() else 0
        updated = article.get("updated", article.get("created", ""))[:10]

        # ── Elegant Header ──
        pdf.set_y(22)
        pdf.set_font(pdf._fn, "B", 18)
        pdf.set_text_color(30, 41, 59)
        pdf.multi_cell(pw, 7.5, sf(title))

        pdf.ln(2)

        # Meta info row
        pdf.set_font(pdf._fn, "", 9.5)
        pdf.set_text_color(100, 116, 139)
        lbl = clbl(cat)
        meta_str = f"Category: {lbl}   |   {wc} Words   |   Updated: {updated}   |   Essay {idx+1} of {total}"
        pdf.cell(0, 5, sf(meta_str), ln=True)

        # Thin divider line under header
        pdf.ln(3)
        pdf.set_draw_color(226, 232, 240)
        pdf.set_line_width(0.3)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(5)

        # ── Callout Box for Subtitle / Question ──
        if subtitle:
            q_y0 = pdf.get_y()

            # Set font to calculate height
            pdf.set_font(pdf._fn, "I", 10.5)
            pdf.set_xy(24, q_y0 + 4)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(pw - 10, 5.5, sf(subtitle))
            q_h = pdf.get_y() - q_y0 + 4

            # Draw background and left accent border
            pdf.set_fill_color(248, 250, 252)
            pdf.set_draw_color(r, g, b)
            pdf.set_line_width(0.8)

            pdf.rect(18, q_y0, pw, q_h, "F")
            pdf.line(18, q_y0, 18, q_y0 + q_h)

            # Re-draw text
            pdf.set_xy(23, q_y0 + 4)
            pdf.set_font(pdf._fn, "I", 10.5)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(pw - 10, 5.5, sf(subtitle))
            pdf.ln(6)

        # ── Content Paragraphs ──
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        pdf.set_font(pdf._fns if fonts_ok else pdf._fn, "", 12.5)
        pdf.set_text_color(30, 41, 59)
        for para in paragraphs:
            pdf.multi_cell(0, 7.2, sf(para))
            pdf.ln(3.5)

        # ── Article Footer ──
        pdf.ln(4)
        pdf.set_draw_color(241, 245, 249)
        pdf.set_line_width(0.3)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
        pdf.set_font(pdf._fn, "I", 9)
        pdf.set_text_color(148, 163, 184)
        pdf.cell(0, 5, sf(f"End of Essay  |  Total Words: {wc}  |  Platform: C_iumNotebook"), align="C")

    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name=download_name)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)

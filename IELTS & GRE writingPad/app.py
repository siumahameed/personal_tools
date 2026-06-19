import json, os, datetime, re
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
    "ielts_t1_ac":  {"label": "IELTS Academic Task 1", "target": 150,  "color": "#6366f1"},
    "ielts_t2":     {"label": "IELTS Academic Task 2", "target": 250,  "color": "#8b5cf6"},
    "gre_issue":    {"label": "GRE Issue Task",        "target": 500,  "color": "#ec4899"},
    "general":      {"label": "General Practice",      "target": 0,    "color": "#6b7280"},
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
    return {
        "total_words": len(words),
        "unique_words": len(unique_words),
        "basic_words": sorted(basic),
        "basic_count": basic_count,
        "advanced_count": advanced_count,
        "vocab_score": round((advanced_count / len(words)) * 100, 1) if len(words) else 0,
    }

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/config")
def get_config():
    return jsonify({"categories": CATEGORIES})

@app.route("/api/articles", methods=["GET"])
def get_articles():
    articles = load_articles()
    items = []
    for key, val in articles.items():
        stats = word_stats(val.get("content", ""))
        items.append({
            "id": key,
            "title": val["title"],
            "subtitle": val.get("subtitle", ""),
            "content": val.get("content", ""),
            "category": val.get("category", "general"),
            "updated": val.get("updated", val.get("created", "")),
            "word_count": stats["word_count"],
        })
    items.sort(key=lambda x: x["updated"], reverse=True)
    return jsonify(items)

@app.route("/api/articles/<article_id>", methods=["GET"])
def get_article(article_id):
    articles = load_articles()
    if article_id not in articles:
        return jsonify({"error": "not found"}), 404
    a = articles[article_id]
    result = dict(a)
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
    })

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
    return jsonify({
        "total_articles": total_articles,
        "total_words": total_words,
        "by_category": by_category,
    })

@app.route("/api/export-pdf", methods=["GET"])
def export_pdf():
    articles = load_articles()
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    arial_path = r"C:\Windows\Fonts\arial.ttf"
    arial_bd_path = r"C:\Windows\Fonts\arialbd.ttf"
    pdf.add_font("Arial", "", arial_path, uni=True)
    pdf.add_font("Arial", "B", arial_bd_path, uni=True)
    for aid, article in articles.items():
        pdf.add_page()
        cat = article.get("category", "general")
        cat_label = CATEGORIES.get(cat, {}).get("label", "General")
        pdf.set_font("Arial", "B", 16)
        pdf.multi_cell(0, 8, article["title"])
        if article.get("subtitle"):
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 6, article["subtitle"])
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, cat_label, align="R")
        pdf.ln(6)
        pdf.set_font("Arial", "", 11)
        content = article.get("content", "")
        for line in content.split("\n"):
            pdf.multi_cell(0, 6, line if line.strip() else " ")
        pdf.ln(4)
        word_count = len(content.strip().split()) if content.strip() else 0
        pdf.set_font("Arial", "", 9)
        pdf.cell(0, 6, f"Words: {word_count}  |  Last updated: {article.get('updated', article.get('created', ''))[:10]}", align="R")
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True, download_name="all_articles.pdf")

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=False)

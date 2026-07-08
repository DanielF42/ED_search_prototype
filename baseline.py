import webview
from course_definition import course
from pathlib import Path
import base64
import threading


def img_b64(path):
    p = Path(path)
    data = base64.b64encode(p.read_bytes()).decode("utf-8")
    ext = p.suffix.replace(".", "")
    return f"data:image/{ext};base64,{data}"

ICON_MAP = {
    "video": "images/video.png",
    "lesson": "images/lesson.png",
    "reading": "images/reading.png",
    "reflection": "images/reflection.png",
    "course": "images/course.png"
}

# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------

search_query = ""
search_mode = "title"

# ---------------------------------------------------------------------
# SEARCH LOGIC
# ---------------------------------------------------------------------

def node_matches(node, query, mode):

    # Only lesson nodes participate
    if not node.get("children"):
        return False

    return query.lower() in node.get("title", "").lower()


def mark_matches(node, query, mode):
    node["_match"] = False
    node["_subtree_match"] = False

    if query == "":
        node["_match"] = False
        node["_subtree_match"] = True
    else:
        node["_match"] = node_matches(node, query, mode)

    subtree_match = node["_match"]

    for child in node.get("children", []):
        mark_matches(child, query, mode)
        subtree_match = subtree_match or child["_subtree_match"]

    node["_subtree_match"] = subtree_match


def first_matching_sentence(transcript, query):
    if not transcript:
        return ""

    sentences = transcript.split(". ")
    query = query.lower()

    for s in sentences:
        if query in s.lower():
            return s.strip()

    return ""

def matching_sentences(transcript, query):
    if not transcript:
        return []

    sentences = transcript.split(". ")
    query = query.lower()

    matches = []

    for s in sentences:
        if query in s.lower():
            matches.append(s.strip())

    return matches

def find_node(nodes, node_id):
    for node in nodes:
        if node["id"] == node_id:
            return node

        result = find_node(node.get("children", []), node_id)
        if result:
            return result

    return None
# ---------------------------------------------------------------------
# TOGGLE LOGIC
# ---------------------------------------------------------------------

def toggle(nodes, node_id):
    for node in nodes:
        if node["id"] == node_id:
            node["expanded"] = not node["expanded"]
            return True
        if toggle(node.get("children", []), node_id):
            return True
    return False


# ---------------------------------------------------------------------
# RENDERING
# ---------------------------------------------------------------------

def highlight(text, query):
    if not query:
        return text
    return text.replace(query, f"<span class='hl'>{query}</span>")


def render_node(node, depth=0, query="", mode="title"):

    # -----------------------------
    # SEARCH FILTER
    # -----------------------------
    if query and not node.get("_subtree_match", True):
        return ""

    # -----------------------------
    # EXPANSION RULE (FIXED)
    # -----------------------------
    if search_query:
        expanded = node.get("_subtree_match", False)
    else:
        expanded = node.get("expanded", False)

    has_children = bool(node.get("children"))

    arrow = "▼" if has_children and expanded else ("▶" if has_children else "")
    check = "✓" if node.get("complete") else ""

    has_transcript = bool(node.get("transcript"))

    # -----------------------------
    # TITLE + PREVIEW
    # -----------------------------
    title = highlight(node.get("title", ""), search_query)

    preview_lines = []
    if mode == "transcript" and search_query:
        preview_lines = matching_sentences(
            node.get("transcript", ""),
            search_query
        )

    # -----------------------------
    # MAIN ROW (FIXED STRUCTURE)
    # -----------------------------
    icon = ICON_MAP.get(node.get("icon", "default"))
    icon_html = f'<img class="node-icon" src="{img_b64(icon)}">'

    click = ""

    if has_transcript:
        click = f'onclick="openTranscript({node["id"]})"'

    html = f"""
    <div class="row" style="padding-left:{depth * 22}px"{click}>
        
        
        {icon_html}

        <div class="check">{check}</div>

        <div class="content">
            <div class="title">{title}
        </div>

        <div class="arrow" onclick="event.stopPropagation(); toggleNode({node['id']})">
            {arrow}
        </div>
    """

    if preview_lines:
        html += "<div class='preview'>"

        for line in preview_lines:
            html += f"<div class='preview-line'>{line}</div>"

        html += "</div>"

    html += """
        </div>
    </div>
    """

    # -----------------------------
    # CHILDREN (FIXED WRAPPING)
    # -----------------------------
    if expanded:
        children_html = ""

        for child in node.get("children", []):
            children_html += render_node(child, depth + 1, query, mode)

        if children_html.strip():
            html += f"<div class='children'>{children_html}</div>"

    return html


def render_tree():
    mark_matches(course, search_query, search_mode)
    return "".join(render_node(n, 0, search_query, search_mode) for n in course["children"])


# ---------------------------------------------------------------------
# API
# ---------------------------------------------------------------------

class Api:

    def toggle_node(self, node_id):
        toggle(course["children"], node_id)
        return render_tree()

    def set_search(self, query):
        global search_query
        search_query = query
        return render_tree()

    def set_search_mode(self, mode):
        global search_mode
        search_mode = mode
        return render_tree()

    def open_transcript(self, node_id):

        def run():
            node = find_node(course["children"], node_id)

            if not node:
                return

            html = f"""
<html>
<head>
<style>

body {{
    font-family: Segoe UI;
    padding: 20px;
    margin: 0;
    line-height: 1.5;
}}

.transcript {{
    white-space: pre-wrap;   /* preserves line breaks */
    word-wrap: break-word;   /* breaks long words */
    overflow-wrap: break-word;
}}

</style>
</head>

<body>

<h2>{node['title']}</h2>

<div class="transcript">
{node.get('transcript','')}
</div>

</body>
</html>
"""

            webview.create_window(
                node["title"],
                html=html,
                width=800,
                height=600
            )

        threading.Thread(target=run, daemon=True).start()

api = Api()


# ---------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------

ED_LOGO = img_b64("images/ed_logo.png")
GT_LOGO = img_b64("images/gt_logo.png")
TOOLBAR_ICON = img_b64("images/toolbar_top_right.png")

html = f"""
<!DOCTYPE html>
<html>
<head>

<style>

body {{
    margin:0;
    font-family:Segoe UI, Arial;
}}

.container {{
    width: 5in;
    margin: 0 auto;
}}

.children {{
    margin-left: 12px;
    padding-left: 10px;
}}

.header {{
    text-align:center;
    font-size:26px;
    padding:20px;
    border-bottom:1px solid #ddd;
}}

.toolbar {{
    display:flex;
    justify-content:center;
    padding:12px;
    border-bottom:1px solid #eee;
}}

.search {{
    width:320px;
    height:32px;
    border-radius:16px;
    border:1px solid #ccc;
    padding-left:12px;
    outline:none;
}}

.row {{
    display: flex;
    align-items: center;
    min-height: 38px;
    height: auto;
    padding: 4px 0;
    border-bottom: 1px solid #f0f0f0;
}}

.arrow {{
    display: flex;
    margin-left: auto;
    width: 22px;
    text-align: right;
    cursor: pointer;
    color: #666;
    flex-shrink: 0;
}}

.icon {{
    width:16px;
    height:16px;
    background:#4fc3f7;
    border-radius:3px;
    margin-right:10px;
    flex-shrink: 0;
}}

.node-icon {{
    width: 25px;
    height: 25px;
    object-fit: contain;
}}

.check {{
    display: flex;
    width:22px;
    color:green;
    font-weight:bold;
}}

.content {{
    display:flex;
    flex-direction:column;
    flex: 1;
}}

.title {{
    font-size:15px;
}}

.hl {{
    background: yellow;
    font-weight: bold;
}}

.preview {{
    margin-top: 2px;
}}

.preview-line {{
    font-size: 12px;
    color: #666;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding: 1px 0;
}}

.topbar {{

    position: fixed;

    top: 0;
    left: 0;
    right: 0;

    height: 48px;

    background: #512A89;

    display: flex;
    justify-content: space-between;
    align-items: center;

    padding: 0 14px;

    box-sizing: border-box;

    z-index: 1000;
}}

.topbar-left,
.topbar-right {{

    display: flex;
    align-items: center;
}}

.logo {{

    height: 30px;
    margin-right: 14px;
}}

.gt-logo {{

    height: 35px;
    margin-right: 14px;
}}

.divider {{

    width: 1px;
    height: 26px;

    background: rgba(255,255,255,.35);

    margin-right: 16px;
}}

.course-title {{

    color: white;
    font-size: 18px;
    font-weight: 500;
}}

.toolbar-icon {{

    width: 200px;
    height: 35px;

    margin-left: 18px;

    cursor: pointer;
}}

.avatar {{

    width: 34px;
    height: 34px;

    margin-left: 18px;
}}

.page{{
    margin-top:48px;
    height:calc(100vh - 48px);
    overflow-y:auto;
}}


</style>

</head>

<body>

<div class="topbar">

    <div class="topbar-left">

        <img class="logo" src="{ED_LOGO}">

        <img class="gt-logo" src="{GT_LOGO}">

        <div class="divider"></div>

        <span class="course-title">
            CS6750 – Ed Lessons
        </span>

    </div>

    <div class="topbar-right">

        <img class="toolbar-icon" src="{TOOLBAR_ICON}">

    </div>

</div>


<div class="page">

    <div class="header">Lessons</div>

    <div class="toolbar">

        <input class="search"
            placeholder="Search..."
            oninput="runSearch(this.value)">

        <label style="margin-left:10px;">
            <input type="radio" name="mode" value="title"
                checked onchange="setMode(this.value)">
            Title
        </label>

        <label style="margin-left:10px;">
            <input type="radio" name="mode" value="transcript"
                onchange="setMode(this.value)">
            Transcript
        </label>

    </div>

    <div class="container">
        <div id="tree">
"""

html += render_tree()

html += """
    </div>
</div>

<script>

async function renderInitial() {
    const html = await pywebview.api.set_search("");
    document.getElementById("tree").innerHTML = html;
}

async function toggleNode(id) {
    const html = await pywebview.api.toggle_node(id);
    document.getElementById("tree").innerHTML = html;
}

async function runSearch(query) {
    const html = await pywebview.api.set_search(query);
    document.getElementById("tree").innerHTML = html;
}

async function setMode(mode) {
    const html = await pywebview.api.set_search_mode(mode);
    document.getElementById("tree").innerHTML = html;
}

async function openTranscript(id) {
    await pywebview.api.open_transcript(id);
}

</script>

</body>
</html>
"""


# ---------------------------------------------------------------------
# RUN APP
# ---------------------------------------------------------------------

webview.create_window(
    "CS6750",
    html=html,
    js_api=api,
    width=850,
    height=750,
    easy_drag=False
)

webview.start()
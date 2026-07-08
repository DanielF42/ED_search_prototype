import webview
from course_definition import course
from pathlib import Path
import base64

# ---------------------------------------------------------------------
# IMAGE ENCODING
# ---------------------------------------------------------------------

def img_b64(path):
    p = Path(path)
    data = base64.b64encode(p.read_bytes()).decode("utf-8")
    ext = p.suffix.replace(".", "")
    return f"data:image/{ext};base64,{data}"

# ---------------------------------------------------------------------
# STATE
# ---------------------------------------------------------------------

search_query = ""
search_mode = "title"

# ---------------------------------------------------------------------
# SEARCH LOGIC
# ---------------------------------------------------------------------

def node_matches(node, query, mode):
    text = ""

    if mode == "title":
        text = node.get("title", "")

    elif mode == "transcript":
        text = node.get("transcript", "") or node.get("title", "")

    return query.lower() in text.lower()


def mark_matches(node, query, mode):
    node["_match"] = False
    node["_subtree_match"] = False

    if query == "":
        node["_subtree_match"] = True
    else:
        node["_match"] = node_matches(node, query, mode)

    subtree_match = node["_match"]

    for child in node.get("children", []):
        mark_matches(child, query, mode)
        subtree_match = subtree_match or child["_subtree_match"]

    node["_subtree_match"] = subtree_match


def matching_sentences(transcript, query):
    if not transcript:
        return []

    sentences = transcript.split(". ")
    query = query.lower()

    return [s.strip() for s in sentences if query in s.lower()]


# ---------------------------------------------------------------------
# TOGGLE LOGIC
# ---------------------------------------------------------------------

def toggle(nodes, node_id):
    for node in nodes:
        if node["id"] == node_id:
            node["expanded"] = not node.get("expanded", False)
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

    if query and not node.get("_subtree_match", True):
        return ""

    # EXPANSION RULE
    if search_query:
        expanded = node.get("_subtree_match", False)
    else:
        expanded = node.get("expanded", False)

    has_children = bool(node.get("children"))

    arrow = "▼" if has_children and expanded else ("▶" if has_children else "")
    check = "✓" if node.get("complete") else ""

    title = highlight(node.get("title", ""), search_query)

    # ICON (safe fallback)
    icon_path = node.get("icon")
    icon_html = (
        f'<img class="icon" src="{img_b64(icon_path)}">'
        if icon_path else
        '<div class="icon"></div>'
    )

    preview_lines = []
    if mode == "transcript" and search_query:
        preview_lines = matching_sentences(
            node.get("transcript", ""),
            search_query
        )

    html = f"""
    <div class="row" style="padding-left:{depth * 22}px">

        {icon_html}

        <div class="check">{check}</div>

        <div class="content">
            <div class="title">{title}</div>
    """

    if preview_lines:
        html += "<div class='preview'>"
        for line in preview_lines:
            html += f"<div class='preview-line'>{line}</div>"
        html += "</div>"

    html += f"""
        </div>

        <div class="arrow" onclick="toggleNode({node['id']})">
            {arrow}
        </div>

    </div>
    """

    if expanded:
        children_html = ""
        for child in node.get("children", []):
            children_html += render_node(child, depth + 1, query, mode)

        if children_html:
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

.row {{
    display:flex;
    align-items:center;
    padding:4px 0;
    border-bottom:1px solid #f0f0f0;
}}

.icon {{
    width:18px;
    height:18px;
    margin-right:10px;
    background:#4fc3f7;
    border-radius:3px;
    flex-shrink:0;
}}

.check {{
    width:20px;
    color:green;
    font-weight:bold;
}}

.content {{
    flex:1;
    display:flex;
    flex-direction:column;
}}

.title {{
    font-size:15px;
}}

.arrow {{
    margin-left:auto;
    cursor:pointer;
    width:22px;
}}

.hl {{
    background: yellow;
    font-weight: bold;
}}

.preview-line {{
    font-size:12px;
    color:#666;
}}

.topbar {{
    position:fixed;
    top:0;
    left:0;
    right:0;
    height:48px;
    background:#512A89;
    display:flex;
    justify-content:space-between;
    align-items:center;
    padding:0 14px;
    z-index:1000;
}}

.page {{
    margin-top:48px;
    height:calc(100vh - 48px);
    overflow-y:auto;
}}

</style>
</head>

<body>

<div class="topbar"></div>

<div class="page">

<div class="container">

<div id="tree"></div>

</div>
</div>

<script>

async function renderInitial() {{
    const html = await pywebview.api.set_search("");
    document.getElementById("tree").innerHTML = html;
}}

async function toggleNode(id) {{
    const html = await pywebview.api.toggle_node(id);
    document.getElementById("tree").innerHTML = html;
}}

async function runSearch(q) {{
    const html = await pywebview.api.set_search(q);
    document.getElementById("tree").innerHTML = html;
}}

async function setMode(m) {{
    const html = await pywebview.api.set_search_mode(m);
    document.getElementById("tree").innerHTML = html;
}}

renderInitial();

</script>

</body>
</html>
"""

# ---------------------------------------------------------------------
# RUN
# ---------------------------------------------------------------------

webview.create_window(
    "CS6750",
    html=html,
    js_api=api,
    width=850,
    height=750
)

webview.start()
import ast
import html
import json
import os
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import URLPattern, URLResolver, get_resolver


# ============================================================
# AYARLAR
# ============================================================

IGNORE_DIRS = {
    ".git",
    ".idea",
    ".vscode",
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "static",
    "media",
}

TEMPLATE_EXTENSIONS = {".html", ".htm"}

# Django template içindeki:
# {% url 'athlete-detail' athlete.pk %}
URL_TAG_RE = re.compile(
    r"""{%\s*url\s+['"]([^'"]+)['"][^%]*%}""",
    re.MULTILINE,
)

# hx-get="{% url 'xxx' ... %}"
HTMX_URL_RE = re.compile(
    r"""hx-(?:get|post|put|patch|delete)\s*=\s*["']\s*{%\s*url\s+['"]([^'"]+)['"][^%]*%}\s*["']""",
    re.IGNORECASE | re.MULTILINE,
)

# hx-get="/some/path/"
HTMX_LITERAL_RE = re.compile(
    r"""hx-(?:get|post|put|patch|delete)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
)

# {% include "..." %}
INCLUDE_RE = re.compile(
    r"""{%\s*include\s+['"]([^'"]+)['"][^%]*%}""",
    re.MULTILINE,
)

# {% extends "..." %}
EXTENDS_RE = re.compile(
    r"""{%\s*extends\s+['"]([^'"]+)['"]\s*%}""",
    re.MULTILINE,
)


# ============================================================
# COMMAND
# ============================================================

class Command(BaseCommand):
    help = (
        "Django projesindeki URL → View → Template → "
        "Partial → HTMX ilişkilerini interaktif HTML haritası olarak çıkarır."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="project-map.html",
            help="Oluşturulacak HTML dosyasının adı.",
        )

    def handle(self, *args, **options):
        output = Path(options["output"]).resolve()

        self.stdout.write("")
        self.stdout.write(
            self.style.MIGRATE_HEADING(
                "Django Project Map oluşturuluyor..."
            )
        )
        self.stdout.write("")

        project_root = self.get_project_root()

        self.stdout.write(
            f"Proje dizini: {project_root}"
        )

        # ----------------------------------------------------
        # 1. URL'LER
        # ----------------------------------------------------

        self.stdout.write("URL'ler taranıyor...")

        routes = self.collect_urls()

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {len(routes)} URL bulundu."
            )
        )

        # ----------------------------------------------------
        # 2. TEMPLATE'LER
        # ----------------------------------------------------

        self.stdout.write("Template'ler taranıyor...")

        templates = self.collect_templates(project_root)

        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ {len(templates)} template bulundu."
            )
        )

        # ----------------------------------------------------
        # 3. VIEW → TEMPLATE ANALİZİ
        # ----------------------------------------------------

        self.stdout.write("View → Template ilişkileri analiz ediliyor...")

        view_template_map = self.analyze_views(project_root)

        # ----------------------------------------------------
        # 4. TEMPLATE → INCLUDE / URL / HTMX
        # ----------------------------------------------------

        self.stdout.write(
            "Template → Include / URL / HTMX ilişkileri analiz ediliyor..."
        )

        template_relations = self.analyze_templates(
            templates,
            routes,
        )

        # ----------------------------------------------------
        # 5. GRAPH OLUŞTUR
        # ----------------------------------------------------

        graph = self.build_graph(
            routes=routes,
            view_template_map=view_template_map,
            template_relations=template_relations,
        )

        # ----------------------------------------------------
        # 6. HTML
        # ----------------------------------------------------

        html_content = self.render_html(
            graph=graph,
            routes=routes,
            templates=templates,
            view_template_map=view_template_map,
        )

        output.write_text(
            html_content,
            encoding="utf-8",
        )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Project map oluşturuldu:"
            )
        )
        self.stdout.write(
            f"  {output}"
        )
        self.stdout.write("")

        self.stdout.write(
            "Tarayıcıda bu dosyayı açabilirsin."
        )
        self.stdout.write("")


    # ========================================================
    # PROJECT ROOT
    # ========================================================

    def get_project_root(self):
        """
        settings.BASE_DIR üzerinden proje kökünü bulur.
        """

        base_dir = Path(settings.BASE_DIR)

        if base_dir.exists():
            return base_dir.resolve()

        return Path.cwd().resolve()


    # ========================================================
    # URL TOPLAMA
    # ========================================================

    def collect_urls(self):
        """
        Django'nun gerçek URL resolver'ını kullanır.

        Sonuç:

        [
            {
                "pattern": "/athletes/",
                "name": "athlete-list",
                "view": "...",
                "view_class": "...",
                "type": "class",
                "module": "...",
            }
        ]
        """

        resolver = get_resolver()

        routes = []

        self.walk_urlpatterns(
            resolver.url_patterns,
            prefix="",
            routes=routes,
        )

        return routes


    def walk_urlpatterns(
        self,
        urlpatterns,
        prefix,
        routes,
    ):
        for pattern in urlpatterns:

            if isinstance(pattern, URLResolver):

                current_prefix = (
                    prefix
                    + str(pattern.pattern)
                )

                self.walk_urlpatterns(
                    pattern.url_patterns,
                    current_prefix,
                    routes,
                )

                continue

            if not isinstance(pattern, URLPattern):
                continue

            route = self.clean_route(
                prefix + str(pattern.pattern)
            )

            callback = pattern.callback

            route_name = pattern.name or ""

            view_info = self.describe_callback(callback)

            routes.append(
                {
                    "pattern": route,
                    "name": route_name,
                    **view_info,
                }
            )


    def clean_route(self, route):
        route = route.replace("^", "")
        route = route.replace("$", "")

        if route == "":
            return "/"

        if not route.startswith("/"):
            route = "/" + route

        return route


    # ========================================================
    # VIEW ANALİZİ
    # ========================================================

    def describe_callback(self, callback):
        """
        CBV ve FBV ayrımını yapar.
        """

        result = {
            "view": "",
            "view_class": "",
            "view_type": "unknown",
            "module": "",
            "file": "",
        }

        # ----------------------------------------------------
        # CBV
        # ----------------------------------------------------

        view_class = getattr(
            callback,
            "view_class",
            None,
        )

        if view_class:

            result["view_type"] = "class"

            result["view_class"] = (
                f"{view_class.__module__}."
                f"{view_class.__name__}"
            )

            result["view"] = view_class.__name__

            result["module"] = view_class.__module__

            try:
                result["file"] = str(
                    Path(
                        __import__(
                            view_class.__module__,
                            fromlist=["dummy"],
                        ).__file__
                    ).resolve()
                )
            except Exception:
                pass

            return result

        # ----------------------------------------------------
        # FBV
        # ----------------------------------------------------

        func = callback

        result["view_type"] = "function"

        result["view"] = getattr(
            func,
            "__name__",
            str(func),
        )

        module = getattr(
            func,
            "__module__",
            "",
        )

        result["module"] = module

        if module:

            result["view"] = (
                f"{module}.{result['view']}"
            )

            try:
                result["file"] = str(
                    Path(
                        __import__(
                            module,
                            fromlist=["dummy"],
                        ).__file__
                    ).resolve()
                )
            except Exception:
                pass

        return result


    # ========================================================
    # TEMPLATE DOSYALARINI BUL
    # ========================================================

    def collect_templates(self, project_root):

        templates = {}

        for root, dirs, files in os.walk(project_root):

            # Gereksiz klasörleri çıkar
            dirs[:] = [
                d
                for d in dirs
                if d not in IGNORE_DIRS
            ]

            for filename in files:

                path = Path(root) / filename

                if path.suffix.lower() not in TEMPLATE_EXTENSIONS:
                    continue

                try:
                    relative = path.relative_to(
                        project_root
                    )
                except ValueError:
                    continue

                relative_string = str(
                    relative
                ).replace("\\", "/")

                templates[relative_string] = {
                    "path": str(path),
                    "relative": relative_string,
                }

                # templates/ klasörü içinden itibaren
                # template adını ayrıca kaydet
                parts = list(relative.parts)

                if "templates" in parts:

                    index = parts.index("templates")

                    template_name = "/".join(
                        parts[index + 1:]
                    )

                    if template_name:
                        templates.setdefault(
                            template_name,
                            {
                                "path": str(path),
                                "relative": relative_string,
                            },
                        )

        return templates


    # ========================================================
    # VIEW SOURCE ANALİZİ
    # ========================================================

    def analyze_views(self, project_root):

        result = {}

        python_files = []

        for root, dirs, files in os.walk(project_root):

            dirs[:] = [
                d
                for d in dirs
                if d not in IGNORE_DIRS
            ]

            for filename in files:

                if not filename.endswith(".py"):
                    continue

                if filename in {
                    "manage.py",
                }:
                    continue

                python_files.append(
                    Path(root) / filename
                )

        for path in python_files:

            try:
                source = path.read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue

            analyzer = ViewASTAnalyzer()

            analyzer.visit(tree)

            for view_name, templates in analyzer.views.items():

                result[view_name] = {
                    "templates": sorted(
                        templates
                    ),
                    "file": str(path),
                }

        return result


    # ========================================================
    # TEMPLATE ANALİZİ
    # ========================================================

    def analyze_templates(
        self,
        templates,
        routes,
    ):

        route_names = {
            route["name"]
            for route in routes
            if route.get("name")
        }

        result = {}

        # Sadece gerçek template path'lerini analiz et
        seen_paths = set()

        for template_name, info in templates.items():

            path = info["path"]

            if path in seen_paths:
                continue

            seen_paths.add(path)

            try:
                source = Path(path).read_text(
                    encoding="utf-8"
                )
            except Exception:
                continue

            includes = sorted(
                set(
                    INCLUDE_RE.findall(
                        source
                    )
                )
            )

            extends = sorted(
                set(
                    EXTENDS_RE.findall(
                        source
                    )
                )
            )

            urls = sorted(
                set(
                    URL_TAG_RE.findall(
                        source
                    )
                )
            )

            htmx_url_names = sorted(
                set(
                    HTMX_URL_RE.findall(
                        source
                    )
                )
            )

            literal_htmx = sorted(
                set(
                    HTMX_LITERAL_RE.findall(
                        source
                    )
                )
            )

            result[template_name] = {
                "path": path,
                "includes": includes,
                "extends": extends,
                "urls": [
                    x for x in urls
                    if x in route_names
                ],
                "htmx_urls": [
                    x for x in htmx_url_names
                    if x in route_names
                ],
                "literal_htmx": literal_htmx,
            }

        return result


    # ========================================================
    # GRAPH
    # ========================================================

    def build_graph(
        self,
        routes,
        view_template_map,
        template_relations,
    ):

        nodes = []
        links = []

        node_ids = set()

        def add_node(
            node_id,
            label,
            node_type,
            details=None,
        ):

            if node_id in node_ids:
                return

            node_ids.add(node_id)

            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "details": details or {},
                }
            )


        def add_link(
            source,
            target,
            relation,
        ):

            links.append(
                {
                    "source": source,
                    "target": target,
                    "relation": relation,
                }
            )


        # ----------------------------------------------------
        # URL → VIEW → TEMPLATE
        # ----------------------------------------------------

        for route in routes:

            url_id = (
                "url:"
                + route["pattern"]
                + ":"
                + route["name"]
            )

            view_id = (
                "view:"
                + (
                    route["view_class"]
                    or route["view"]
                )
            )

            add_node(
                url_id,
                route["pattern"],
                "url",
                route,
            )

            add_node(
                view_id,
                route["view_class"]
                or route["view"],
                "view",
                route,
            )

            add_link(
                url_id,
                view_id,
                "URL → VIEW",
            )

            # ------------------------------------------------
            # VIEW TEMPLATE
            # ------------------------------------------------

            possible_view_names = {
                route["view"],
                route["view_class"],
                route["view"].split(".")[-1]
                if route["view"]
                else "",
                route["view_class"].split(".")[-1]
                if route["view_class"]
                else "",
            }

            matched_templates = set()

            for view_name in possible_view_names:

                if not view_name:
                    continue

                data = view_template_map.get(
                    view_name
                )

                if data:
                    matched_templates.update(
                        data["templates"]
                    )

            for template in matched_templates:

                template_id = (
                    "template:"
                    + template
                )

                add_node(
                    template_id,
                    template,
                    "template",
                    {
                        "template": template,
                    },
                )

                add_link(
                    view_id,
                    template_id,
                    "VIEW → TEMPLATE",
                )


        # ----------------------------------------------------
        # TEMPLATE RELATIONS
        # ----------------------------------------------------

        for template_name, data in template_relations.items():

            template_id = (
                "template:"
                + template_name
            )

            # Template node olmayabilir.
            # Yine de oluştur.
            add_node(
                template_id,
                template_name,
                "template",
                data,
            )

            # INCLUDE
            for include in data["includes"]:

                include_id = (
                    "template:"
                    + include
                )

                add_node(
                    include_id,
                    include,
                    "partial",
                    {
                        "template": include,
                    },
                )

                add_link(
                    template_id,
                    include_id,
                    "INCLUDE",
                )

            # EXTENDS
            for parent in data["extends"]:

                parent_id = (
                    "template:"
                    + parent
                )

                add_node(
                    parent_id,
                    parent,
                    "template",
                    {
                        "template": parent,
                    },
                )

                add_link(
                    template_id,
                    parent_id,
                    "EXTENDS",
                )

            # TEMPLATE URL
            for url_name in data["urls"]:

                matching_routes = [
                    r
                    for r in routes
                    if r["name"] == url_name
                ]

                for route in matching_routes:

                    url_id = (
                        "url:"
                        + route["pattern"]
                        + ":"
                        + route["name"]
                    )

                    add_node(
                        url_id,
                        route["pattern"],
                        "url",
                        route,
                    )

                    relation = "HTMX → URL" if (
                        url_name
                        in data["htmx_urls"]
                    ) else "TEMPLATE → URL"

                    add_link(
                        template_id,
                        url_id,
                        relation,
                    )

        return {
            "nodes": nodes,
            "links": links,
        }


    # ========================================================
    # HTML
    # ========================================================

    def render_html(
        self,
        graph,
        routes,
        templates,
        view_template_map,
    ):

        graph_json = json.dumps(
            graph,
            ensure_ascii=False,
        )

        route_count = len(routes)

        view_count = len({
            r.get("view_class") or r.get("view")
            for r in routes
            if r.get("view_class") or r.get("view")
        })

        template_count = len(templates)

        return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">

<meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
>

<title>Django Project Map</title>

<style>

* {{
    box-sizing: border-box;
}}

html,
body {{
    margin: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family:
        Inter,
        ui-sans-serif,
        system-ui,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        sans-serif;
    background: #f5f7fb;
    color: #172033;
}}

button,
input {{
    font: inherit;
}}

.app {{
    display: flex;
    width: 100%;
    height: 100%;
}}

.sidebar {{
    width: 330px;
    min-width: 330px;
    height: 100%;
    background: #ffffff;
    border-right: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
    z-index: 10;
}}

.header {{
    padding: 20px;
    border-bottom: 1px solid #e5e7eb;
}}

.title {{
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 5px;
}}

.subtitle {{
    font-size: 12px;
    color: #6b7280;
}}

.stats {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 16px;
}}

.stat {{
    padding: 10px;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    background: #fafafa;
}}

.stat strong {{
    display: block;
    font-size: 18px;
}}

.stat span {{
    font-size: 10px;
    color: #6b7280;
}}

.search {{
    padding: 12px;
    border-bottom: 1px solid #e5e7eb;
}}

.search input {{
    width: 100%;
    border: 1px solid #d1d5db;
    border-radius: 9px;
    padding: 9px 11px;
    outline: none;
}}

.search input:focus {{
    border-color: #6366f1;
}}

.filters {{
    display: flex;
    gap: 6px;
    padding: 10px 12px;
    border-bottom: 1px solid #e5e7eb;
    flex-wrap: wrap;
}}

.filter {{
    border: 1px solid #d1d5db;
    background: white;
    border-radius: 7px;
    padding: 5px 8px;
    font-size: 11px;
    cursor: pointer;
}}

.filter.active {{
    background: #111827;
    color: white;
    border-color: #111827;
}}

.routes {{
    flex: 1;
    overflow-y: auto;
    padding: 8px;
}}

.route-item {{
    padding: 9px 10px;
    border-radius: 8px;
    cursor: pointer;
    margin-bottom: 3px;
}}

.route-item:hover {{
    background: #f3f4f6;
}}

.route-pattern {{
    font-family: monospace;
    font-size: 11px;
    font-weight: 700;
}}

.route-name {{
    margin-top: 3px;
    font-size: 10px;
    color: #6b7280;
}}

.main {{
    position: relative;
    flex: 1;
    height: 100%;
    overflow: hidden;
}}

.toolbar {{
    position: absolute;
    top: 14px;
    left: 14px;
    right: 14px;
    z-index: 5;
    display: flex;
    gap: 7px;
    align-items: center;
}}

.toolbar button {{
    border: 1px solid #d1d5db;
    background: rgba(255,255,255,.95);
    padding: 7px 10px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 12px;
    box-shadow: 0 2px 8px rgba(0,0,0,.04);
}}

.toolbar button:hover {{
    background: #f9fafb;
}}

#graph {{
    width: 100%;
    height: 100%;
    cursor: grab;
}}

#graph:active {{
    cursor: grabbing;
}}

.link {{
    stroke: #cbd5e1;
    stroke-width: 1.5;
    fill: none;
}}

.link.htmx {{
    stroke: #7c3aed;
    stroke-width: 2.2;
}}

.link.include {{
    stroke: #0891b2;
    stroke-dasharray: 5 4;
}}

.link.extends {{
    stroke: #64748b;
    stroke-dasharray: 2 4;
}}

.node {{
    cursor: pointer;
}}

.node rect {{
    stroke-width: 1.5;
}}

.node text {{
    pointer-events: none;
    user-select: none;
}}

.node-url rect {{
    fill: #eff6ff;
    stroke: #60a5fa;
}}

.node-view rect {{
    fill: #f0fdf4;
    stroke: #4ade80;
}}

.node-template rect {{
    fill: #fff7ed;
    stroke: #fb923c;
}}

.node-partial rect {{
    fill: #fdf4ff;
    stroke: #d946ef;
}}

.detail {{
    position: absolute;
    top: 65px;
    right: 15px;
    width: 360px;
    max-height: calc(100% - 80px);
    overflow-y: auto;
    background: rgba(255,255,255,.97);
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    box-shadow: 0 12px 40px rgba(0,0,0,.12);
    padding: 16px;
    display: none;
    z-index: 6;
}}

.detail.visible {{
    display: block;
}}

.detail h3 {{
    margin: 0 0 12px;
    font-size: 15px;
}}

.detail-section {{
    margin-top: 14px;
}}

.detail-label {{
    font-size: 10px;
    color: #6b7280;
    text-transform: uppercase;
    font-weight: 700;
    margin-bottom: 5px;
}}

.detail-value {{
    font-size: 12px;
    word-break: break-word;
}}

.badge {{
    display: inline-block;
    padding: 3px 6px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 700;
}}

.badge-url {{
    background: #dbeafe;
    color: #1d4ed8;
}}

.badge-view {{
    background: #dcfce7;
    color: #15803d;
}}

.badge-template {{
    background: #ffedd5;
    color: #c2410c;
}}

.badge-partial {{
    background: #fae8ff;
    color: #a21caf;
}}

.empty {{
    padding: 30px 15px;
    text-align: center;
    color: #9ca3af;
    font-size: 12px;
}}

.legend {{
    position: absolute;
    bottom: 15px;
    left: 15px;
    z-index: 5;
    display: flex;
    gap: 8px;
    padding: 8px;
    background: rgba(255,255,255,.95);
    border: 1px solid #e5e7eb;
    border-radius: 9px;
    font-size: 10px;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 4px;
}}

.dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
}}

@media (max-width: 800px) {{

    .sidebar {{
        width: 260px;
        min-width: 260px;
    }}

    .detail {{
        width: 300px;
    }}

}}

</style>
</head>

<body>

<div class="app">

    <aside class="sidebar">

        <div class="header">

            <div class="title">
                Django Project Map
            </div>

            <div class="subtitle">
                URL → View → Template → HTMX
            </div>

            <div class="stats">

                <div class="stat">
                    <strong>{route_count}</strong>
                    <span>URL</span>
                </div>

                <div class="stat">
                    <strong>{view_count}</strong>
                    <span>VIEW</span>
                </div>

                <div class="stat">
                    <strong>{template_count}</strong>
                    <span>TEMPLATE</span>
                </div>

            </div>

        </div>

        <div class="search">

            <input
                id="search"
                type="search"
                placeholder="URL veya view ara..."
            >

        </div>

        <div class="filters">

            <button
                class="filter active"
                data-filter="all"
            >
                Tümü
            </button>

            <button
                class="filter"
                data-filter="class"
            >
                CBV
            </button>

            <button
                class="filter"
                data-filter="function"
            >
                FBV
            </button>

        </div>

        <div
            id="routes"
            class="routes"
        ></div>

    </aside>


    <main class="main">

        <div class="toolbar">

            <button id="zoomIn">
                +
            </button>

            <button id="zoomOut">
                −
            </button>

            <button id="reset">
                Sıfırla
            </button>

            <button id="hideDetail">
                Detayı kapat
            </button>

        </div>

        <svg id="graph"></svg>

        <div
            id="detail"
            class="detail"
        ></div>

        <div class="legend">

            <div class="legend-item">
                <span
                    class="dot"
                    style="background:#60a5fa"
                ></span>
                URL
            </div>

            <div class="legend-item">
                <span
                    class="dot"
                    style="background:#4ade80"
                ></span>
                View
            </div>

            <div class="legend-item">
                <span
                    class="dot"
                    style="background:#fb923c"
                ></span>
                Template
            </div>

            <div class="legend-item">
                <span
                    class="dot"
                    style="background:#d946ef"
                ></span>
                Partial
            </div>

        </div>

    </main>

</div>


<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>

<script>

const graphData = {graph_json};

const svg = d3.select("#graph");

const width = document.querySelector(".main").clientWidth;
const height = document.querySelector(".main").clientHeight;

svg.attr("viewBox", `0 0 ${{width}} ${{height}}`);

const root = svg.append("g");

const linkLayer = root.append("g");

const nodeLayer = root.append("g");


/* ============================================================
   LINKS
============================================================ */

const links = linkLayer
    .selectAll("line")
    .data(graphData.links)
    .enter()
    .append("line")
    .attr("class", d => {{

        if (
            d.relation &&
            d.relation.includes("HTMX")
        ) {{
            return "link htmx";
        }}

        if (d.relation === "INCLUDE") {{
            return "link include";
        }}

        if (d.relation === "EXTENDS") {{
            return "link extends";
        }}

        return "link";
    }});


/* ============================================================
   NODES
============================================================ */

const node = nodeLayer
    .selectAll("g")
    .data(graphData.nodes)
    .enter()
    .append("g")
    .attr(
        "class",
        d => "node node-" + d.type
    )
    .call(
        d3.drag()
            .on("start", dragStarted)
            .on("drag", dragged)
            .on("end", dragEnded)
    )
    .on("click", showDetails);


node.append("rect")
    .attr("width", 190)
    .attr("height", 48)
    .attr("rx", 8)
    .attr("x", -95)
    .attr("y", -24);


node.append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "-2")
    .attr("font-size", "11px")
    .attr("font-weight", "700")
    .text(d => truncate(d.label, 26));


node.append("text")
    .attr("text-anchor", "middle")
    .attr("dy", "14")
    .attr("font-size", "9px")
    .attr("fill", "#6b7280")
    .text(d => d.type.toUpperCase());


/* ============================================================
   FORCE
============================================================ */

const simulation = d3.forceSimulation(
    graphData.nodes
)
    .force(
        "link",
        d3.forceLink(graphData.links)
            .id(d => d.id)
            .distance(150)
    )
    .force(
        "charge",
        d3.forceManyBody()
            .strength(-500)
    )
    .force(
        "center",
        d3.forceCenter(
            width / 2,
            height / 2
        )
    )
    .force(
        "collision",
        d3.forceCollide(110)
    )
    .on(
        "tick",
        ticked
    );


function ticked() {{

    links
        .attr(
            "x1",
            d => d.source.x
        )
        .attr(
            "y1",
            d => d.source.y
        )
        .attr(
            "x2",
            d => d.target.x
        )
        .attr(
            "y2",
            d => d.target.y
        );

    node.attr(
        "transform",
        d => `translate(${{d.x}},${{d.y}})`
    );
}}


/* ============================================================
   DRAG
============================================================ */

function dragStarted(event, d) {{

    if (!event.active) {{
        simulation.alphaTarget(.3).restart();
    }}

    d.fx = d.x;
    d.fy = d.y;
}}


function dragged(event, d) {{

    d.fx = event.x;
    d.fy = event.y;
}}


function dragEnded(event, d) {{

    if (!event.active) {{
        simulation.alphaTarget(0);
    }}

    d.fx = null;
    d.fy = null;
}}


/* ============================================================
   DETAIL PANEL
============================================================ */

function showDetails(event, d) {{

    event.stopPropagation();

    const detail =
        document.getElementById("detail");

    let html = "";

    html += `
        <span class="badge badge-${{d.type}}">
            ${{d.type.toUpperCase()}}
        </span>

        <h3>
            ${{escapeHtml(d.label)}}
        </h3>
    `;

    if (d.type === "url") {{

        const info = d.details || {{}};

        html += section(
            "URL",
            info.pattern || ""
        );

        html += section(
            "Name",
            info.name || ""
        );

        html += section(
            "View",
            info.view_class ||
            info.view ||
            ""
        );

        html += section(
            "View tipi",
            info.view_type || ""
        );

        html += section(
            "Module",
            info.module || ""
        );
    }}

    if (
        d.type === "template" ||
        d.type === "partial"
    ) {{

        const info = d.details || {{}};

        html += section(
            "Template",
            info.template || d.label
        );

        if (info.path) {{
            html += section(
                "Dosya",
                info.path
            );
        }}

        if (
            info.includes &&
            info.includes.length
        ) {{

            html += section(
                "Include",
                info.includes.join("<br>")
            );
        }}

        if (
            info.htmx_urls &&
            info.htmx_urls.length
        ) {{

            html += section(
                "HTMX URL",
                info.htmx_urls.join("<br>")
            );
        }}

        if (
            info.urls &&
            info.urls.length
        ) {{

            html += section(
                "URL",
                info.urls.join("<br>")
            );
        }}
    }}

    if (d.type === "view") {{

        const info = d.details || {{}};

        html += section(
            "View",
            info.view_class ||
            info.view ||
            ""
        );

        html += section(
            "View tipi",
            info.view_type || ""
        );

        html += section(
            "Module",
            info.module || ""
        );

        html += section(
            "Dosya",
            info.file || ""
        );
    }}

    detail.innerHTML = html;

    detail.classList.add(
        "visible"
    );
}}


function section(label, value) {{

    if (!value) {{
        return "";
    }}

    return `
        <div class="detail-section">

            <div class="detail-label">
                ${{escapeHtml(label)}}
            </div>

            <div class="detail-value">
                ${{value}}
            </div>

        </div>
    `;
}}


function escapeHtml(value) {{

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}}


/* ============================================================
   SEARCH
============================================================ */

const searchInput =
    document.getElementById("search");

searchInput.addEventListener(
    "input",
    applyFilters
);


let activeFilter = "all";


document
    .querySelectorAll(".filter")
    .forEach(button => {{

        button.addEventListener(
            "click",
            () => {{

                document
                    .querySelectorAll(".filter")
                    .forEach(
                        x => x.classList.remove("active")
                    );

                button.classList.add("active");

                activeFilter =
                    button.dataset.filter;

                applyFilters();
            }}
        );

    }});


function applyFilters() {{

    const query =
        searchInput.value
            .trim()
            .toLowerCase();

    node.style(
        "opacity",
        d => {{

            const text = (
                d.label +
                " " +
                d.type
            ).toLowerCase();

            const searchMatch =
                !query ||
                text.includes(query);

            return searchMatch
                ? 1
                : .08;
        }}
    );

    links.style(
        "opacity",
        d => {{

            const source = d.source;
            const target = d.target;

            const sourceMatch =
                !query ||
                (
                    source.label +
                    " " +
                    source.type
                )
                .toLowerCase()
                .includes(query);

            const targetMatch =
                !query ||
                (
                    target.label +
                    " " +
                    target.type
                )
                .toLowerCase()
                .includes(query);

            return (
                sourceMatch ||
                targetMatch
            )
                ? 1
                : .05;
        }}
    );
}}


/* ============================================================
   ROUTE LIST
============================================================ */

const routeContainer =
    document.getElementById("routes");

const routes =
    graphData.nodes
        .filter(
            d => d.type === "url"
        )
        .map(
            d => d.details
        )
        .sort(
            (a, b) =>
                (a.pattern || "")
                .localeCompare(
                    b.pattern || ""
                )
        );


function renderRoutes() {{

    const query =
        searchInput.value
            .trim()
            .toLowerCase();

    const filtered =
        routes.filter(route => {{

            const text = (
                route.pattern +
                " " +
                route.name +
                " " +
                route.view
            ).toLowerCase();

            return (
                !query ||
                text.includes(query)
            );
        }});

    if (!filtered.length) {{

        routeContainer.innerHTML =
            '<div class="empty">Sonuç bulunamadı.</div>';

        return;
    }}

    routeContainer.innerHTML =
        filtered.map(route => `

            <div
                class="route-item"
                data-pattern="${{escapeAttr(route.pattern)}}"
            >

                <div class="route-pattern">
                    ${{escapeHtml(route.pattern)}}
                </div>

                <div class="route-name">
                    ${{escapeHtml(route.name || "-")}}
                </div>

            </div>

        `).join("");

    routeContainer
        .querySelectorAll(".route-item")
        .forEach(item => {{

            item.addEventListener(
                "click",
                () => {{

                    const pattern =
                        item.dataset.pattern;

                    const found =
                        graphData.nodes.find(
                            n =>
                                n.type === "url" &&
                                n.details.pattern === pattern
                        );

                    if (!found) {{
                        return;
                    }}

                    showDetails(
                        {{
                            stopPropagation() {{}}
                        }},
                        found
                    );

                    centerNode(found);
                }}
            );

        }});
}}


function escapeAttr(value) {{

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll('"', "&quot;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
}}


searchInput.addEventListener(
    "input",
    renderRoutes
);

renderRoutes();


/* ============================================================
   CENTER NODE
============================================================ */

function centerNode(d) {{

    const scale = 1.15;

    const tx =
        width / 2 -
        d.x * scale;

    const ty =
        height / 2 -
        d.y * scale;

    root
        .transition()
        .duration(500)
        .attr(
            "transform",
            `translate(${{tx}},${{ty}}) scale(${{scale}})`
        );
}}


/* ============================================================
   ZOOM
============================================================ */

let currentScale = 1;

document
    .getElementById("zoomIn")
    .addEventListener(
        "click",
        () => zoomBy(1.2)
    );

document
    .getElementById("zoomOut")
    .addEventListener(
        "click",
        () => zoomBy(.8)
    );


document
    .getElementById("reset")
    .addEventListener(
        "click",
        () => {{

            currentScale = 1;

            root
                .transition()
                .duration(400)
                .attr(
                    "transform",
                    "translate(0,0) scale(1)"
                );
        }}
    );


function zoomBy(factor) {{

    currentScale *= factor;

    root
        .transition()
        .duration(250)
        .attr(
            "transform",
            `scale(${{currentScale}})`
        );
}}


document
    .getElementById("hideDetail")
    .addEventListener(
        "click",
        () => {{

            document
                .getElementById("detail")
                .classList.remove("visible");

        }}
    );


/* ============================================================
   HELPERS
============================================================ */

function truncate(text, max) {{

    text = String(text || "");

    if (text.length <= max) {{
        return text;
    }}

    return text.substring(
        0,
        max - 1
    ) + "…";
}}

</script>

</body>
</html>
"""


# ============================================================
# AST ANALYZER
# ============================================================

class ViewASTAnalyzer(ast.NodeVisitor):

    def __init__(self):
        self.views = {}

        self.current_view = None

    # --------------------------------------------------------
    # Function
    # --------------------------------------------------------

    def visit_FunctionDef(self, node):

        previous = self.current_view

        self.current_view = node.name

        templates = set()

        for child in ast.walk(node):

            template = self.extract_template_from_call(
                child
            )

            if template:
                templates.add(template)

        if templates:

            self.views.setdefault(
                node.name,
                set(),
            ).update(
                templates
            )

        self.current_view = previous

        # Burada generic visit yapmıyoruz;
        # nested function'ları ayrı ele al.
        self.generic_visit(node)

    # --------------------------------------------------------
    # Async Function
    # --------------------------------------------------------

    def visit_AsyncFunctionDef(self, node):

        previous = self.current_view

        self.current_view = node.name

        templates = set()

        for child in ast.walk(node):

            template = self.extract_template_from_call(
                child
            )

            if template:
                templates.add(template)

        if templates:

            self.views.setdefault(
                node.name,
                set(),
            ).update(
                templates
            )

        self.current_view = previous

        self.generic_visit(node)

    # --------------------------------------------------------
    # Class
    # --------------------------------------------------------

    def visit_ClassDef(self, node):

        class_name = node.name

        templates = set()

        # template_name = "..."
        for child in node.body:

            if isinstance(
                child,
                ast.Assign,
            ):

                for target in child.targets:

                    if (
                        isinstance(
                            target,
                            ast.Name,
                        )
                        and target.id
                        == "template_name"
                    ):

                        value = (
                            self.constant_string(
                                child.value
                            )
                        )

                        if value:
                            templates.add(value)

            elif isinstance(
                child,
                ast.AnnAssign,
            ):

                if (
                    isinstance(
                        child.target,
                        ast.Name,
                    )
                    and child.target.id
                    == "template_name"
                ):

                    value = (
                        self.constant_string(
                            child.value
                        )
                    )

                    if value:
                        templates.add(value)

        # get_template_names()
        for child in ast.walk(node):

            if isinstance(
                child,
                ast.Return,
            ):

                value = (
                    self.constant_string(
                        child.value
                    )
                )

                if value:
                    templates.add(value)

            template = (
                self.extract_template_from_call(
                    child
                )
            )

            if template:
                templates.add(template)

        if templates:

            self.views.setdefault(
                class_name,
                set(),
            ).update(
                templates
            )

        self.generic_visit(node)

    # --------------------------------------------------------
    # render(...)
    # TemplateResponse(...)
    # render_to_response(...)
    # --------------------------------------------------------

    def extract_template_from_call(
        self,
        node,
    ):

        if not isinstance(
            node,
            ast.Call,
        ):
            return None

        func_name = ""

        if isinstance(
            node.func,
            ast.Name,
        ):
            func_name = node.func.id

        elif isinstance(
            node.func,
            ast.Attribute,
        ):
            func_name = node.func.attr

        supported = {
            "render",
            "TemplateResponse",
            "render_to_response",
            "get_template",
            "select_template",
        }

        if func_name not in supported:
            return None

        # render(request, "template.html", ...)
        if node.args:

            start_index = 1

            # get_template("...")
            if func_name == "get_template":
                start_index = 0

            if len(node.args) > start_index:

                value = self.constant_string(
                    node.args[start_index]
                )

                if value:
                    return value

        # template_name="..."
        for keyword in node.keywords:

            if keyword.arg in {
                "template_name",
                "template",
            }:

                value = self.constant_string(
                    keyword.value
                )

                if value:
                    return value

        return None

    # --------------------------------------------------------
    # Constant string
    # --------------------------------------------------------

    def constant_string(self, node):
        if node is None:
            return None

        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return node.value

        return None
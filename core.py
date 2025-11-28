import os
import json
import shutil
import git
import tempfile
import re
import stat

# --- CONFIGURATION ---
STD_LIBS = {
    'python': {
        'os', 'sys', 're', 'json', 'math', 'datetime', 'time', 'random',
        'subprocess', 'typing', 'collections', 'threading', 'asyncio',
        'logging', 'argparse', 'itertools', 'functools', 'pathlib', 'http',
        'email', 'enum', 'statistics', 'fractions'
    },
    'node': {
        'fs', 'path', 'http', 'https', 'os', 'util', 'events', 'crypto',
        'child_process', 'cluster', 'dns', 'net', 'stream', 'querystring',
        'url', 'zlib', 'timers'
    },
    'java': {'java.lang', 'java.util', 'java.io', 'java.net', 'java.math'},
    'go': {'fmt', 'os', 'net', 'time', 'encoding', 'sync', 'strings',
           'strconv', 'io', 'log', 'bufio', 'errors', 'context'}
}

IGNORE_DIRS = {
    '.git', 'node_modules', 'venv', '.env', '__pycache__',
    'dist', 'build', 'target', 'vendor', '.idea', '.vscode',
    'coverage', '.next', '__mocks__', 'assets', 'bin', 'obj', 'out', '.settings'
}


class DeepScanner:
    def __init__(self, path, custom_context=""):
        self.original_path = path
        self.path = path
        self.custom_context = custom_context
        self.is_remote = path.startswith('http') or path.endswith('.git')
        self.temp_dir = None

        # internal helpers
        self._service_info = {}      # top-level folder -> info
        self._api_endpoint_set = set()

        self.metadata = {
            "project_name": "",
            "username": "username",
            "repo_name": "repo",
            "repo_url": "<repo_url>",

            "languages": set(),
            "tech_stack": set(),      # legacy flat labels
            "tech_stack_details": {   # structured details
                "frameworks": set(),
                "databases": set(),
                "auth": set(),
                "cache": set()
            },

            "dependencies": {
                "Python": set(),
                "Node.js": set(),
                "Java": set(),
                "Go": set()
            },
            "scripts": {},
            "structure": "",
            "description": "",

            # Entry points
            "entry_point": None,          # legacy single entry
            "entry_points": {             # per-language entries
                "Python": None,
                "Node.js": None,
                "Java": None,
                "Go": None
            },
            "entry_point_cmd": None,      # Java main class if any

            "api_endpoints": [],          # list of "METHOD /path"
            "license": "Unlicensed",
            "modules": [],                # classes/modules
            "env_vars": set(),

            "tests": [],                  # detected test frameworks
            "build_tools": set(),         # Maven, Gradle, Poetry, etc.

            # Paths to important files
            "python_requirements_path": None,
            "node_package_json_path": None,
            "go_mod_path": None,

            # Docker info
            "docker": {
                "dockerfile": False,
                "compose": False
            },

            # Monorepo services
            "services": [],

            # Project health stats
            "stats": {
                "files": {
                    "Python": 0,
                    "Node.js": 0,
                    "Java": 0,
                    "Go": 0
                },
                "test_files": 0,
                "has_ci": False,
                "linting": set()
            }
        }

    # ---------- High-level public API ----------

    def setup_path(self):
        if self.is_remote:
            self.temp_dir = tempfile.mkdtemp()
            try:
                git.Repo.clone_from(self.original_path, self.temp_dir)
                self.path = self.temp_dir
                self.metadata["repo_url"] = self.original_path
                parts = self.original_path.rstrip('/').split('/')
                if len(parts) >= 2:
                    self.metadata["repo_name"] = parts[-1].replace('.git', '')
                    self.metadata["username"] = parts[-2]
                    self.metadata["project_name"] = self.metadata["repo_name"]
            except Exception as e:
                self.cleanup()
                raise Exception(f"Clone failed: {str(e)}")
        else:
            if not os.path.exists(self.path):
                raise Exception("Local path does not exist.")
            self.metadata["project_name"] = os.path.basename(os.path.normpath(self.path))
            try:
                repo = git.Repo(self.path)
                url = repo.remotes.origin.url
                self.metadata["repo_url"] = url
                parts = url.rstrip('/').replace('.git', '').split('/')
                self.metadata["repo_name"] = parts[-1]
                self.metadata["username"] = parts[-2].split(':')[-1]
            except Exception:
                pass
        return self.path

    def cleanup(self):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                def on_rm_error(func, path, exc_info):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)
                shutil.rmtree(self.temp_dir, onerror=on_rm_error)
            except Exception:
                pass

    def scan(self):
        self._scan_license()
        self._scan_tree(self.path)
        self._finalize_services()
        self._infer_tech_stack()

        if not self.metadata["description"]:
            self.metadata["description"] = self._generate_smart_description()
        return self.metadata

    def get_serializable_metadata(self):
        """Return metadata as JSON-serializable dict (sets -> lists)."""
        m = self.metadata
        out = json.loads(json.dumps(m, default=self._json_default))
        return out

    @staticmethod
    def _json_default(obj):
        if isinstance(obj, set):
            return list(obj)
        return str(obj)

    # ---------- Description / license ----------

    def _generate_smart_description(self):
        name = self.metadata["project_name"].replace('-', ' ').replace('_', ' ').title()
        langs = list(self.metadata["languages"])

        ptype = "Software Solution"
        if "Api" in name:
            ptype = "RESTful API"
        elif "Web" in name or "Ui" in name:
            ptype = "Web Application"
        elif "Lib" in name or "Sdk" in name:
            ptype = "Library"
        elif "Management" in name or "System" in name:
            ptype = "Management System"

        desc = f"**{name}** is a {ptype}"
        if langs:
            desc += f" built with **{sorted(langs)[0]}**"

        # Use structured tech stack details if available
        details = self.metadata.get("tech_stack_details", {})
        frameworks = sorted(details.get("frameworks", []))
        dbs = sorted(details.get("databases", []))

        if frameworks:
            desc += f", leveraging **{frameworks[0]}** for the architecture"
        if dbs:
            desc += f" and **{dbs[0]}** for data storage"

        desc += "."
        return desc

    def _scan_license(self):
        for f in os.listdir(self.path):
            if f.upper().startswith('LICENSE') or f.upper().startswith('COPYING'):
                try:
                    with open(os.path.join(self.path, f), 'r', encoding="utf-8", errors="ignore") as lic_file:
                        content = lic_file.read(200).upper()
                        if "MIT" in content:
                            self.metadata["license"] = "MIT"
                        elif "APACHE" in content:
                            self.metadata["license"] = "Apache 2.0"
                        elif "GNU" in content or "GPL" in content:
                            self.metadata["license"] = "GPL"
                        else:
                            self.metadata["license"] = "See LICENSE file"
                except Exception:
                    pass
                break

    # ---------- Tree / file scanning ----------

    def _scan_tree(self, root_path):
        tree_lines = []
        stats = self.metadata["stats"]

        for root, dirs, files in os.walk(root_path):
            # Filter out ignored dirs
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            rel_path = os.path.relpath(root, root_path)
            level = 0 if rel_path == '.' else rel_path.count(os.sep) + 1

            # CI detection via directory structure
            if root.endswith(os.path.join('.github')) and 'workflows' in dirs:
                stats["has_ci"] = True

            # Tree representation
            if level < 4:
                indent = '│   ' * level
                subindent = '├── '
                if level > 0:
                    tree_lines.append(f"{indent}{subindent}{os.path.basename(root)}/")
                for f in files:
                    if f.endswith(('.java', '.py', '.js', '.ts', '.go', '.json', '.xml', '.md', '.yml', '.yaml')):
                        tree_lines.append(f"{indent}│   {f}")

            # Top-level service detection (monorepo-ish)
            if rel_path != '.':
                top_service = rel_path.split(os.sep)[0]
                if top_service not in self._service_info:
                    self._service_info[top_service] = {
                        "path": top_service,
                        "has_package_json": False,
                        "has_requirements": False,
                        "has_pom": False,
                        "has_go_mod": False
                    }
            else:
                top_service = None

            for f in files:
                filepath = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower()

                # CI configs by file name
                if f in ('circle.yml', '.gitlab-ci.yml', 'azure-pipelines.yml',
                         'bitbucket-pipelines.yml', '.travis.yml'):
                    stats["has_ci"] = True

                # Linting configs
                lint = stats["linting"]
                if f.startswith('.eslintrc') or f in ('.prettierrc', '.prettierrc.js', '.prettierrc.json'):
                    lint.add("JavaScript/TypeScript")
                if f in ('pylintrc', '.flake8'):
                    lint.add("Python")
                if f == 'pyproject.toml':
                    lint.add("Python (pyproject)")

                # Docker detection
                if f == 'Dockerfile':
                    self.metadata["docker"]["dockerfile"] = True
                if f in ('docker-compose.yml', 'docker-compose.yaml'):
                    self.metadata["docker"]["compose"] = True

                # Config & Build Tools
                if f == 'package.json':
                    if self.metadata["node_package_json_path"] is None:
                        self.metadata["node_package_json_path"] = os.path.relpath(filepath, self.path)
                    self.metadata["languages"].add("Node.js")
                    if top_service:
                        self._service_info[top_service]["has_package_json"] = True
                    self._parse_package_json(filepath)

                elif f == 'requirements.txt':
                    if self.metadata["python_requirements_path"] is None:
                        self.metadata["python_requirements_path"] = os.path.relpath(filepath, self.path)
                    self.metadata["languages"].add("Python")
                    if top_service:
                        self._service_info[top_service]["has_requirements"] = True
                    self._parse_requirements(filepath)

                elif f == 'pom.xml':
                    self.metadata["languages"].add("Java")
                    self.metadata["build_tools"].add("Maven")
                    if top_service:
                        self._service_info[top_service]["has_pom"] = True

                elif f == 'build.gradle':
                    self.metadata["languages"].add("Java")
                    self.metadata["build_tools"].add("Gradle")

                elif f == 'go.mod':
                    self.metadata["languages"].add("Go")
                    if self.metadata["go_mod_path"] is None:
                        self.metadata["go_mod_path"] = os.path.relpath(filepath, self.path)
                    if top_service:
                        self._service_info[top_service]["has_go_mod"] = True

                # Code Analysis
                if ext in ['.py', '.js', '.ts', '.java', '.go']:
                    # stats: file counts
                    if ext == '.py':
                        stats["files"]["Python"] += 1
                    elif ext in ['.js', '.ts']:
                        stats["files"]["Node.js"] += 1
                    elif ext == '.java':
                        stats["files"]["Java"] += 1
                    elif ext == '.go':
                        stats["files"]["Go"] += 1

                    # test file heuristics
                    if ext == '.py':
                        if (f.startswith('test_') or f.endswith('_test.py') or
                                'tests' in root.split(os.sep)):
                            stats["test_files"] += 1
                    elif ext in ['.js', '.ts']:
                        if (f.endswith(('.test.js', '.spec.js', '.test.ts', '.spec.ts')) or
                                '__tests__' in root.split(os.sep)):
                            stats["test_files"] += 1

                    self._analyze_code(filepath, ext)

        self.metadata["structure"] = "```text\n.\n" + "\n".join(tree_lines) + "\n```"

    # ---------- Parse manifest files ----------

    def _parse_package_json(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
                if data.get('name'):
                    self.metadata["project_name"] = data.get('name')

                if data.get('main'):
                    # per-language entry
                    if not self.metadata["entry_points"]["Node.js"]:
                        self.metadata["entry_points"]["Node.js"] = data.get('main')
                    if not self.metadata["entry_point"]:
                        self.metadata["entry_point"] = data.get('main')

                deps = list(data.get('dependencies', {}).keys())
                devDeps = list(data.get('devDependencies', {}).keys())

                self.metadata["dependencies"]["Node.js"].update(deps)
                self.metadata["scripts"] = data.get('scripts', {})
                if data.get('description'):
                    self.metadata["description"] = data.get('description')

                # Detect Testing Frameworks
                for d in deps + devDeps:
                    if d in ['jest', 'mocha', 'chai', 'supertest']:
                        self.metadata["tests"].append(d)
        except Exception:
            pass

    def _parse_requirements(self, filepath):
        try:
            with open(filepath, encoding="utf-8") as f:
                deps = [
                    line.split('==')[0].strip()
                    for line in f
                    if line.strip() and not line.strip().startswith('#')
                ]
                self.metadata["dependencies"]["Python"].update(deps)
                for d in deps:
                    if d in ['pytest', 'unittest', 'nose', 'mock']:
                        self.metadata["tests"].append(d)
        except Exception:
            pass

    # ---------- Code analysis ----------

    def _analyze_code(self, filepath, ext):
        try:
            with open(filepath, 'r', errors='ignore', encoding='utf-8') as f:
                content = f.read()
                fname = os.path.basename(filepath)

                # --- PYTHON ---
                if ext == '.py':
                    self.metadata["languages"].add("Python")

                    if ('if __name__ == "__main__":' in content or 'app.run(' in content):
                        if not self.metadata["entry_points"]["Python"]:
                            self.metadata["entry_points"]["Python"] = fname
                        if not self.metadata["entry_point"]:
                            self.metadata["entry_point"] = fname

                    classes = re.findall(r'class\s+(\w+)', content)
                    for c in classes:
                        self.metadata["modules"].append(c)

                    imports = re.findall(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE)
                    for imp in imports:
                        root_imp = imp.split('.')[0]
                        if root_imp not in STD_LIBS['python']:
                            self.metadata["dependencies"]["Python"].add(root_imp)

                # --- NODE.JS / TS ---
                elif ext in ['.js', '.ts']:
                    self.metadata["languages"].add("Node.js")

                    if 'app.listen' in content or 'server.listen' in content:
                        if not self.metadata["entry_points"]["Node.js"]:
                            self.metadata["entry_points"]["Node.js"] = fname
                        if not self.metadata["entry_point"]:
                            self.metadata["entry_point"] = fname

                    imports = re.findall(r'(?:require|from)\s*[\'"]([@\w./-]+)[\'"]', content)
                    for imp in imports:
                        if not imp.startswith('.') and imp.split('/')[0] not in STD_LIBS['node']:
                            self.metadata["dependencies"]["Node.js"].add(imp.split('/')[0])

                # --- GO ---
                elif ext == '.go':
                    self.metadata["languages"].add("Go")

                    if 'func main()' in content:
                        if not self.metadata["entry_points"]["Go"]:
                            self.metadata["entry_points"]["Go"] = fname
                        if not self.metadata["entry_point"]:
                            self.metadata["entry_point"] = fname

                    imports = re.findall(r'"([\w/\.]+)"', content)
                    for imp in imports:
                        # crude heuristic: external packages usually contain dots or slashes
                        if '.' in imp or '/' in imp:
                            self.metadata["dependencies"]["Go"].add(imp)

                # --- JAVA ---
                elif ext == '.java':
                    self.metadata["languages"].add("Java")

                    class_match = re.search(r'class\s+(\w+)', content)
                    if class_match:
                        self.metadata["modules"].append(class_match.group(1))

                    if "public static void main" in content:
                        if not self.metadata["entry_points"]["Java"]:
                            self.metadata["entry_points"]["Java"] = fname
                        if not self.metadata["entry_point"]:
                            self.metadata["entry_point"] = fname
                        if class_match:
                            self.metadata["entry_point_cmd"] = class_match.group(1)

                    imports = re.findall(r'import\s+([\w\.]+);', content)
                    for imp in imports:
                        if not any(imp.startswith(std) for std in ['java.lang', 'java.util', 'java.io']):
                            self.metadata["dependencies"]["Java"].add(imp)

                # Env Vars (Universal)
                self._detect_env_vars(content)

                # API endpoints
                self._detect_api_endpoints(content, ext, filepath)

        except Exception:
            pass

    def _detect_env_vars(self, content):
        # process.env.VAR, os.environ["VAR"], os.environ.get("VAR"), os.getenv("VAR")
        pattern = (
            r'process\.env\.([A-Z_][A-Z0-9_]*)'
            r'|os\.environ\[\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]\s*\]'
            r'|os\.environ\.get\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]'
            r'|os\.getenv\(\s*[\'"]([A-Z_][A-Z0-9_]*)[\'"]'
        )
        matches = re.findall(pattern, content)
        for group in matches:
            for name in group:
                if name:
                    self.metadata["env_vars"].add(name)

    def _detect_api_endpoints(self, content, ext, filepath):
        # Very heuristic, but good enough for auto-doc starting point
        endpoints = set()

        if ext == '.py':
            # FastAPI style: @app.get("/path")
            for method, path in re.findall(
                r'@app\.(get|post|put|delete|patch|options|head)\(\s*[\'"]([^\'"]+)[\'"]',
                content,
                flags=re.IGNORECASE
            ):
                endpoints.add(f"{method.upper()} {path}")

            # Flask: @app.route("/path", methods=["GET","POST"])
            for path, methods in re.findall(
                r'@app\.route\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*methods\s*=\s*\[([^\]]+)\]',
                content
            ):
                for m in re.findall(r'[\'"]([A-Z]+)[\'"]', methods):
                    endpoints.add(f"{m.upper()} {path}")

            # Django urls.py: path("users/", ...)
            fname = os.path.basename(filepath)
            if fname in ('urls.py', 'routes.py'):
                for path in re.findall(r'path\(\s*[\'"]([^\'"]+)[\'"]', content):
                    clean = "/" + path.strip('/ ')
                    endpoints.add(f"* {clean}")

        elif ext in ['.js', '.ts']:
            # Express: app.get('/path', ...), router.post('/path', ...)
            for method, path in re.findall(
                r'\bapp\.(get|post|put|delete|patch|options|head)\(\s*[\'"]([^\'"]+)[\'"]',
                content,
                flags=re.IGNORECASE
            ):
                endpoints.add(f"{method.upper()} {path}")
            for method, path in re.findall(
                r'\brouter\.(get|post|put|delete|patch|options|head)\(\s*[\'"]([^\'"]+)[\'"]',
                content,
                flags=re.IGNORECASE
            ):
                endpoints.add(f"{method.upper()} {path}")

        for ep in sorted(endpoints):
            if ep not in self.metadata["api_endpoints"]:
                self.metadata["api_endpoints"].append(ep)

    # ---------- Tech stack inference ----------

    def _infer_tech_stack(self):
        """Fill tech_stack_details + tech_stack based on dependencies."""
        m = self.metadata
        details = m["tech_stack_details"]

        py_deps = {d.lower() for d in m["dependencies"]["Python"]}
        node_deps = {d.lower() for d in m["dependencies"]["Node.js"]}
        java_deps = {d.lower() for d in m["dependencies"]["Java"]}
        go_deps = {d.lower() for d in m["dependencies"]["Go"]}

        # Frameworks
        if 'django' in py_deps:
            details["frameworks"].add("Django")
        if 'flask' in py_deps:
            details["frameworks"].add("Flask")
        if 'fastapi' in py_deps:
            details["frameworks"].add("FastAPI")

        if 'express' in node_deps:
            details["frameworks"].add("Express")
        if 'next' in node_deps or 'next.js' in node_deps:
            details["frameworks"].add("Next.js")
        if 'nuxt' in node_deps or 'nuxt.js' in node_deps:
            details["frameworks"].add("Nuxt.js")
        if 'nest' in node_deps or 'nestjs' in node_deps:
            details["frameworks"].add("NestJS")
        if 'koa' in node_deps:
            details["frameworks"].add("Koa")

        if any('spring' in d for d in java_deps):
            details["frameworks"].add("Spring/Spring Boot")

        if 'gin' in go_deps:
            details["frameworks"].add("Gin")
        if 'echo' in go_deps:
            details["frameworks"].add("Echo")

        # Databases
        if {'psycopg2', 'psycopg2-binary'} & py_deps:
            details["databases"].add("PostgreSQL")
        if 'mysqlclient' in py_deps or 'pymysql' in py_deps:
            details["databases"].add("MySQL")
        if 'pymongo' in py_deps or 'motor' in py_deps:
            details["databases"].add("MongoDB")
        if 'sqlalchemy' in py_deps:
            details["databases"].add("SQL (SQLAlchemy)")

        if 'mongoose' in node_deps:
            details["databases"].add("MongoDB")
        if 'pg' in node_deps or 'pg-promise' in node_deps:
            details["databases"].add("PostgreSQL")
        if 'mysql2' in node_deps:
            details["databases"].add("MySQL")
        if 'redis' in node_deps or 'ioredis' in node_deps:
            details["databases"].add("Redis")

        # Auth
        if 'jsonwebtoken' in node_deps or 'jwt' in py_deps:
            details["auth"].add("JWT")
        if 'passport' in node_deps:
            details["auth"].add("Passport.js")
        if 'django-allauth' in py_deps:
            details["auth"].add("Django Allauth")
        if 'djangorestframework-simplejwt' in py_deps:
            details["auth"].add("DRF + JWT")

        # Cache
        if 'redis' in node_deps or 'ioredis' in node_deps or 'redis' in py_deps:
            details["cache"].add("Redis")

        # Mirror into flat tech_stack labels
        for fw in details["frameworks"]:
            m["tech_stack"].add(f"Framework: {fw}")
        for db in details["databases"]:
            m["tech_stack"].add(f"Database: {db}")
        for au in details["auth"]:
            m["tech_stack"].add(f"Auth: {au}")
        for c in details["cache"]:
            m["tech_stack"].add(f"Cache: {c}")

    def _finalize_services(self):
        for name, info in self._service_info.items():
            langs = []
            if info["has_package_json"]:
                langs.append("Node.js")
            if info["has_requirements"]:
                langs.append("Python")
            if info["has_pom"]:
                langs.append("Java")
            if info["has_go_mod"]:
                langs.append("Go")

            self.metadata["services"].append({
                "name": name,
                "path": info["path"],
                "languages": langs
            })

    # ---------- Diagrams ----------

    def generate_diagrams(self):
        # 1. Component Architecture (Graph)
        chart = "```mermaid\ngraph TD\n"

        # Scenario A: Java/Python Class Diagram
        if ("Java" in self.metadata["languages"] or "Python" in self.metadata["languages"]) and self.metadata["modules"]:
            entry = (self.metadata["entry_point_cmd"]
                     or self.metadata["entry_point"]
                     or "Main")
            if isinstance(entry, str) and (entry.endswith('.py') or entry.endswith('.java')):
                entry = entry.split('.')[0]

            chart += f"    {entry} --> Logic_Layer\n"
            for mod in self.metadata["modules"][:6]:
                if mod != entry:
                    chart += f"    Logic_Layer --> {mod}\n"

        # Scenario B: Node/Go Component Diagram
        else:
            chart += "    User[User] --> UI[Client]\n"
            backend = self.metadata["entry_point"] or "Server"
            chart += f"    UI --> {backend}\n"

            # Map Frameworks/DBs
            for dep in (self.metadata["dependencies"].get("Node.js", set()) |
                        self.metadata["dependencies"].get("Python", set())):
                if dep in ['mongoose', 'mongodb', 'pg', 'mysql', 'mysql2', 'sequelize']:
                    chart += f"    {backend} --> {dep}[({dep} DB)]\n"
                elif dep in ['redis', 'ioredis']:
                    chart += f"    {backend} --> {dep}(({dep} Cache))\n"

        chart += "```\n\n"

        # 2. Application Flow (Sequence)
        flow = "```mermaid\nsequenceDiagram\n    participant User\n    participant System\n"

        # Detect DB usage for Sequence Diagram
        has_db = any("Database" in t for t in self.metadata["tech_stack"])
        if not has_db:
            for lang, deps in self.metadata["dependencies"].items():
                if any(d in ['mongoose', 'mongodb', 'sqlalchemy', 'pymongo', 'mysql',
                             'mysql2', 'pg', 'psycopg2', 'psycopg2-binary'] for d in deps):
                    has_db = True
                    break

        if has_db:
            flow += "    participant DB as Database\n"

        flow += "    User->>System: Request\n"
        flow += "    System->>System: Process Logic\n"

        if has_db:
            flow += "    System->>DB: Query Data\n    DB-->>System: Return Data\n"

        flow += "    System-->>User: Response\n```"

        return "### Component Architecture\n" + chart + "### Application Flow\n" + flow

    # ---------- README generation ----------

    def build_markdown(self, template="Detailed"):
        m = self.metadata
        langs = sorted(list(m["languages"]))

        md = f"# {m['project_name']}\n\n"

        if template == "Minimal":
            # language badges
            for l in langs:
                md += f"![{l}](https://img.shields.io/badge/Language-{l}-blue) "
            md += "\n\n"
            md += f"## 📝 Description\n{m['description']}\n\n"
            if self.custom_context:
                md += f"> **Context:** {self.custom_context}\n\n"
            md += "## 🛠 Tech Stack\n"
            if self._has_tech_stack_details():
                md += self._generate_tech_stack_list() + "\n"
            else:
                md += ", ".join(langs) + "\n\n"
            md += "## ⚙️ Installation\n" + self._generate_strict_install(langs)
            md += "## 🚀 Usage\n" + self._generate_strict_usage(langs)
            if m["env_vars"]:
                md += self._generate_env_section()
            if m["api_endpoints"]:
                md += self._generate_api_section()
            md += f"## 📄 License\n{m['license']}"
            return md

        # Detailed
        if m['username'] != "username":
            user, repo = m['username'], m['repo_name']
            md += (
                f"[![Stars](https://img.shields.io/github/stars/{user}/{repo}?style=social)]"
                f"(https://github.com/{user}/{repo}/stargazers) "
            )
            md += (
                f"[![Forks](https://img.shields.io/github/forks/{user}/{repo}?style=social)]"
                f"(https://github.com/{user}/{repo}/network/members)\n"
            )
        else:
            for l in langs:
                md += f"![{l}](https://img.shields.io/badge/Language-{l}-blue) "
        md += f"![License](https://img.shields.io/badge/License-{m['license'].replace(' ', '_')}-green)\n\n"

        md += f"## 📝 Description\n{m['description']}\n\n"
        if self.custom_context:
            md += f"> **Developer Note:** {self.custom_context}\n\n"

        md += "## 📸 Screenshot\n![App Screenshot](https://via.placeholder.com/800x400?text=Application+Screenshot)\n\n"

        # Table of contents
        md += "## 📑 Table of Contents\n"
        if self._has_tech_stack_details():
            md += "- [Tech Stack](#-tech-stack)\n"
        md += "- [Architecture](#-architecture)\n"
        md += "- [Project Structure](#-project-structure)\n"
        md += "- [Installation](#-installation)\n"
        md += "- [Usage](#-usage)\n"
        if m["api_endpoints"]:
            md += "- [API Endpoints](#-api-endpoints)\n"
        if m["env_vars"]:
            md += "- [Environment Variables](#-environment-variables)\n"
        if m["docker"]["dockerfile"] or m["docker"]["compose"]:
            md += "- [Docker](#-docker)\n"
        if m["services"]:
            md += "- [Services](#-services)\n"
        if m["scripts"]:
            md += "- [Scripts](#-scripts)\n"
        if any(m["dependencies"].values()):
            md += "- [Dependencies](#-dependencies)\n"
        if m["tests"] or m["stats"]["test_files"] > 0:
            md += "- [Testing](#-testing)\n"
        md += "- [Project Health](#-project-health)\n"
        md += "- [Contributing](#-contributing)\n"
        md += "- [Next Steps](#-next-steps)\n"
        md += "- [License](#-license)\n\n"

        # Sections
        if self._has_tech_stack_details():
            md += "## 🛠 Tech Stack\n" + self._generate_tech_stack_list() + "\n"

        md += "## 🏗 Architecture\n" + self.generate_diagrams() + "\n\n"
        md += "## 📂 Project Structure\n" + m["structure"] + "\n\n"
        md += "## ⚙️ Installation\n" + self._generate_strict_install(langs)
        md += "## 🚀 Usage\n" + self._generate_strict_usage(langs)

        if m["api_endpoints"]:
            md += self._generate_api_section()
        if m["env_vars"]:
            md += self._generate_env_section()
        if m["docker"]["dockerfile"] or m["docker"]["compose"]:
            md += self._generate_docker_section()
        if m["services"]:
            md += self._generate_services_section()

        # Scripts Section
        if m["scripts"]:
            md += "## 📜 Scripts\n| Command | Description |\n|---|---|\n"
            for k, v in m["scripts"].items():
                md += f"| `npm run {k}` | {v} |\n"
            md += "\n"

        # Dependencies Section
        has_deps = any(m["dependencies"].values())
        if has_deps:
            md += "## 📦 Dependencies\n"
            for l in langs:
                if m["dependencies"].get(l):
                    md += f"**{l}**\n"
                    for d in sorted(list(m["dependencies"][l]))[:12]:
                        md += f"- `{d}`\n"
                    md += "\n"

        # Testing Section
        if m["tests"] or m["stats"]["test_files"] > 0:
            md += "## 🧪 Testing\n"
            if m["tests"]:
                md += "Detected testing tools/frameworks:\n\n"
                md += ", ".join(sorted(set(m["tests"]))) + "\n\n"
            if m["stats"]["test_files"] > 0:
                md += f"- Approx. **{m['stats']['test_files']}** test files detected\n\n"

            md += "To run the tests, execute (adjust as needed):\n```bash\n"
            if any(t in m["tests"] for t in ["jest", "mocha"]):
                md += "npm test\n"
            elif "pytest" in m["tests"]:
                md += "pytest\n"
            else:
                # fallback based on language
                if "Node.js" in langs:
                    md += "npm test\n"
                elif "Python" in langs:
                    md += "pytest\n"
                else:
                    md += "# Run your test command here\n"
            md += "```\n\n"

        # Project Health section
        md += self._generate_health_section()

        md += "## 🤝 Contributing\n1. Fork the Project\n2. Create your Feature Branch\n3. Commit your Changes\n4. Push to the Branch\n5. Open a Pull Request\n\n"

        # Next steps suggestions
        md += self._generate_next_steps_section()

        md += f"## 📄 License\nThis project is licensed under the **{m['license']}**."
        return md

    # ---------- Helper section generators ----------

    def _has_tech_stack_details(self):
        d = self.metadata.get("tech_stack_details", {})
        return any(d.get(key) for key in ("frameworks", "databases", "auth", "cache"))

    def _generate_tech_stack_list(self):
        d = self.metadata["tech_stack_details"]
        lines = []
        if d["frameworks"]:
            lines.append(f"- **Frameworks:** " + ", ".join(sorted(d["frameworks"])))
        if d["databases"]:
            lines.append(f"- **Databases:** " + ", ".join(sorted(d["databases"])))
        if d["auth"]:
            lines.append(f"- **Auth:** " + ", ".join(sorted(d["auth"])))
        if d["cache"]:
            lines.append(f"- **Cache:** " + ", ".join(sorted(d["cache"])))
        if not lines:
            return "Languages: " + ", ".join(sorted(self.metadata["languages"])) + "\n"
        return "\n".join(lines) + "\n"

    def _generate_env_section(self):
        envs = sorted(list(self.metadata["env_vars"]))
        if not envs:
            return ""
        md = "## 🔐 Environment Variables\n\n"
        md += "Configure the following environment variables (e.g. in a `.env` file):\n\n"
        md += "```bash\n"
        for v in envs:
            md += f"{v}=\n"
        md += "```\n\n"
        return md

    def _generate_api_section(self):
        eps = self.metadata["api_endpoints"]
        if not eps:
            return ""
        md = "## 📡 API Endpoints (Auto-detected)\n\n"
        for ep in eps:
            md += f"- `{ep}`\n"
        md += "\n> Note: This list is auto-generated and may be incomplete. Please review and update.\n\n"
        return md

    def _generate_docker_section(self):
        d = self.metadata["docker"]
        if not (d["dockerfile"] or d["compose"]):
            return ""
        md = "## 🐳 Docker\n\n"
        if d["dockerfile"]:
            md += "Build and run using Docker:\n\n```bash\ndocker build -t my-app .\ndocker run -p 8000:8000 my-app\n```\n\n"
        if d["compose"]:
            md += "Or using Docker Compose:\n\n```bash\ndocker-compose up --build\n```\n\n"
        return md

    def _generate_services_section(self):
        services = self.metadata["services"]
        if not services:
            return ""
        md = "## 🧩 Services / Packages (Detected)\n\n"
        for s in sorted(services, key=lambda x: x["name"]):
            langs = ", ".join(s["languages"]) if s["languages"] else "Unknown"
            md += f"### `{s['name']}/`\n"
            md += f"- Path: `{s['path']}`\n"
            md += f"- Languages: {langs}\n\n"
        return md

    def _generate_health_section(self):
        stats = self.metadata["stats"]
        md = "## 📊 Project Health Snapshot\n\n"
        files = stats["files"]
        total_files = sum(files.values())
        md += f"- **Code Files (approx):** {total_files}\n"
        for lang, count in files.items():
            if count:
                md += f"  - {lang}: {count}\n"
        md += f"- **Test Files (approx):** {stats['test_files']}\n"
        md += f"- **CI/CD Config:** {'Yes' if stats['has_ci'] else 'Not detected'}\n"
        if stats["linting"]:
            md += "- **Linting/Formatting:** " + ", ".join(sorted(stats["linting"])) + "\n"
        else:
            md += "- **Linting/Formatting:** Not detected\n"
        md += "\n"
        return md

    def _generate_next_steps_section(self):
        m = self.metadata
        stats = m["stats"]
        suggestions = []

        if m["license"] in ["Unlicensed", "See LICENSE file"]:
            suggestions.append("Add a proper LICENSE file (e.g., MIT, Apache 2.0).")
        if stats["test_files"] == 0:
            suggestions.append("Add automated tests (unit/integration) for critical parts.")
        if not stats["has_ci"]:
            suggestions.append("Set up a CI pipeline (GitHub Actions, GitLab CI, etc.).")
        if not m["env_vars"]:
            suggestions.append("Document required environment variables in the README or `.env.example`.")
        if not any(m["dependencies"].values()):
            suggestions.append("Add or document dependency management files (`requirements.txt`, `package.json`, etc.).")

        if not suggestions:
            suggestions.append("Project looks good! Consider improving documentation and adding more examples.")

        md = "## 🔮 Suggested Next Steps (Auto-generated)\n\n"
        for s in suggestions:
            md += f"- [ ] {s}\n"
        md += "\n"
        return md

    # ---------- Installation & Usage ----------

    def _generate_strict_install(self, langs):
        steps = (
            "1. **Clone the repository**\n"
            "   ```bash\n"
            f"   git clone {self.metadata['repo_url']}\n"
            f"   cd {self.metadata['project_name']}\n"
            "   ```\n"
        )

        # Node.js
        if "Node.js" in langs:
            steps += "2. **Node.js Setup**\n   ```bash\n   npm install\n   ```\n"

        # Python
        if "Python" in langs:
            steps += "2. **Python Setup**\n   ```bash\n   python -m venv venv\n   source venv/bin/activate\n"
            req_path = self.metadata.get("python_requirements_path")
            if req_path:
                steps += f"   pip install -r {req_path}\n"
            elif self.metadata["dependencies"]["Python"]:
                steps += "   pip install " + " ".join(
                    list(self.metadata["dependencies"]["Python"])[:5]
                ) + "\n"
            steps += "   ```\n"

        # Java
        if "Java" in langs:
            steps += "2. **Java Setup**\n"
            if "Maven" in self.metadata["build_tools"]:
                steps += "   ```bash\n   mvn clean install\n   ```\n"
            elif "Gradle" in self.metadata["build_tools"]:
                steps += "   ```bash\n   ./gradlew build\n   ```\n"
            else:
                steps += "   ```bash\n   # Raw Java Project: Compile manually\n   javac *.java\n   ```\n"

        # Go
        if "Go" in langs:
            steps += "2. **Go Setup**\n   ```bash\n   go mod tidy\n   ```\n"

        return steps

    def _generate_strict_usage(self, langs):
        cmd = ""

        # Node.js
        if "Node.js" in langs:
            cmd += "**Node.js:**\n"
            if "start" in self.metadata["scripts"]:
                cmd += "```bash\nnpm start\n```\n"
            else:
                entry = self.metadata["entry_points"].get("Node.js") or self.metadata["entry_point"] or "index.js"
                cmd += f"```bash\nnode {entry}\n```\n"

        # Python
        if "Python" in langs:
            cmd += "**Python:**\n"
            entry = self.metadata["entry_points"].get("Python") or self.metadata["entry_point"] or "main.py"
            # Detect FastAPI/Flask specifically for run command
            py_deps = self.metadata["dependencies"]["Python"]
            if "fastapi" in py_deps:
                cmd += f"```bash\nuvicorn {entry.replace('.py','')}:app --reload\n```\n"
            else:
                cmd += f"```bash\npython {entry}\n```\n"

        # Java
        if "Java" in langs:
            cmd += "**Java:**\n"
            if "Maven" in self.metadata["build_tools"]:
                cmd += "```bash\nmvn spring-boot:run\n```\n"
            elif "Gradle" in self.metadata["build_tools"]:
                cmd += "```bash\n./gradlew bootRun\n```\n"
            else:
                entry_cls = self.metadata["entry_point_cmd"]
                entry_file = self.metadata["entry_points"].get("Java") or self.metadata["entry_point"]
                if entry_cls and entry_file:
                    cmd += f"```bash\njavac {entry_file}\njava {entry_cls}\n```\n"
                else:
                    cmd += "```bash\njavac Main.java\njava Main\n```\n"

        # Go
        if "Go" in langs:
            cmd += "**Go:**\n"
            entry = self.metadata["entry_points"].get("Go") or self.metadata["entry_point"] or "main.go"
            cmd += f"```bash\ngo run {entry}\n```\n"

        return cmd


def generate_readme(path, template, context):
    scanner = DeepScanner(path, context)
    try:
        scanner.setup_path()
        scanner.scan()
        return scanner.build_markdown(template)
    finally:
        scanner.cleanup()

#!/usr/bin/env python3
"""
Automated deployment script for WOWA backend (Railway) and frontend (Netlify).
Run this from the **root folder of your backend code** (the same folder containing `api.py` and `core/`).
"""

import os
import subprocess
import sys
import shutil
import time
import json
from pathlib import Path

# ========== CONFIGURATION – CHANGE THESE ==========
GITHUB_USERNAME = "ngoainguqingsong-spec"   # e.g., "lethanhtung"
REPO_NAME = "wowa-backend"                # will be created on GitHub
BACKEND_DIR = "."                          # current folder (contains api.py, core/, storage/)
RAILWAY_PROJECT_NAME = "wowa-backend"      # optional
NETLIFY_SITE_NAME = "wowa-frontend"        # optional
# ==================================================

# Environment variables to set on Railway (key: value)
ENV_VARS = {
    "GROQ_API_KEY": "",          # replace with your actual key, or leave empty to skip
    "OPENAI_API_KEY": "",
    "JWT_SECRET": "change-this-to-a-long-random-string",
    "DATABASE_URL": "",
    "DEBUG": "false",
}

def run_cmd(cmd, cwd=None, check=True, capture=False):
    print(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=capture, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip() if capture else None

def file_exists(path):
    return Path(path).exists()

def create_required_files():
    """Create Procfile, requirements.txt, and frontend/index.html if missing."""
    # Procfile (assumes entry point is api.py with app = FastAPI())
    if not file_exists("Procfile"):
        with open("Procfile", "w") as f:
            f.write("web: uvicorn api:app --host 0.0.0.0 --port $PORT\n")
        print("✅ Created Procfile")
    else:
        print("✅ Procfile already exists")

    # requirements.txt
    if not file_exists("requirements.txt"):
        with open("requirements.txt", "w") as f:
            f.write("""fastapi
uvicorn
pydantic
python-multipart
""")
        print("✅ Created requirements.txt (please review and add any missing packages)")
    else:
        print("✅ requirements.txt already exists")

    # frontend/index.html
    frontend_dir = Path("frontend")
    frontend_dir.mkdir(exist_ok=True)
    index_path = frontend_dir / "index.html"
    if not index_path.exists():
        with open(index_path, "w") as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>WOWA Tool Executor</title>
    <style>
        body { font-family: monospace; max-width: 800px; margin: 2rem auto; padding: 1rem; }
        input, button { font-size: 1rem; padding: 0.5rem; }
        pre { background: #f4f4f4; padding: 1rem; overflow: auto; }
    </style>
</head>
<body>
<h2>WOWA Tool Executor</h2>
<input id="input" placeholder="Enter tool input" size="50"/>
<button onclick="run()">Run</button>
<pre id="out"></pre>

<script>
async function run() {
    const backend = document.getElementById("backend").value;
    const input = document.getElementById("input").value;
    const res = await fetch(backend + "/tool", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ tool: "supoclip", input: input, cloud: false })
    });
    const data = await res.json();
    document.getElementById("out").innerText = JSON.stringify(data, null, 2);
}
</script>
<hr>
<label for="backend">Backend URL (will be updated after Railway deploy):</label>
<input id="backend" value="https://YOUR-BACKEND-URL" size="50" style="margin-top: 1rem;"/>
<p style="font-size: 0.8rem;">After Railway deploy, replace the backend URL above.</p>
</body>
</html>""")
        print("✅ Created frontend/index.html")
    else:
        print("✅ frontend/index.html already exists")

def git_push():
    """Initialize git (if needed), commit, and push to GitHub."""
    if not Path(".git").exists():
        run_cmd("git init")
        print("✅ Git repository initialized")

    run_cmd("git add .")

    try:
        run_cmd("git diff --cached --quiet", check=False)
        if subprocess.call("git diff --cached --quiet", shell=True) != 0:
            run_cmd('git commit -m "Deploy preparation"')
            print("✅ Committed changes")
        else:
            print("ℹ️ No changes to commit")
    except Exception:
        run_cmd('git commit -m "Deploy preparation"', check=False)

    remote_url = f"https://github.com/{GITHUB_USERNAME}/{REPO_NAME}.git"
    try:
        run_cmd("git remote get-url origin", capture=True, check=False)
        run_cmd(f"git remote set-url origin {remote_url}")
    except:
        run_cmd(f"git remote add origin {remote_url}")

    run_cmd("git branch -M main")
    run_cmd(f"git push -u origin main --force")
    print("✅ Code pushed to GitHub")

def create_github_repo():
    result = run_cmd(f"gh repo view {GITHUB_USERNAME}/{REPO_NAME}", capture=True, check=False)
    if "not found" in result or "could not resolve" in result:
        print(f"Creating GitHub repository {GITHUB_USERNAME}/{REPO_NAME}")
        run_cmd(f"gh repo create {REPO_NAME} --public --source=. --remote=origin --push")
    else:
        print("✅ GitHub repository already exists")

def railway_deploy():
    try:
        run_cmd("railway status", capture=True, check=False)
        print("ℹ️ Already linked to a Railway project")
    except:
        run_cmd(f"railway project create {RAILWAY_PROJECT_NAME}", check=False)
        run_cmd(f"railway link --project {RAILWAY_PROJECT_NAME}")

    for key, value in ENV_VARS.items():
        if value:
            run_cmd(f"railway variables set {key}={value}")
        else:
            print(f"⚠️ Skipping empty variable {key}")

    run_cmd("railway up")
    print("✅ Backend deployed on Railway")

def get_railway_url():
    try:
        output = run_cmd("railway status --json", capture=True)
        data = json.loads(output)
        for service in data.get("services", []):
            if service.get("type") == "web":
                return service.get("domains", [])[0]
    except Exception:
        print("⚠️ Could not automatically fetch Railway URL.")
        return input("Please enter the backend URL (e.g., https://your-app.up.railway.app): ").strip()
    return None

def netlify_deploy(frontend_dir="frontend"):
    if not Path("netlify.toml").exists():
        with open("netlify.toml", "w") as f:
            f.write(f"""[build]
  publish = "{frontend_dir}"
""")
        print("✅ Created netlify.toml")
    run_cmd(f"netlify deploy --prod --dir={frontend_dir}")
    print("✅ Frontend deployed on Netlify")

def update_frontend_backend_url(backend_url):
    index_path = Path("frontend/index.html")
    if not index_path.exists():
        return
    content = index_path.read_text()
    if "YOUR-BACKEND-URL" in content:
        new_content = content.replace("YOUR-BACKEND-URL", backend_url)
        index_path.write_text(new_content)
        print(f"✅ Updated frontend backend URL to {backend_url}")
    else:
        print("ℹ️ Frontend backend URL already set")

def main():
    print("🚀 WOWA Auto-Deploy Script\n")
    print("Checking prerequisites...")

    missing = []
    for tool in ["git", "railway", "netlify", "gh"]:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        print(f"❌ Missing tools: {', '.join(missing)}")
        print("Please install them before running this script.")
        sys.exit(1)

    # Check that backend files exist (api.py or core/command_engine.py)
    if not (Path("api.py").exists() or Path("core/command_engine.py").exists()):
        print("❌ Could not find api.py or core/command_engine.py. Make sure you are in the correct folder.")
        sys.exit(1)

    create_required_files()
    create_github_repo()
    git_push()
    railway_deploy()
    print("⏳ Waiting for Railway to finish deployment (20 seconds)...")
    time.sleep(20)

    backend_url = get_railway_url()
    if backend_url:
        print(f"Backend URL: {backend_url}")
    else:
        backend_url = input("Please enter the backend URL: ")

    update_frontend_backend_url(backend_url)
    netlify_deploy()

    print("\n🎉 Deployment complete!")
    print("Your backend is live on Railway. Your frontend is live on Netlify.")
    print("You can find the Netlify URL in the output above (or in Netlify dashboard).")

if __name__ == "__main__":
    main()
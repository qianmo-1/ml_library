import urllib.request, json, base64, ssl
import os

TOKEN = os.environ.get("GITHUB_TOKEN", "")
if not TOKEN:
    raise ValueError("请设置环境变量 GITHUB_TOKEN")

OWNER = os.environ.get("GITHUB_OWNER", "qianmo-1")
REPO = os.environ.get("GITHUB_REPO", "ml_library")
BRANCH = os.environ.get("GITHUB_BRANCH", "main")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(method, path, data=None):
    url = f"https://api.github.com{path}"
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if body:
        req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=15)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        err = json.loads(e.read())
        print(f"  API ERROR: {e.code} - {err.get('message', '?')}")
        return None

# 1. Get current HEAD commit
print("1. Getting current HEAD...")
ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{BRANCH}")
if not ref:
    print("FAILED")
    exit(1)
head_sha = ref["object"]["sha"]
print(f"   HEAD: {head_sha}")

current_commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{head_sha}")
current_tree_sha = current_commit["tree"]["sha"]
print(f"   Tree: {current_tree_sha}")

# 2. Create blob for .gitignore
print("\n2. Creating blob for .gitignore...")
with open(".gitignore", "rb") as f:
    gitignore_content = f.read()

blob_data = {
    "content": base64.b64encode(gitignore_content).decode(),
    "encoding": "base64"
}
blob = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", blob_data)
if not blob:
    exit(1)
gitignore_sha = blob["sha"]
print(f"   Blob: {gitignore_sha}")

# 3. Create a new tree (remove deleted files, add .gitignore)
print("\n3. Creating tree...")
current_tree = api("GET", f"/repos/{OWNER}/{REPO}/git/trees/{current_tree_sha}?recursive=1")
existing = current_tree["tree"]

# Build new tree items - exclude deleted files, add new ones
new_tree_items = []
for item in existing:
    if item["path"] in ["db.sqlite3", "__pycache__/regenerate_chapters.cpython-313.pyc"]:
        print(f"   REMOVE: {item['path']}")
        continue
    new_tree_items.append({
        "path": item["path"],
        "mode": item["mode"],
        "type": item["type"],
        "sha": item["sha"]
    })

# Add .gitignore
new_tree_items.append({
    "path": ".gitignore",
    "mode": "100644",
    "type": "blob",
    "sha": gitignore_sha
})
print(f"   ADD: .gitignore")

tree_data = {"base_tree": current_tree_sha, "tree": new_tree_items}
new_tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", tree_data)
if not new_tree:
    exit(1)
new_tree_sha = new_tree["sha"]
print(f"   New tree: {new_tree_sha}")

# 4. Create commit
print("\n4. Creating commit...")
commit_data = {
    "message": "chore: add .gitignore, remove db.sqlite3 and __pycache__ from tracking",
    "tree": new_tree_sha,
    "parents": [head_sha]
}
new_commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits", commit_data)
if not new_commit:
    exit(1)
new_commit_sha = new_commit["sha"]
print(f"   Commit: {new_commit_sha}")

# 5. Update ref
print("\n5. Updating ref...")
ref_data = {"sha": new_commit_sha, "force": False}
updated = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{BRANCH}", ref_data)
if updated:
    print(f"   SUCCESS! Pushed to {BRANCH}")
else:
    print("   FAILED")
    exit(1)

print("\n=== DONE ===")

"""Build one static shop snapshot per official Dota 2 patch (stdlib only)."""
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SITE = Path(__file__).resolve().parents[1] / "site"
PATCHES = "https://www.dota2.com/datafeed/patchnoteslist?language=english"
CDN = "https://cdn.cloudflare.steamstatic.com"
GROUPS = "consumables attributes weapons_armor misc basics support magics defense weapons artifacts secretshop".split()


def fetch(url):
    if not url.startswith(CDN):
        print("GET", url)
    headers = {"User-Agent": "DotaItemCalculator/1.0"}
    if url.startswith("https://api.github.com/") and os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GH_TOKEN"]
    with urlopen(Request(url, headers=headers), timeout=45) as response:
        return response.read()


def parse_shops(text):
    text = re.sub(r"//[^\n]*|/\*[\s\S]*?\*/", "", text)
    groups = {}
    for group in GROUPS:
        match = re.search(r'"' + group + r'"\s*\{([^{}]*)\}', text)
        if not match:
            raise ValueError("Missing shop group: " + group)
        groups[group] = list(dict.fromkeys(re.findall(r'"item"\s+"item_([a-z0-9_]+)"', match[1])))
        if not groups[group]:
            raise ValueError("Empty shop group: " + group)
    return groups


def validate_items(items, groups):
    keys = list(dict.fromkeys(key for group in groups.values() for key in group))
    for key in keys:
        item = items.get(key, {})
        if not item.get("dname") or not isinstance(item.get("cost"), (int, float)) or item["cost"] < 0 or not item.get("img"):
            raise ValueError("Missing or invalid shop item: " + key)
    return keys


def sync(site=SITE):
    snapshot = site / "data/items.json"
    previous = json.loads(snapshot.read_text(encoding="utf-8")) if snapshot.exists() else {}
    patch = max(json.loads(fetch(PATCHES))["patches"], key=lambda p: p["patch_timestamp"])
    if previous.get("patch") == patch["patch_number"]:
        print("Patch", patch["patch_number"], "unchanged; skipping item data, shops and images.")
        return False
    sources = {"patch": PATCHES}
    for name, repo, path, query in [
        ("items", "odota/dotaconstants", "build/items.json", "&path=build"),
        ("shops", "dotabuff/d2vpkr", "dota/scripts/shops.txt", ""),
    ]:
        commit = json.loads(fetch("https://api.github.com/repos/" + repo + "/commits?per_page=1" + query))[0]
        source_time = datetime.fromisoformat(commit["commit"]["committer"]["date"].replace("Z", "+00:00")).timestamp()
        if source_time < patch["patch_timestamp"]:
            print("Waiting for", repo, "to catch up with patch", patch["patch_number"])
            return False
        sources[name] = "https://raw.githubusercontent.com/" + repo + "/" + commit["sha"] + "/" + path
    items = json.loads(fetch(sources["items"]))
    groups = parse_shops(fetch(sources["shops"]).decode("utf-8"))
    keys = validate_items(items, groups)

    def cache_image(key):
        image_path = site / "assets/items" / (key + ".png")
        if not image_path.exists():
            url = items[key]["img"]
            data = fetch(url if url.startswith("https://") else CDN + url)
            if not data.startswith(b"\x89PNG\r\n\x1a\n"):
                raise ValueError("Invalid PNG for " + key)
            image_path.write_bytes(data)

    (site / "assets/items").mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(cache_image, keys))
    # Keep component names for the detail panel, without carrying unused ability text.
    fields = ("id", "dname", "cost", "components", "qual", "created")
    compact = {key: {field: item[field] for field in fields if field in item} for key, item in items.items()}
    for key in keys:
        compact[key]["img"] = "assets/items/" + key + ".png"
    data = {
        "patch": patch["patch_number"],
        "patchTimestamp": patch["patch_timestamp"],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": sources,
        "count": len(keys), "groups": groups, "items": compact,
    }
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    # Only advance the version after every required item and image is ready.
    temporary = snapshot.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(snapshot)
    print("Published snapshot:", data["patch"], len(keys), "items")
    return True


if __name__ == "__main__":
    changed = sync()
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
            output.write("changed=" + str(changed).lower() + "\n")

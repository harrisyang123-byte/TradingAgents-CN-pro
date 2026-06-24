#!/usr/bin/env python3
"""
Custom X/Twitter feed scraper using CloakBrowser with auth_token.
Authenticated access = full timeline + unlocked accounts + proper timestamps.
Outputs JSON compatible with follow-builders' feed-x.json format.
"""

import argparse
import json
import time
import sys
import os
from datetime import datetime, timezone

USER_CONFIG_PATH = os.path.expanduser("~/.follow-builders/custom-sources.json")
# Output to tradingagents-cn project data/v4/inputs/
_V4_PROJECT = os.environ.get(
    "TRADINGAGENTS_PROJECT_DIR",
    os.path.expanduser("~/AI-Coding-Engine/domains/tradingagents-cn")
)
OUTPUT_PATH = os.path.join(_V4_PROJECT, "data", "v4", "custom-feed-x.json")
STATE_PATH = os.path.expanduser("~/.follow-builders/state-custom-x.json")
ENV_PATH = os.path.expanduser("~/.follow-builders/.env")

DEFAULT_SOURCES = [
    "@dylan522p",
    "@SemiAnalysis_",
    "@tengyanai",
    "@firstadopter",
    "@xingpt",
    "@bitfurygeorge",
    "@lordwilliamuk",
    "@aleabitoreddit",
    "@xiaomustock",
    "@0xxsmart",
    "@degentradinglsd",
    "@LambdaAPI",
    "@CoreWeave",
    "@blockspace",
    "@karpathy",
    "@sama",
    "@kobeissiletter",
    "@bitfool1",
    "@yiqifacai",
    "@bboczeng",
    "@lianyanshe",
    "@tj_research",
]

MAX_TWEETS_PER_USER = 10


def load_json(path, default):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_env(path):
    """Load simple KEY=VALUE .env file"""
    env = {}
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def extract_tweets(page):
    """Extract tweets from authenticated x.com timeline"""
    return page.evaluate("""() => {
        const articles = document.querySelectorAll('article[data-testid="tweet"]');
        if (articles.length === 0) {
            // fallback: any article with a status link
            const allArticles = document.querySelectorAll('article');
            const results = [];
            allArticles.forEach(article => {
                const text = article.innerText || '';
                if (text.length < 30) return;
                const linkEl = article.querySelector('a[href*="/status/"]');
                const url = linkEl ? linkEl.href : '';
                const timeEl = article.querySelector('time');
                const datetime = timeEl ? timeEl.getAttribute('datetime') : '';
                results.push({text: text.slice(0, 600), url: url, datetime: datetime});
            });
            return results;
        }

        const results = [];
        articles.forEach(article => {
            const text = article.innerText || '';
            if (text.length < 30) return;

            const linkEl = article.querySelector('a[href*="/status/"]');
            const url = linkEl ? linkEl.href : '';

            const timeEl = article.querySelector('time');
            const datetime = timeEl ? timeEl.getAttribute('datetime') : '';

            results.push({
                text: text.slice(0, 600),
                url: url,
                datetime: datetime
            });
        });
        return results;
    }""")


def inject_cookies(page, auth_token, ct0):
    """Inject X auth cookies into browser context"""
    cookies = [
        {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/"},
        {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/"},
    ]
    page.context.add_cookies(cookies)


def scrape_user(page, username):
    clean = username.lstrip("@")
    # Use "with_replies" to get the user's own tweets timeline
    url = f"https://x.com/{clean}"
    result = {"name": clean, "username": clean, "bio": "", "tweets": []}

    try:
        page.goto(url, timeout=45000, wait_until="load")
    except Exception:
        pass  # X keeps streaming, wait_until="load" may throw but content is there
    time.sleep(5)

    # Scroll to trigger lazy-rendered timeline content
    try:
        page.evaluate("() => window.scrollBy(0, 600)")
        time.sleep(2)
    except Exception:
        pass

    # Check if account exists / suspended / not found
    try:
        status = page.evaluate("""() => {
            const b = document.body ? document.body.innerText : '';
            if (b.includes('not exist') || b.includes('not found') || b.includes('此账号不存在')) return 'NOT_FOUND';
            if (b.includes('Account suspended') || b.includes('已被冻结')) return 'SUSPENDED';
            return 'OK';
        }""")
        if status == 'NOT_FOUND':
            print(f"  ❌ {clean}: account not found", file=sys.stderr)
            return result
        if status == 'SUSPENDED':
            print(f"  ❌ {clean}: account suspended", file=sys.stderr)
            return result
    except Exception:
        pass

    raw_tweets = extract_tweets(page)
    if not raw_tweets:
        return result

    result["tweets"] = [{
        "text": t.get("text", ""),
        "url": t.get("url", ""),
        "created_at": t.get("datetime", ""),
    } for t in raw_tweets[:MAX_TWEETS_PER_USER]]

    return result


def parse_batch(batch_str, total):
    """Parse '2/3' → (start_idx, end_idx) for slicing sources list."""
    try:
        part, parts = batch_str.split("/")
        part = int(part)
        parts = int(parts)
        if part < 1 or part > parts:
            raise ValueError
        chunk = (total + parts - 1) // parts  # ceiling division
        start = (part - 1) * chunk
        end = min(part * chunk, total)
        return start, end
    except Exception:
        print(f"❌ --batch 格式错误，应为 'N/M'，例如 '1/2'", file=sys.stderr)
        sys.exit(1)


def merge_output(existing_path, new_results, batch_stats, batch_label):
    """Merge batch results into existing output file (or create new)."""
    if os.path.exists(existing_path):
        with open(existing_path) as f:
            existing = json.load(f)
        existing_map = {e["username"]: e for e in existing.get("x", [])}
        for entry in new_results:
            existing_map[entry["username"]] = entry
        merged_x = list(existing_map.values())
        prev_stats = existing.get("stats", {})
        merged_stats = {
            "totalTweets": prev_stats.get("totalTweets", 0) + batch_stats["totalTweets"],
            "newTweets": prev_stats.get("newTweets", 0) + batch_stats["newTweets"],
            "sources": batch_stats["sourcesTotalAll"],
            "sourcesWithContent": len(merged_x),
            "sourcesBlocked": prev_stats.get("sourcesBlocked", 0) + batch_stats["sourcesBlocked"],
            "lastBatch": batch_label,
        }
    else:
        merged_x = new_results
        merged_stats = {
            "totalTweets": batch_stats["totalTweets"],
            "newTweets": batch_stats["newTweets"],
            "sources": batch_stats["sourcesTotalAll"],
            "sourcesWithContent": len(merged_x),
            "sourcesBlocked": batch_stats["sourcesBlocked"],
            "lastBatch": batch_label,
        }
    return merged_x, merged_stats


def main():
    parser = argparse.ArgumentParser(description="Custom X feed scraper")
    parser.add_argument(
        "--batch",
        default=None,
        help="Run a subset of accounts, e.g. '1/2' = first half, '2/2' = second half",
    )
    args_parsed = parser.parse_args()

    from cloakbrowser import launch

    env = load_env(ENV_PATH)
    auth_token = env.get("X_AUTH_TOKEN", "")
    ct0 = env.get("X_CT0_TOKEN", "")

    if not auth_token or not ct0:
        print("❌ 缺少 X auth_token / ct0，请检查 ~/.follow-builders/.env", file=sys.stderr)
        sys.exit(1)

    all_sources = load_json(USER_CONFIG_PATH, {}).get("sources", DEFAULT_SOURCES)
    state = load_json(STATE_PATH, {"seenTweets": {}})
    seen = state["seenTweets"]

    if args_parsed.batch:
        start, end = parse_batch(args_parsed.batch, len(all_sources))
        sources = all_sources[start:end]
        batch_label = args_parsed.batch
        print(f"🔢 Batch {batch_label}: accounts {start+1}–{end} of {len(all_sources)}", file=sys.stderr)
    else:
        sources = all_sources
        batch_label = "full"

    print(f"🚀 CloakBrowser + auth ({len(sources)} accounts)...", file=sys.stderr)
    browser = launch(headless=True, humanize=True)
    context = browser.new_context()
    page = context.new_page()

    # Inject auth cookies before any navigation
    inject_cookies(page, auth_token, ct0)

    results = []
    total = 0
    new = 0
    blocked = 0

    for i, username in enumerate(sources):
        clean = username.lstrip("@")
        print(f"[{i+1}/{len(sources)}] @{clean}...", file=sys.stderr)
        entry = scrape_user(page, clean)
        total += len(entry["tweets"])

        if not entry["tweets"]:
            blocked += 1
            continue

        filtered = []
        for t in entry["tweets"]:
            tid = t.get("url", "")
            if tid and tid in seen:
                continue
            if tid:
                seen[tid] = True
            filtered.append(t)

        new += len(filtered)
        entry["tweets"] = filtered
        if filtered:
            results.append(entry)

        time.sleep(3)  # 3s instead of 1.5s to reduce bot-detection risk

    browser.close()
    save_json(STATE_PATH, state)

    if args_parsed.batch:
        batch_stats = {
            "totalTweets": total,
            "newTweets": new,
            "sourcesBlocked": blocked,
            "sourcesTotalAll": len(all_sources),
        }
        merged_x, merged_stats = merge_output(OUTPUT_PATH, results, batch_stats, batch_label)
        output = {
            "x": merged_x,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "stats": merged_stats,
        }
    else:
        output = {
            "x": results,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "totalTweets": total,
                "newTweets": new,
                "sources": len(all_sources),
                "sourcesWithContent": len(results),
                "sourcesBlocked": blocked,
            },
        }

    save_json(OUTPUT_PATH, output)
    print(f"\n✅ batch={batch_label} | {new} new / {total} total, {len(results)} accounts, {blocked} blocked", file=sys.stderr)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()

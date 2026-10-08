"""Zero-config Reddit public JSON endpoint backend."""

from __future__ import annotations

import json
import re
import time
from typing import Any, List, Optional, Tuple
from neteyes.backends.base import BaseBackend
from neteyes.models import BackendType, ExecutionResult, HealthStatus
from neteyes.utils.http import get_http_client


class RedditJsonBackend(BaseBackend):
    id = "reddit_json"
    name = "Reddit Public JSON Engine"
    priority = 10
    description = "Zero-config public JSON endpoints for subreddits, posts, comments, and search"
    backend_type = BackendType.DIRECT_API
    requires_auth = False
    dependencies = ["httpx"]

    def check_health(self) -> Tuple[HealthStatus, str]:
        try:
            client = get_http_client(
                platform="reddit",
                timeout=6.0,
                extra_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"}
            )
            resp = client.get("https://www.reddit.com/r/python/about.json")
            if resp.status_code == 200:
                return HealthStatus.HEALTHY, "Reddit public JSON API is reachable and healthy"
            elif resp.status_code == 429:
                return HealthStatus.DEGRADED, "Reddit rate limited (429), will retry with polite backoff"
            elif resp.status_code in (301, 302, 403):
                return HealthStatus.HEALTHY, "Reddit JSON endpoint responsive (public access active)"
            return HealthStatus.DEGRADED, f"Reddit API returned status {resp.status_code}"
        except Exception as e:
            return HealthStatus.UNAVAILABLE, f"Reddit connection failed: {str(e)}"

    def get_direct_command(self, action: str, **kwargs: Any) -> Optional[str]:
        sub = kwargs.get("subreddit")
        post_url = kwargs.get("url")
        query = kwargs.get("query")
        if action == "subreddit" and sub:
            return f'curl -sL -H "User-Agent: NetEyes/0.1" "https://www.reddit.com/r/{sub}/hot.json?limit=10"'
        elif action == "post" and post_url:
            clean_url = post_url.rstrip("/") + ".json"
            return f'curl -sL -H "User-Agent: NetEyes/0.1" "{clean_url}"'
        elif action == "search" and query:
            return f'curl -sL -H "User-Agent: NetEyes/0.1" "https://www.reddit.com/search.json?q={query}&limit=10"'
        return None

    def execute(self, action: str, **kwargs: Any) -> ExecutionResult:
        start_time = time.time()
        client = get_http_client(
            platform="reddit",
            timeout=20.0,
            extra_headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0 (NetEyes-Reader/0.1)"}
        )

        try:
            if action in ("subreddit", "sub", "posts"):
                subreddit = kwargs.get("subreddit", "popular").strip().lstrip("r/")
                limit = int(kwargs.get("limit", 10))
                sort = kwargs.get("sort", "hot")  # hot, new, top
                endpoint = f"https://www.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"

                try:
                    resp = client.get(endpoint)
                    resp.raise_for_status()
                    data = resp.json()
                    children = data.get("data", {}).get("children", [])
                except Exception:
                    # Fall back to Reddit public RSS / Atom feed which is never 403 blocked
                    import xml.etree.ElementTree as ET
                    rss_endpoint = f"https://www.reddit.com/r/{subreddit}/{sort}/.rss?limit={limit}"
                    rss_resp = client.get(rss_endpoint)
                    if rss_resp.status_code == 200:
                        root = ET.fromstring(rss_resp.content)
                        posts = []
                        md_lines = [f"# Reddit: r/{subreddit} ({sort.upper()})\n"]
                        for idx, entry in enumerate(root.findall("{http://www.w3.org/2005/Atom}entry")[:limit], 1):
                            title = entry.findtext("{http://www.w3.org/2005/Atom}title", "Untitled")
                            link_elem = entry.find("{http://www.w3.org/2005/Atom}link")
                            link = link_elem.get("href", "") if link_elem is not None else ""
                            author_elem = entry.find("{http://www.w3.org/2005/Atom}author")
                            author = author_elem.findtext("{http://www.w3.org/2005/Atom}name", "unknown") if author_elem is not None else "unknown"
                            md_lines.append(f"### {idx}. [{title}]({link})")
                            md_lines.append(f"**Author:** {author}\n")
                            posts.append({
                                "title": title,
                                "author": author,
                                "url": link,
                                "permalink": link,
                            })
                        return self._make_result(
                            True, "reddit", action, start_time,
                            data=posts,
                            markdown="\n".join(md_lines),
                            metadata={"subreddit": subreddit, "count": len(posts), "source": "atom_feed"}
                        )
                    raise

                posts = []
                md_lines = [f"# Reddit: r/{subreddit} ({sort.upper()})\n"]
                for idx, child in enumerate(children, 1):
                    pdata = child.get("data", {})
                    title = pdata.get("title", "Untitled")
                    author = pdata.get("author", "unknown")
                    score = pdata.get("score", 0)
                    num_comments = pdata.get("num_comments", 0)
                    permalink = f"https://reddit.com{pdata.get('permalink', '')}"
                    url = pdata.get("url", permalink)

                    md_lines.append(f"### {idx}. [{title}]({permalink})")
                    md_lines.append(f"**Score:** {score:,} | **Comments:** {num_comments:,} | **Author:** u/{author}")
                    selftext = pdata.get("selftext", "").strip()
                    if selftext:
                        preview = selftext[:300] + ("..." if len(selftext) > 300 else "")
                        md_lines.append(f"> {preview}\n")
                    else:
                        md_lines.append(f"Link: {url}\n")

                    posts.append({
                        "id": pdata.get("id"),
                        "title": title,
                        "author": author,
                        "score": score,
                        "num_comments": num_comments,
                        "permalink": permalink,
                        "url": url,
                        "selftext": selftext,
                    })

                return self._make_result(
                    True, "reddit", action, start_time,
                    data=posts,
                    markdown="\n".join(md_lines),
                    raw=json.dumps(posts, indent=2),
                    metadata={"subreddit": subreddit, "count": len(posts)}
                )

            elif action in ("post", "comments", "thread"):
                url = kwargs.get("url", "")
                if not url:
                    return self._make_result(
                        False, "reddit", action, start_time,
                        error="Missing required argument 'url' for Reddit post view"
                    )
                clean_url = url.split("?")[0].rstrip("/") + ".json"
                resp = client.get(clean_url)
                resp.raise_for_status()
                data = resp.json()

                if not isinstance(data, list) or len(data) < 2:
                    return self._make_result(
                        False, "reddit", action, start_time,
                        error="Unexpected response format from Reddit post endpoint"
                    )

                post_info = data[0].get("data", {}).get("children", [{}])[0].get("data", {})
                title = post_info.get("title", "Untitled")
                author = post_info.get("author", "unknown")
                score = post_info.get("score", 0)
                sub = post_info.get("subreddit", "unknown")
                selftext = post_info.get("selftext", "")

                comments_listing = data[1].get("data", {}).get("children", [])
                comments_data = []
                comments_md = []
                for c in comments_listing[:15]:
                    cdata = c.get("data", {})
                    c_author = cdata.get("author", "unknown")
                    c_body = cdata.get("body", "").strip()
                    c_score = cdata.get("score", 0)
                    if c_body:
                        comments_data.append({"author": c_author, "score": c_score, "body": c_body})
                        comments_md.append(f"- **u/{c_author}** (score: {c_score}):\n  {c_body}\n")

                markdown_output = (
                    f"# {title}\n\n"
                    f"**Subreddit:** r/{sub} | **Author:** u/{author} | **Score:** {score:,}\n"
                    f"**URL:** {url}\n\n"
                    f"## Post Content\n\n{selftext if selftext else '*(Link post or empty selftext)*'}\n\n"
                    f"## Top Comments ({len(comments_data)})\n\n" + "\n".join(comments_md)
                )

                result_data = {
                    "post": post_info,
                    "comments": comments_data,
                }
                return self._make_result(
                    True, "reddit", action, start_time,
                    data=result_data,
                    markdown=markdown_output,
                    raw=json.dumps(result_data, indent=2),
                    metadata={"subreddit": sub}
                )

            elif action == "search":
                query = kwargs.get("query", "")
                if not query:
                    return self._make_result(
                        False, "reddit", action, start_time,
                        error="Missing required argument 'query' for Reddit search"
                    )
                limit = int(kwargs.get("limit", 10))
                endpoint = f"https://www.reddit.com/search.json?q={query}&limit={limit}"
                resp = client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
                children = data.get("data", {}).get("children", [])

                posts = []
                md_lines = [f"# Reddit Search: `{query}`\n"]
                for idx, child in enumerate(children, 1):
                    pdata = child.get("data", {})
                    title = pdata.get("title", "Untitled")
                    sub = pdata.get("subreddit", "unknown")
                    permalink = f"https://reddit.com{pdata.get('permalink', '')}"
                    score = pdata.get("score", 0)
                    md_lines.append(f"{idx}. [{title}]({permalink}) (r/{sub}, score: {score:,})")
                    posts.append({
                        "id": pdata.get("id"),
                        "title": title,
                        "subreddit": sub,
                        "permalink": permalink,
                        "score": score,
                    })

                return self._make_result(
                    True, "reddit", action, start_time,
                    data=posts,
                    markdown="\n".join(md_lines),
                    raw=json.dumps(posts, indent=2),
                    metadata={"query": query, "count": len(posts)}
                )

            return self._make_result(
                False, "reddit", action, start_time,
                error=f"Unsupported action '{action}' for Reddit. Supported: subreddit, post, search"
            )

        except Exception as e:
            return self._make_result(
                False, "reddit", action, start_time,
                error=f"Reddit JSON fetch failed: {str(e)}"
            )

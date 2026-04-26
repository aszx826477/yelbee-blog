import re
from datetime import datetime
from pathlib import Path

import paramiko


SSH_HOST = "139.129.51.81"
SSH_PORT = 22
SSH_USER = "root"
SSH_PASSWORD = "as!lk@25506216"

MYSQL_USER = "root"
MYSQL_PASSWORD = "aszx25506216"
MYSQL_DB = "typecho"

OUTPUT_DIR = Path(__file__).resolve().parent / "article"
HEXO_POSTS_DIR = Path(__file__).resolve().parents[1] / "hexo-blog" / "source" / "_posts"
FRONT_MATTER_PATTERN = re.compile(
    r"\A(?:\ufeff)?---\r?\n(.*?)\r?\n---(?:\r?\n|$)",
    re.DOTALL,
)


def sanitize_filename(name: str) -> str:
    name = (name or "").strip()
    if not name:
        name = "untitled"
    # Windows illegal filename characters
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.rstrip(". ")
    return name or "untitled"


def unique_path(base_name: str, ext: str, used: set[str]) -> Path:
    candidate = f"{base_name}{ext}"
    index = 2
    while candidate.lower() in used:
        candidate = f"{base_name} ({index}){ext}"
        index += 1
    used.add(candidate.lower())
    return OUTPUT_DIR / candidate


def decode_hex_field(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    return bytes.fromhex(value).decode("utf-8", errors="replace")


def normalize_title(title: str) -> str:
    return (title or "").strip().strip('"\'“”‘’')


def format_created_timestamp(created: int) -> str:
    return datetime.fromtimestamp(created).strftime("%Y-%m-%d %H:%M:%S")


def fetch_posts_via_ssh() -> list[dict]:
    query = (
        "SELECT HEX(IFNULL(title,'')), HEX(IFNULL(text,'')), IFNULL(created, 0) "
        "FROM typecho_contents "
        "WHERE text IS NOT NULL AND text <> ''"
    )

    mysql_cmd = (
        "mysql "
        f"-u{MYSQL_USER} "
        f"-p'{MYSQL_PASSWORD}' "
        f"-D {MYSQL_DB} "
        "--default-character-set=utf8mb4 "
        "-N -B "
        f"-e \"{query}\""
    )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=SSH_HOST,
            port=SSH_PORT,
            username=SSH_USER,
            password=SSH_PASSWORD,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
        )

        stdin, stdout, stderr = client.exec_command(mysql_cmd)
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace").strip()

        if error:
            raise RuntimeError(f"MySQL command failed: {error}")

        posts = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            title = decode_hex_field(parts[0])
            text = decode_hex_field(parts[1])
            try:
                created = int(parts[2])
            except ValueError:
                created = 0
            posts.append({"title": title, "text": text, "created": created})

        return posts
    finally:
        client.close()


def export_posts(posts: list[dict]) -> int:
    used_names: set[str] = set()
    count = 0

    for post in posts:
        title = str(post.get("title") or "untitled")
        text = str(post.get("text") or "")

        base_name = sanitize_filename(title)
        out_path = unique_path(base_name, ".md", used_names)

        out_path.write_text(text, encoding="utf-8")
        count += 1

    return count


def update_front_matter_date(content: str, new_date: str) -> tuple[str, bool]:
    match = FRONT_MATTER_PATTERN.search(content)
    if not match:
        return content, False

    newline = "\r\n" if "\r\n" in content else "\n"
    front_matter_lines = match.group(1).splitlines()

    replaced = False
    for i, line in enumerate(front_matter_lines):
        if re.match(r"^date\s*:\s*", line):
            front_matter_lines[i] = f"date: {new_date}"
            replaced = True
            break

    if not replaced:
        insert_pos = 1 if front_matter_lines else 0
        for i, line in enumerate(front_matter_lines):
            if re.match(r"^title\s*:\s*", line):
                insert_pos = i + 1
                break
        front_matter_lines.insert(insert_pos, f"date: {new_date}")

    suffix = newline if match.group(0).endswith(newline) else ""
    new_front_matter = f"---{newline}{newline.join(front_matter_lines)}{newline}---{suffix}"
    updated_content = content[: match.start()] + new_front_matter + content[match.end() :]
    return updated_content, updated_content != content


def update_hexo_post_dates(posts: list[dict]) -> tuple[int, int]:
    if not HEXO_POSTS_DIR.exists():
        return 0, 0

    created_by_title: dict[str, int] = {}
    for post in posts:
        title = normalize_title(str(post.get("title") or ""))
        created = int(post.get("created") or 0)
        if not title or created <= 0:
            continue
        # 同标题出现多次时保留最早创建时间，避免意外覆盖为较新的版本。
        current = created_by_title.get(title)
        if current is None or created < current:
            created_by_title[title] = created

    matched = 0
    updated = 0

    for md_file in HEXO_POSTS_DIR.glob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        match = FRONT_MATTER_PATTERN.search(content)
        if not match:
            continue

        title = ""
        for line in match.group(1).splitlines():
            title_match = re.match(r"^title\s*:\s*(.*)$", line)
            if title_match:
                title = normalize_title(title_match.group(1))
                break

        if not title:
            continue

        created = created_by_title.get(title)
        if not created:
            continue

        matched += 1
        new_date = format_created_timestamp(created)
        updated_content, changed = update_front_matter_date(content, new_date)
        if changed:
            md_file.write_text(updated_content, encoding="utf-8")
            updated += 1

    return matched, updated


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    posts = fetch_posts_via_ssh()
    exported = export_posts(posts)
    matched, updated = update_hexo_post_dates(posts)
    print(f"Exported {exported} posts to {OUTPUT_DIR}")
    print(f"Matched {matched} Hexo posts, updated {updated} date fields in {HEXO_POSTS_DIR}")


if __name__ == "__main__":
    main()

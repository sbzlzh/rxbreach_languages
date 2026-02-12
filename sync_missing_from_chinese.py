from __future__ import annotations

import argparse
import datetime as dt
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

PREFIX_DECL_RE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*\{\s*\}\s*(?:--.*)?$")


AUTO_APPENDED_HEADER_RE = re.compile(r"^\s*--\s*=====\s*AUTO\s+ADDED\s+FROM\s+chinese\.lua", re.IGNORECASE)

VAR_ASSIGN_RE_TEMPLATE = r"^\s*__PREFIX__(?P<key>(?:\.[A-Za-z_]\w+|\[[^\]]+\])+?)\s*=\s*(?P<rhs>.*)$"
COMMENTED_VAR_ASSIGN_RE_TEMPLATE = r"^\s*--\s*__PREFIX__(?P<key>(?:\.[A-Za-z_]\w+|\[[^\]]+\])+?)\s*=\s*(?P<rhs>.*)$"
DESC_INIT_RE_TEMPLATE = r"^\s*BREACH\.Descriptions\.__PREFIX__\s*=\s*BREACH\.Descriptions\.__PREFIX__\s*or\s*\{\s*\}\s*(?:--.*)?$"
DESC_LINE_RE_TEMPLATE = r"^\s*BREACH\.Descriptions\.__PREFIX__\[(?P<role>[^\]]+)\]\s*=\s*(?P<rhs>.*)$"
ALLLANG_RE_TEMPLATE = r"^\s*ALLLANGUAGES\.__PREFIX__\s*=\s*__PREFIX__\s*(?:--.*)?$"


def detect_prefix(lines: List[str], fallback: str | None = None) -> str:
    for line in lines:
        match = PREFIX_DECL_RE.match(line)
        if match:
            return match.group(1)
    if fallback:
        return fallback
    raise ValueError("无法检测语言前缀（例如 english = {}）")


def count_braces(text: str) -> int:
    return text.count("{") - text.count("}")


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    return ""


def _strip_ending(line: str) -> str:
    return line[:-2] if line.endswith("\r\n") else (line[:-1] if line.endswith("\n") else line)


def replace_lang_tokens(line: str, src_prefix: str, dst_prefix: str) -> str:
    out = line
    out = re.sub(
        rf"\bBREACH\.Descriptions\.{re.escape(src_prefix)}\b",
        f"BREACH.Descriptions.{dst_prefix}",
        out,
    )
    out = re.sub(
        rf"\bALLLANGUAGES\.{re.escape(src_prefix)}\b",
        f"ALLLANGUAGES.{dst_prefix}",
        out,
    )
    out = re.sub(
        rf"(^\s*ALLLANGUAGES\.{re.escape(dst_prefix)}\s*=\s*){re.escape(src_prefix)}\b",
        rf"\1{dst_prefix}",
        out,
    )
    out = re.sub(
        rf"^(\s*(?:--\s*)?){re.escape(src_prefix)}(?=(?:\.|\[))",
        rf"\1{dst_prefix}",
        out,
        count=1,
    )
    return out


def _try_parse_entry(lines: List[str], index: int, prefix: str) -> Tuple[str, List[str], int] | None:
    line = lines[index]
    escaped_prefix = re.escape(prefix)

    var_re = re.compile(VAR_ASSIGN_RE_TEMPLATE.replace("__PREFIX__", escaped_prefix))
    cvar_re = re.compile(COMMENTED_VAR_ASSIGN_RE_TEMPLATE.replace("__PREFIX__", escaped_prefix))
    desc_init_re = re.compile(DESC_INIT_RE_TEMPLATE.replace("__PREFIX__", escaped_prefix))
    desc_line_re = re.compile(DESC_LINE_RE_TEMPLATE.replace("__PREFIX__", escaped_prefix))
    alllang_re = re.compile(ALLLANG_RE_TEMPLATE.replace("__PREFIX__", escaped_prefix))

    match = var_re.match(line)
    if match:
        key = f"var:{match.group('key')}"
        rhs = match.group("rhs").strip()
        block = [line]
        next_index = index + 1
        if rhs.endswith("{"):
            balance = count_braces(rhs)
            while next_index < len(lines) and balance > 0:
                block_line = lines[next_index]
                block.append(block_line)
                balance += count_braces(block_line)
                next_index += 1
        return key, block, next_index

    match = cvar_re.match(line)
    if match:
        key = f"cvar:{match.group('key')}"
        return key, [line], index + 1

    match = desc_line_re.match(line)
    if match:
        key = f"desc:{match.group('role').strip()}"
        return key, [line], index + 1

    if desc_init_re.match(line):
        return "desc_init", [line], index + 1

    if alllang_re.match(line):
        return "alllanguages", [line], index + 1

    return None


def parse_entries(lines: List[str], prefix: str) -> List[Tuple[str, List[str]]]:
    """提取可对齐的语言绑定条目（变量、注释变量、描述文本、ALLLANGUAGES）。"""

    entries: List[Tuple[str, List[str]]] = []
    seen_keys = set()
    index = 0

    while index < len(lines):
        parsed = _try_parse_entry(lines, index, prefix)
        if parsed is None:
            index += 1
            continue

        key, block, next_index = parsed

        if key not in seen_keys:
            entries.append((key, block))
            seen_keys.add(key)

        index = next_index

    return entries


TemplateItem = Tuple[str, str, List[str]]


def parse_template(lines: List[str], prefix: str) -> List[TemplateItem]:
    """按基准文件顺序解析出模板项：raw 行 or entry(含多行表块)。

    返回的 item 结构为：
    - ("raw", "", [line])
    - ("entry", key, block_lines)
    """
    items: List[TemplateItem] = []
    index = 0
    while index < len(lines):
        parsed = _try_parse_entry(lines, index, prefix)
        if parsed is None:
            items.append(("raw", "", [lines[index]]))
            index += 1
            continue

        key, block, next_index = parsed
        items.append(("entry", key, block))
        index = next_index

    return items


def replace_prefix(line: str, src_prefix: str, dst_prefix: str) -> str:
    return replace_lang_tokens(line, src_prefix, dst_prefix)


def normalize_lines(text: str) -> List[str]:
    return text.splitlines(keepends=True)


def strip_auto_appended_section(lines: List[str]) -> List[str]:
    """移除旧脚本追加的末尾区块，避免把“自动补齐的中文占位”当成真实翻译。"""
    for idx, line in enumerate(lines):
        if AUTO_APPENDED_HEADER_RE.match(line):
            return lines[:idx]
    return lines


def transform_prefix_declaration(line: str, src_prefix: str, dst_prefix: str) -> str:
    match = PREFIX_DECL_RE.match(line)
    if not match:
        return line

    ending = _line_ending(line)
    stripped = _strip_ending(line)
    indent_match = re.match(r"^(\s*)", stripped)
    indent = indent_match.group(1) if indent_match else ""
    return f"{indent}{dst_prefix} = {{}}{ending}"


def comment_block(block: List[str], src_prefix: str, dst_prefix: str) -> List[str]:
    out: List[str] = []
    for original_line in block:
        ending = _line_ending(original_line)
        content = _strip_ending(original_line)
        if content.strip() == "":
            out.append(original_line)
            continue

        content = replace_lang_tokens(content + ending, src_prefix, dst_prefix)
        ending = _line_ending(content)
        content = _strip_ending(content)

        ws_match = re.match(r"^(\s*)", content)
        indent = ws_match.group(1) if ws_match else ""
        rest = content[len(indent) :]

        out.append(f"{indent}-- {rest}{ending}")

    return out


def build_missing_patch(
    base_entries: List[Tuple[str, List[str]]],
    existing_keys: set[str],
    src_prefix: str,
    dst_prefix: str,
    note: str,
) -> List[str]:
    patch_lines: List[str] = []
    missing_count = 0

    for key, source_block in base_entries:
        if key in existing_keys:
            continue

        missing_count += 1
        patch_lines.append(f"-- {note}: {key}\n")

        first_line = replace_prefix(source_block[0], src_prefix, dst_prefix)
        patch_lines.append(first_line)
        if len(source_block) > 1:
            patch_lines.extend(source_block[1:])

    if not patch_lines:
        return []

    today = dt.date.today().isoformat()
    header = [
        "\n",
        f"-- ===== AUTO ADDED FROM chinese.lua ({today}) =====\n",
    ]
    return header + patch_lines


def rebuild_from_template(
    base_lines: List[str],
    target_lines: List[str],
    note: str,
) -> Tuple[List[str], int, int, int]:
    """使用 chinese.lua 的结构/顺序重建目标文件。

    - 已存在的 key：保持目标文件原行块（前提是行块长度与模板一致）
    - 缺失的 key：输出同等行数的注释占位（prefix 替换为目标 prefix）
    - 多余的 key：不输出（等价于删除）
    """
    base_prefix = detect_prefix(base_lines, fallback="chinese")
    target_prefix = detect_prefix(target_lines)

    base_template = parse_template(base_lines, base_prefix)
    base_keys = [key for kind, key, _ in base_template if kind == "entry"]
    base_key_set = set(base_keys)

    target_lines = strip_auto_appended_section(target_lines)
    target_entries = parse_entries(target_lines, target_prefix)
    target_map: Dict[str, List[str]] = {key: block for key, block in target_entries}
    target_key_set = set(target_map.keys())

    missing = 0
    removed = len(target_key_set - base_key_set)
    mismatched = 0

    output: List[str] = []

    for kind, key, block in base_template:
        if kind == "raw":
            line = block[0]
            output.append(replace_lang_tokens(transform_prefix_declaration(line, base_prefix, target_prefix), base_prefix, target_prefix))
            continue

        # entry
        existing = target_map.get(key)
        if existing is None:
            missing += 1
            output.extend(comment_block(block, base_prefix, target_prefix))
            continue

        if len(existing) != len(block):
            mismatched += 1
            output.extend(
                comment_block(block, base_prefix, target_prefix)
            )
            continue

        output.extend(existing)

    return output, missing, removed, mismatched


def process_one_file_append(
    base_path: Path,
    target_path: Path,
    note: str,
    dry_run: bool,
) -> Tuple[int, int]:
    base_lines = normalize_lines(base_path.read_text(encoding="utf-8"))
    target_lines = normalize_lines(target_path.read_text(encoding="utf-8"))

    src_prefix = detect_prefix(base_lines, fallback="chinese")
    dst_prefix = detect_prefix(target_lines)

    base_entries = parse_entries(base_lines, src_prefix)
    target_entries = parse_entries(target_lines, dst_prefix)

    existing_keys = {key for key, _ in target_entries}
    patch_lines = build_missing_patch(base_entries, existing_keys, src_prefix, dst_prefix, note)

    if not patch_lines:
        return (0, 0)

    missing_added = sum(1 for line in patch_lines if line.startswith(f"-- {note}: "))

    if dry_run:
        return (missing_added, 0)

    output = "".join(target_lines + patch_lines)
    target_path.write_text(output, encoding="utf-8")
    return (missing_added, len(patch_lines))


def process_one_file_template(
    base_path: Path,
    target_path: Path,
    note: str,
    dry_run: bool,
) -> Tuple[int, int, int, int]:
    base_lines = normalize_lines(base_path.read_text(encoding="utf-8"))
    target_lines = normalize_lines(target_path.read_text(encoding="utf-8"))

    output, missing, removed, mismatched = rebuild_from_template(base_lines, target_lines, note)

    if dry_run:
        return missing, removed, mismatched, 0

    target_path.write_text("".join(output), encoding="utf-8")
    return missing, removed, mismatched, len(output)


def find_default_targets(folder: Path, base_name: str) -> List[Path]:
    targets = []
    for path in sorted(folder.glob("*.lua")):
        if path.name == base_name:
            continue
        targets.append(path)
    return targets


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "以 chinese.lua 为基准同步其他语言文件。默认按模板顺序重建文件："
            "保持已有翻译行块，缺失项用同等行数的注释占位，多余项删除。"
        )
    )
    parser.add_argument("--dir", default=".", help="语言文件目录，默认当前目录")
    parser.add_argument("--base", default="chinese.lua", help="基准文件名，默认 chinese.lua")
    parser.add_argument(
        "--targets",
        nargs="*",
        default=None,
        help="指定目标文件名（可多个）。不传则自动处理目录内所有 .lua（排除 base）。",
    )
    parser.add_argument(
        "--note",
        default="缺失补齐",
        help="新增行注释前缀文本，默认：缺失补齐",
    )
    parser.add_argument(
        "--mode",
        choices=["template", "append"],
        default="template",
        help="同步模式：template=按基准顺序重建(推荐)；append=仅在末尾追加缺失键(旧模式)",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅显示将补齐的数量，不写文件")

    args = parser.parse_args()
    folder = Path(args.dir).resolve()
    base_path = folder / args.base

    if not base_path.exists():
        raise FileNotFoundError(f"未找到基准文件: {base_path}")

    if args.targets:
        targets = [folder / item for item in args.targets]
    else:
        targets = find_default_targets(folder, args.base)

    if not targets:
        print("没有找到可处理的目标文件。")
        return

    total_missing = 0
    total_removed = 0
    total_mismatched = 0
    for target in targets:
        if not target.exists():
            print(f"[跳过] 文件不存在: {target.name}")
            continue

        if args.mode == "append":
            added, written_lines = process_one_file_append(
                base_path=base_path,
                target_path=target,
                note=args.note,
                dry_run=args.dry_run,
            )
            total_missing += added
            if args.dry_run:
                print(f"[DRY-RUN] {target.name}: 将在末尾补齐 {added} 项")
            else:
                print(f"[OK] {target.name}: 已在末尾补齐 {added} 项，写入 {written_lines} 行")
            continue

        missing, removed, mismatched, written_lines = process_one_file_template(
            base_path=base_path,
            target_path=target,
            note=args.note,
            dry_run=args.dry_run,
        )
        total_missing += missing
        total_removed += removed
        total_mismatched += mismatched

        if args.dry_run:
            print(
                f"[DRY-RUN] {target.name}: 缺失占位 {missing} 项，移除多余 {removed} 项，结构不一致 {mismatched} 项"
            )
        else:
            print(
                f"[OK] {target.name}: 缺失占位 {missing} 项，移除多余 {removed} 项，结构不一致 {mismatched} 项，写入 {written_lines} 行"
            )

    if args.mode == "append":
        if args.dry_run:
            print(f"\n总计将补齐(末尾追加): {total_missing} 项")
        else:
            print(f"\n总计已补齐(末尾追加): {total_missing} 项")
        return

    if args.dry_run:
        print(
            f"\n总计：缺失占位 {total_missing} 项；移除多余 {total_removed} 项；结构不一致 {total_mismatched} 项"
        )
    else:
        print(
            f"\n总计：缺失占位 {total_missing} 项；移除多余 {total_removed} 项；结构不一致 {total_mismatched} 项"
        )


if __name__ == "__main__":
    main()

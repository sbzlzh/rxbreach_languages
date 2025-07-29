import re

# Define regular expressions to match different components
comment_pattern = r'--\s(.+)'  # 注释
lang_pattern = r'([a-zA-Z0-9_]+)\s*=\s*\{'  # 语言声明，如 english = {

# 后续正则动态替换 {prefix} 为当前语言变量名
singleline_text_pattern_fmt = r'{prefix}([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*"((?:\\"|[^"])*)"'
multiline_text_pattern_open_fmt = r'{prefix}([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\[\[([^\]]*)'
multiline_text_pattern_close = r'(.*?)\]\]'
multiline_single_line_fmt = r'{prefix}([a-zA-Z_][a-zA-Z_0-9]*)\s*=\s*\[\[(.*?)\]\]'
text_param_pattern = r'{([^{}]+)}'

def loadfile(path):
    lines = []
    data = []
    lang_var = None  # 比如 english 或 chinese

    with open(path, "r", encoding="utf-8") as file:
        try:
            lines = file.readlines()
        except UnicodeDecodeError:
            print("ERROR: " + path)
            return

    line_counter = 0
    is_multiline = False

    for line in lines:
        line = line.strip()

        # 匹配 language 名称，如 english = {
        lang_match = re.match(lang_pattern, line)
        if lang_match:
            lang_var = lang_match.group(1)
            data.append({
                "type": "code",
                "identifier": "local",
                "content": line
            })
            line_counter += 1
            continue

        # 注释
        comment_match = re.match(comment_pattern, line)
        if comment_match:
            data.append({
                "type": "comment",
                "content": comment_match.group(1)
            })
            line_counter += 1
            continue

        if not lang_var:
            continue  # 未找到语言变量前缀则跳过

        # 动态构造正则
        prefix = re.escape(lang_var) + r'\.'  # 如 english\.lang_xx
        singleline_text_pattern = singleline_text_pattern_fmt.format(prefix=prefix)
        multiline_text_pattern_open = multiline_text_pattern_open_fmt.format(prefix=prefix)
        multiline_single_line = multiline_single_line_fmt.format(prefix=prefix)

        # 单行字符串
        singleline_text_match = re.search(singleline_text_pattern, line)
        if singleline_text_match and line[0:2] != "--":
            data.append({
                "type": "single",
                "identifier": singleline_text_match.group(1),
                "content": singleline_text_match.group(2)
            })
            data[line_counter]["params"] = re.findall(text_param_pattern, data[line_counter]["content"])
            line_counter += 1
            continue

        # 多行但在一行内
        multisingleline_text_match = re.search(multiline_single_line, line)
        if multisingleline_text_match and line[0:2] != "--":
            data.append({
                "type": "multi",
                "identifier": multisingleline_text_match.group(1),
                "content": multisingleline_text_match.group(2)
            })
            data[line_counter]["params"] = re.findall(text_param_pattern, data[line_counter]["content"])
            line_counter += 1
            continue

        # 多行字符串开始
        multiline_text_match_open = re.search(multiline_text_pattern_open, line)
        if multiline_text_match_open and line[0:2] != "--":
            data.append({
                "type": "multi",
                "identifier": multiline_text_match_open.group(1),
                "content": multiline_text_match_open.group(2)
            })
            is_multiline = True
            continue

        # 多行字符串结束
        multiline_text_match_close = re.search(multiline_text_pattern_close, line)
        if multiline_text_match_close and line[0:2] != "--":
            data[line_counter]["content"] += "\n" + multiline_text_match_close.group(1)
            data[line_counter]["params"] = re.findall(text_param_pattern, data[line_counter]["content"])
            line_counter += 1
            is_multiline = False
            continue

        # 正在处理多行内容中间部分
        if is_multiline and line[0:2] != "--":
            data[line_counter]["content"] += "\n" + line
            continue

        # 其余认为是空行
        data.append({
            "type": "empty",
            "content": ""
        })
        line_counter += 1

    return data

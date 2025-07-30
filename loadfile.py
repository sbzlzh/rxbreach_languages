import re

comment_pattern = r'--\s(.+)'
lang_pattern = r'([a-zA-Z0-9_]+)\s*=\s*\{'
empty_line_pattern = r'^\s*$'

# 匹配各种赋值形式
assignment_patterns = [
    # 简单赋值: english.field = "value"
    r'([a-zA-Z0-9_\.]+)\s*=\s*"((?:\\"|[^"])*)"',
    # 简单赋值(多行): english.field = [[value]]
    r'([a-zA-Z0-9_\.]+)\s*=\s*\[\[(.*?)\]\]',
    # 索引赋值: english["field"] = "value"
    r'([a-zA-Z0-9_]+)\["([^"]+)"\]\s*=\s*"((?:\\"|[^"])*)"',
    # 索引赋值(多行): english["field"] = [[value]]
    r'([a-zA-Z0-9_]+)\["([^"]+)"\]\s*=\s*\[\[(.*?)\]\]',
    # 点索引赋值: table.field.subfield = "value"
    r'([a-zA-Z0-9_\.]+)\["([^"]+)"\]\s*=\s*"((?:\\"|[^"])*)"',
    # 点索引赋值(多行): table.field.subfield["key"] = [[value]]
    r'([a-zA-Z0-9_\.]+)\["([^"]+)"\]\s*=\s*\[\[(.*?)\]\]',
    # 全局表赋值: BREACH.Descriptions.english[role.SCI] = "value"
    r'([a-zA-Z0-9_\.]+)\[([^\]]+)\]\s*=\s*"((?:\\"|[^"])*)"',
    # 全局表赋值(多行): BREACH.Descriptions.english[role.SCI] = [[value]]
    r'([a-zA-Z0-9_\.]+)\[([^\]]+)\]\s*=\s*\[\[(.*?)\]\]',
    # 完整表赋值: english = { ... }
    r'([a-zA-Z0-9_]+)\s*=\s*\{'
]

text_param_pattern = r'{([^{}]+)}'

def loadfile(path):
    data = []
    lang_var = None
    current_table = None
    table_stack = []
    in_multiline = False
    multiline_content = []
    multiline_identifier = None
    multiline_type = None

    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except Exception as e:
        print(f"ERROR loading {path}: {str(e)}")
        return None

    for line_num, line in enumerate(lines):
        raw_line = line
        line = line.strip()
        
        # 跳过空行
        if re.match(empty_line_pattern, line):
            data.append({"type": "empty", "content": ""})
            continue
            
        # 处理注释
        comment_match = re.match(comment_pattern, line)
        if comment_match:
            data.append({"type": "comment", "content": comment_match.group(1)})
            continue

        # 处理多行字符串结束
        if in_multiline:
            end_match = re.search(r'(.*?)\]\]', line)
            if end_match:
                in_multiline = False
                multiline_content.append(end_match.group(1))
                content = "\n".join(multiline_content)
                
                # 创建多行条目
                entry = {
                    "type": "multi",
                    "identifier": multiline_identifier,
                    "content": content,
                    "params": re.findall(text_param_pattern, content)
                }
                data.append(entry)
                multiline_content = []
                multiline_identifier = None
            else:
                multiline_content.append(line)
            continue

        # 尝试匹配各种赋值模式
        matched = False
        for pattern in assignment_patterns:
            match = re.search(pattern, raw_line)
            if match:
                groups = match.groups()
                identifier = None
                value = None
                assign_type = "single"
                
                # 根据不同模式提取标识符和值
                if pattern == assignment_patterns[0]:  # 简单赋值
                    identifier = groups[0]
                    value = groups[1]
                elif pattern == assignment_patterns[1]:  # 多行简单赋值
                    identifier = groups[0]
                    value = groups[1]
                    assign_type = "multi"
                elif pattern in (assignment_patterns[2], assignment_patterns[4], assignment_patterns[6]):  # 索引赋值
                    identifier = f"{groups[0]}['{groups[1]}']"
                    value = groups[2]
                elif pattern in (assignment_patterns[3], assignment_patterns[5], assignment_patterns[7]):  # 多行索引赋值
                    identifier = f"{groups[0]}['{groups[1]}']"
                    value = groups[2]
                    assign_type = "multi"
                elif pattern == assignment_patterns[8]:  # 完整表赋值
                    identifier = groups[0]
                    value = None
                    assign_type = "table_start"
                
                # 处理多行字符串开始
                if assign_type == "multi" and not value.endswith("]]"):
                    in_multiline = True
                    multiline_identifier = identifier
                    multiline_content = [value]
                    matched = True
                    break
                
                # 创建条目
                if assign_type == "table_start":
                    data.append({
                        "type": "code",
                        "identifier": identifier,
                        "content": raw_line.strip()
                    })
                    # 开始新表
                    current_table = identifier
                    table_stack.append(current_table)
                elif value is not None:
                    data.append({
                        "type": assign_type,
                        "identifier": identifier,
                        "content": value,
                        "params": re.findall(text_param_pattern, value)
                    })
                matched = True
                break
        
        # 表结束检测
        if not matched and "}" in line and table_stack:
            current_table = table_stack.pop()
            data.append({
                "type": "code",
                "identifier": current_table,
                "content": raw_line.strip()
            })
            matched = True
        
        # 未匹配任何模式，视为代码行
        if not matched and line:
            data.append({
                "type": "code",
                "content": raw_line.strip()
            })
    
    # 处理未结束的多行字符串
    if in_multiline:
        content = "\n".join(multiline_content)
        data.append({
            "type": "multi",
            "identifier": multiline_identifier,
            "content": content,
            "params": re.findall(text_param_pattern, content)
        })
    
    return data
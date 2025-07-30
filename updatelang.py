import re

def getelement(haystack, needle):
    for line in haystack:
        try:
            if "identifier" in line and line["identifier"] == needle:
                return line
        except KeyError:
            continue
    return None

def getaliasline(array):
    for i, line in enumerate(array):
        if line["type"] == "single" and "identifier" in line and line["identifier"] == "__alias":
            return i
    for i, line in enumerate(array):
        if line["type"] in ["single", "multi"] and "identifier" in line:
            return i
    return 0

def extract_lang_var(array):
    for line in array:
        if line["type"] == "code":
            try:
                prefix = line["content"].split("=")[0].strip()
                return prefix
            except:
                pass
    return "L"

def updatelang(base, update, lang_file):
    newlang = []
    lang_var = extract_lang_var(update)
    base_var = extract_lang_var(base)  # 获取基础语言变量名 (如 'english')
    
    # 复制头部注释和代码
    for i in range(0, getaliasline(update)):
        line = update[i]
        if line["type"] == "comment" or line["type"] == "empty":
            newlang.append("-- " + line["content"] + "\n" if line["content"] != "" else "\n")
        elif line["type"] == "code":
            newlang.append(line["content"] + "\n")
    
    # 处理表结构
    in_table = False
    current_table = None
    
    for i in range(getaliasline(base), len(base)):
        line = base[i]
        
        # 处理注释和空行
        if line["type"] == "comment" or line["type"] == "empty":
            newlang.append("-- " + line["content"] + "\n" if line["content"] != "" else "\n")
            continue
        
        # 检测表开始
        if line["type"] == "code" and "{" in line["content"]:
            in_table = True
            # 替换基础语言变量为目标语言变量
            table_line = line["content"].replace(f"{base_var}.", f"{lang_var}.").replace(f"{base_var}[", f"{lang_var}[")
            newlang.append(table_line + "\n")
            continue
        
        # 检测表结束
        if in_table and line["type"] == "code" and "}" in line["content"]:
            in_table = False
            newlang.append(line["content"] + "\n")
            continue
        
        # 处理表中的内容
        if in_table:
            # 保持表内容不变
            newlang.append(line["content"] + "\n")
            continue
        
        # 检查是否有identifier键
        if "identifier" not in line:
            # 直接复制代码行
            newlang.append(line["content"] + "\n")
            continue
        
        # 处理普通文本行
        transline = getelement(update, line["identifier"])
        
        if transline is not None:
            # 参数检查
            base_params = set(line.get("params", []))
            trans_params = set(transline.get("params", []))
            
            missing_params = base_params - trans_params
            extra_params = trans_params - base_params
            
            if missing_params:
                print(f"[ERROR] in {lang_file}: missing param(s) in translation: {transline['identifier']}")
                print(" - reference:   " + line["content"].replace("\n", " /// "))
                print(" - translation: " + transline["content"].replace("\n", " /// "))
                print(" - missing:     " + str(list(missing_params)))
                print()
            
            if extra_params:
                print(f"[WARNING] in {lang_file}: extra param(s) in translation: {transline['identifier']}")
                print(" - reference:   " + line["content"].replace("\n", " /// "))
                print(" - translation: " + transline["content"].replace("\n", " /// "))
                print(" - extra:       " + str(list(extra_params)))
                print()
            
            # 替换基础语言变量为目标语言变量
            if line["type"] == "single":
                content = transline["content"].replace(f"{base_var}.", f"{lang_var}.")
                newlang.append(f"{lang_var}.{transline['identifier']} = \"{content}\"\n")
            else:
                content = transline["content"].replace(f"{base_var}.", f"{lang_var}.")
                newlang.append(f"{lang_var}.{transline['identifier']} = [[{content}]]\n")
        else:
            # 未翻译的行 - 添加注释
            if line["type"] == "single":
                content = line["content"].replace(f"{base_var}.", f"{lang_var}.")
                newlang.append(f"-- {lang_var}.{line['identifier']} = \"{content}\"\n")
            else:
                content = line["content"].replace(f"{base_var}.", f"{lang_var}.")
                newlang.append(f"-- {lang_var}.{line['identifier']} = [[{content}]]\n")
    
    return newlang
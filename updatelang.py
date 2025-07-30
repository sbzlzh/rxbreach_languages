def getelement(haystack, needle):
	for line in haystack:
		try:
			if line["identifier"] == needle:
				return line
		except KeyError:
			continue

def getaliasline(array):
	for i, line in enumerate(array):
		if line["type"] == "single" and line["identifier"] == "__alias":
			return i
	# fallback: first value line
	for i, line in enumerate(array):
		if line["type"] in ["single", "multi"]:
			return i
	return 0

def extract_lang_var(array):
	for line in array:
		if line["type"] == "code":
			try:
				# e.g., english = {
				prefix = line["content"].split("=")[0].strip()
				return prefix
			except:
				pass
	return "L"  # fallback

def updatelang(base, update, lang_file):
	newlang = []
	lang_var = extract_lang_var(update)  # e.g., english / chinese / traditional

	# copy header from old file
	for i in range(0, getaliasline(update)):
		line = update[i]

		if line["type"] == "comment" or line["type"] == "empty":
			newlang.append("-- " + line["content"] + "\n" if line["content"] != "" else "\n")
			continue

		if line["type"] == "code":
			newlang.append(line["content"] + "\n")

	for i in range(getaliasline(base), len(base)):
		line = base[i]

		if line["type"] == "comment" or line["type"] == "empty":
			newlang.append("-- " + line["content"] + "\n" if line["content"] != "" else "\n")
			continue

		transline = getelement(update, line["identifier"])

		if transline is not None:
			in_base_not_in_trans = [p for p in line["params"] if p not in transline["params"]]
			in_trans_not_in_base = [p for p in transline["params"] if p not in line["params"]]

			if in_base_not_in_trans:
				print(f"[ERROR] in {lang_file}: missing param(s) in translation: {transline['identifier']}")
				print(" - reference:   " + line["content"].replace("\n", " /// "))
				print(" - translation: " + transline["content"].replace("\n", " /// "))
				print(" - missing:     " + str(in_base_not_in_trans))
				print()

			if in_trans_not_in_base:
				print(f"[ERROR] in {lang_file}: unused param(s) in translation: {transline['identifier']}")
				print(" - reference:   " + line["content"].replace("\n", " /// "))
				print(" - translation: " + transline["content"].replace("\n", " /// "))
				print(" - unused:      " + str(in_trans_not_in_base))
				print()

			if line["type"] == "single":
				newlang.append(f"{lang_var}.{transline['identifier']} = \"{transline['content']}\"\n")
			else:
				newlang.append(f"{lang_var}.{transline['identifier']} = [[{transline['content']}]]\n")

		else:
			# not yet translated — keep original text as commented line
			if line["type"] == "single":
				newlang.append(f"-- {lang_var}.{line['identifier']} = \"{line['content']}\"\n")
			else:
				newlang.append(f"-- {lang_var}.{line['identifier']} = [[{line['content']}]]\n")

	return newlang

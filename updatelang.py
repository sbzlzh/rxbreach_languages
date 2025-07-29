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

def updatelang(base, update, lang_file):
	newlang = []

	# first: copy header from old file
	for i in range(0, getaliasline(update)):
		line = update[i]

		if line["type"] == "comment" or line["type"] == "empty":
			if line["content"] != "":
				newlang.append("-- " + line["content"] + "\n")
			else:
				newlang.append("\n")

			continue

		if line["type"] == "code":
			newlang.append(line["content"] + "\n")

	for i in range(getaliasline(base), len(base)):
		line = base[i]

		if line["type"] == "comment" or line["type"] == "empty":
			if line["content"] != "":
				newlang.append("-- " + line["content"] + "\n")
			else:
				newlang.append("\n")

			continue

		# element is already translated
		transline = getelement(update, line["identifier"])

		if transline != None:
			in_base_not_in_trans = [param for param in line["params"] if param not in transline["params"]]
			in_trans_not_in_base = [param for param in transline["params"] if param not in line["params"]]

			if len(in_base_not_in_trans):
				print("[ERROR] in " + lang_file + ": " + str(len(in_base_not_in_trans)) + " missing param(s) in traslation string with the following identifier: " + transline["identifier"])
				print("[ERROR] - reference:   " + line["content"].replace("\n", " /// "))
				print("[ERROR] - translation: " + transline["content"].replace("\n", " /// "))
				print("[ERROR] - missing:     " + str(in_base_not_in_trans))
				print("")

			if len(in_trans_not_in_base):
				print("[ERROR] in " + lang_file + ": " + str(len(in_trans_not_in_base)) + " unused param(s) in traslation string with the following identifier: " + transline["identifier"])
				print("[ERROR] - reference:   " + line["content"].replace("\n", " /// "))
				print("[ERROR] - translation: " + transline["content"].replace("\n", " /// "))
				print("[ERROR] - unused:      " + str(in_trans_not_in_base))
				print("")

			if line["type"] == "single":
				newlang.append("L." + transline["identifier"] + " = \"" + transline["content"] + "\"\n")
			else:
				newlang.append("L." + transline["identifier"] + " = [[" + transline["content"] + "]]\n")
		else:
			if line["type"] == "single":
				newlang.append("--L." + line["identifier"] + " = \"" + line["content"] + "\"\n")
			else:
				sanitized = line["content"].replace("\n", "\n--")

				newlang.append("--L." + line["identifier"] + " = [[" + sanitized + "]]\n")

	return newlang
			
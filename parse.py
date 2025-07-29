import argparse, os

import loadfile, updatelang

parser = argparse.ArgumentParser("parse language files")
parser.add_argument("--in", help="A path to the input folder", type=str, dest="input")
parser.add_argument("--out", help="A path to the output folder", type=str, dest="output")
parser.add_argument("--base", help="The name of the base language", type=str)
parser.add_argument("--ignore", help="Ignore the given file", type=str, nargs="+")
args = parser.parse_args()

lang_file_list = os.listdir(args.input)
base_file = args.base + ".lua"
base_file_path = args.input + "/" + base_file

if not base_file in lang_file_list:
	print("Basefile not found. Ending")
	exit()

baselang = loadfile.loadfile(base_file_path)

if not baselang:
	exit()

for lang_file in lang_file_list:
	if lang_file == base_file:
		continue

	if args.ignore and lang_file.split(".")[0] in args.ignore:
		continue

	lang = loadfile.loadfile(args.input + "/" + lang_file)

	if not lang:
		continue

	new_lang = updatelang.updatelang(baselang, lang, lang_file)
	f = open(args.output + "/" + lang_file, "w", encoding="utf-8")

	for line in new_lang:
		f.write(line)

	f.close()

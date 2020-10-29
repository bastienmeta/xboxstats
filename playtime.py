from requests import get
import sys
import json
from os import path, listdir
from slugify import slugify
import time
from matplotlib import pyplot as plt
import numpy as np
from skimage import color
import seaborn as sns

UPDATE_GAME_LIST = False
UPDATE_ONE_DATA = False
UPDATE_360_DATA = False

xauth = "4412c4ce9676b6e1ab6fbe1a497b5b973accdf58"
HEADER = {"X-AUTH": xauth}

if UPDATE_GAME_LIST:
	url_xboxone = "https://xapi.us/v2/2759124950288873/xboxonegames"
	url_xbox360 = "https://xapi.us/v2/2759124950288873/xbox360games"

	resp_one = get(url_xboxone, headers=HEADER)
	resp_360 = get(url_xbox360, headers=HEADER)

	RAW_DATA_ONE = resp_one.json()
	RAW_DATA_360 = resp_360.json()

	with open("one_data.json", 'w') as f:
		json.dump(RAW_DATA_ONE, f)

	with open("360_data.json", 'w') as f:
		json.dump(RAW_DATA_360, f)
else:
	with open("one_data.json") as f:
		RAW_DATA_ONE = json.load(f)

	with open("360_data.json") as f:
		RAW_DATA_360 = json.load(f)

if UPDATE_ONE_DATA:
	print("Updating ONE data")
	url = lambda s: "https://xapi.us/v2/2759124950288873/game-stats/"+str(s)
	for i,game in enumerate(RAW_DATA_ONE["titles"]):
		game_id = game["titleId"]
		game_name = game["name"]
		file = "one/"+slugify(game_name)+".json"

		if not path.exists(file):
			print("%s/%s"%(i+1,len(RAW_DATA_ONE["titles"])), game_name, end='... ')
			pnt = True
			while(1):
				resp = get(url(game_id), headers=HEADER).json()
				if "success" in resp and not resp["success"]:
					if pnt:
						print("Waiting for tokens", end='... ')
						pnt = False
					time.sleep(60)
				else:
					with open(file, 'w') as f:
						resp["name"] = game_name
						json.dump(resp, f, sort_keys=True, indent=4)
						break

			print("Done!")

if UPDATE_360_DATA:
	print("Updating 360 data")
	url = lambda s: "https://xapi.us/v2/2759124950288873/game-stats/"+str(s)
	for i,game in enumerate(RAW_DATA_360["titles"]):
		game_id = game["titleId"]
		game_name = game["name"]
		file = "360/"+slugify(game_name)+".json"

		if not path.exists(file):
			print("%s/%s"%(i+1,len(RAW_DATA_360["titles"])), game_name, end='... ')
			pnt = True
			while(1):
				resp = get(url(game_id), headers=HEADER).json()
				if "success" in resp and not resp["success"]:
					if pnt:
						print("Waiting for tokens", end='... ')
						pnt = False
					time.sleep(60)
				else:
					with open(file, 'w') as f:
						resp["name"] = game_name
						json.dump(resp, f, sort_keys=True, indent=4)
						break

			print("Done!")

def get_stats(data):
	playtime, completion = 0, 0
	stats = data["statlistscollection"][0]["stats"]
	for s in stats:
		if "name" in s and s["name"].lower() == "minutesplayed":
			if "value" in s:
				playtime = s["value"]
		elif "name" in s and s["name"].lower() == "gameprogress":
			if "value" in s:
				completion = s["value"]
	return {'playtime': playtime, 'completion': completion}

def build_dataset(folder):
	dataset = []
	for i, file in enumerate(listdir(folder)):
		with open(folder+"/"+file) as f:
			if ".json" in file:
				data = json.load(f)
				game = {}
				game["name"] = data["name"]
				for k,v in get_stats(data).items(): game[k] = v
				dataset.append(game)
	return dataset

def format_playtime(t):
	M, H, D = t,0,0
	if t > 60:
		H = t//60
		M = t%60
		if H > 24:
			D = H//24
			H = H%24
	return "%s%s%s" % (str(D)+"d " if D > 0 else '',
					   str(H) + "h " if H > 0 else '',
					   str(M)+"m " if M > 0 else '')

def percent_to_color(p):
	if p > 99:
		return 'cyan'
	elif p > 75:
		return 'green'
	elif p > 50:
		return 'yellowgreen'
	elif p > 20:
		return 'yellow'
	elif p > 5:
		return 'orange'
	else:
		return 'red'

def random_color_hsv(value, all):
	H = np.random.rand()
	S = 0.1 + 0.9*(value / max(all))
	V = 0.8

	return color.hsv2rgb(np.array([H,S,V]))

def do(dataset, key, min, dpi, label):
	print("Processing "+key+" at "+str(dpi)+" dpi")
	EXCLUDES = ["youtube", "twitch", "tv"]
	data = sorted(dataset, key=lambda d: d[key], reverse=True)
	filter = lambda d: all([e not in d["name"].lower() for e in EXCLUDES]) and d[key] > min
	X = [d[key] for d in data if filter(d)]

	if key=="playtime":
		# L = ["%s %s"%(d['name'],format_playtime(d[key])) for d in data if filter(d)]
		# # plt.pie(X, rotatelabels=True, labels=L, explode=[0.1 for d in X], radius=5,
		# # 		autopct=lambda p: '%.1f%%' % p if p > 0 else "", colors=[random_color_hsv(x,X) for x in X])
		# # plt.legend(loc='upper left', bbox_to_anchor=(3.5, 3), borderaxespad=0.,
		# # 		   title="Total time played: %s" % format_playtime(sum(X)))

		L = [d['name'] for d in data if filter(d)]
		plt.figure(figsize=(20, 20))
		sns.set_theme(style="whitegrid")
		plt.bar(np.arange(len(X)), X, color=[random_color_hsv(x,X) for x in X], log=True)
		plt.xticks(np.arange(len(X)), L, rotation="vertical")
		plt.yticks([x for x in X], [format_playtime(t) for t in X], fontsize=10)
		plt.subplots_adjust(bottom=0.4, top=0.99)

	elif key=="completion":
		L = ["%s %s%%"%(d['name'],d[key]) for d in data if filter(d)]
		plt.pie(X, rotatelabels=True, labels=L, explode=[0.1 for d in X], radius=5,
				colors=[percent_to_color(x) for x in X])
		plt.legend(loc='upper left', bbox_to_anchor=(3.5, 3), borderaxespad=0.)

	plt.savefig("%s_%s_%s.png"%(label,key,dpi), bbox_inches='tight', dpi=dpi)
	plt.clf()

do(build_dataset("one"), "playtime", 60, 100, "one")
# do(build_dataset("one"), "completion", 1, 100, "one")


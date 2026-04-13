#!/usr/bin/env python3
"""Scrape GLOSS lesson catalog for Arabic-Levantine and Farsi."""
import urllib.request, json

def post(endpoint, data):
    url = f"https://gloss.dliflc.edu/{endpoint}"
    req = urllib.request.Request(url, data=data.encode(), method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "Morgenbrief/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

# 1. Get language IDs
langs = post("LanguageJSON.aspx", "action=listData")
for l in langs["dataList"]:
    t = l["title"]
    if any(k in t for k in ["Arabic", "Farsi", "Dari", "Levantine"]):
        print(f"  ID {l['id']}: {t}")

print()

# 2. Get level IDs
levels = post("LevelJSON.aspx", "action=listData")
for l in levels["dataList"]:
    print(f"  Level ID {l['id']}: {l['title']}")

print()

# 3. Get competence IDs
comps = post("CompetenceJSON.aspx", "action=listData")
for c in comps["dataList"]:
    print(f"  Comp ID {c['id']}: {c['title']}")

print()

# 4. Search for Arabic-Levantine Level 1 lessons (first page)
# Need to find the Levantine language ID first
lev_id = None
farsi_id = None
for l in langs["dataList"]:
    if "Levantine" in l["title"]: lev_id = str(l["id"])
    if l["title"] == "Farsi": farsi_id = str(l["id"])

print(f"Levantine ID: {lev_id}, Farsi ID: {farsi_id}")
print()

# Find Level 1 ID
level1_id = None
for l in levels["dataList"]:
    if l["title"] == "1": level1_id = str(l["id"])

print(f"Level 1 ID: {level1_id}")
print()

# Search Arabic-Levantine Level 1
if lev_id and level1_id:
    data = f"action=search&gr=0&page=1&searchString=&languageIds={lev_id}&levelIds={level1_id}&modalityIds=&competenceIds=&topicIds=&subTopicIds=&video=0&statusIds=&mine=0&sortBy="
    result = post("LessonJSON.aspx", data)
    lessons = result.get("lessons", [])
    print(f"Arabic-Levantine Level 1: {len(lessons)} lessons")
    for les in lessons[:5]:
        print(f"  {les.get('name', '?')}: {les.get('title', '?')} [{les.get('modality', '?')}] [{les.get('competence', '?')}]")
    print()

# Search Farsi Level 1
if farsi_id and level1_id:
    data = f"action=search&gr=0&page=1&searchString=&languageIds={farsi_id}&levelIds={level1_id}&modalityIds=&competenceIds=&topicIds=&subTopicIds=&video=0&statusIds=&mine=0&sortBy="
    result = post("LessonJSON.aspx", data)
    lessons = result.get("lessons", [])
    print(f"Farsi Level 1: {len(lessons)} lessons")
    for les in lessons[:5]:
        print(f"  {les.get('name', '?')}: {les.get('title', '?')} [{les.get('modality', '?')}] [{les.get('competence', '?')}]")

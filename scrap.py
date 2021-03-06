#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, sys, re, json
import random, md5
import requests
import warnings
warnings.filterwarnings("ignore")

def buildUrl(url):
    if not url.startswith("http"):
        url = "https://www.parlement-et-citoyens.fr/%s" % url.lstrip("/")
    return url

def buildCache(url):
    url = url.replace("https://www.parlement-et-citoyens.fr/", "")
    return url.replace("/", "___")

def download(url):
    url = buildUrl(url)
    if not os.path.isdir(".cache"):
        os.makedirs(".cache")
    page = buildCache(url)
    fil = os.path.join(".cache", page)
    if not os.path.exists(fil):
        print url, "->", page
        data = requests.get(url).content
        with open(fil, "w") as f:
            f.write(data)
    else:
        with open(fil) as f:
            data = f.read()
    return data.decode("utf-8")

re_profiles = re.compile(r'href="/profile/([^"]+)"')
re_nextpage = lambda project: re.compile(ur'href="(/projects/%s/participants/\d+)" aria-label="Aller à la page suivante' % project)

def processList(page, all_contribs, project, users={}, contributions={}):
    print page
    content = download(page)
    for u in set(re_profiles.findall(content)):
        processUser(u, all_contribs, users, contributions, project)
    nextp = re_nextpage(project).search(content)
    return (nextp.group(1) if nextp else None, users, contributions)

re_clean_lines = re.compile(r'[\n\r]+', re.M)
re_clean_spaces = re.compile(r'\s+')
cleaner = lambda x: re_clean_spaces.sub(' ', re_clean_lines.sub(' ', x)).replace('&#039;', "'").replace(u'’', "'").replace('&amp;', '&').replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>').strip()

meta_regexps = {
  "name": re.compile(r'<h1 class="profile__name">([^<]+?)</h1>'),
  "type": re.compile(r'<li><i class="cap cap-connection[^"]*"></i>([^<]+?)</li>'),
  "geoloc": re.compile(r'<li><i class="cap cap-marker[^"]*"></i>([^<]+?)</li>'),
  "description": re.compile(r'</h1>\s*<p>(.*?)</p>'),
  "website": re.compile(r'<li><i class="cap cap-link[^"]*"></i>\s*<a class="external-link" href="([^"]+?)">'),
  "twitter": re.compile(r'<li><i class="cap cap-twitter[^"]*"></i>\s*<a class="external-link" href="[^"]+twitter.com/([^"]+)">'),
  "facebook": re.compile(r'<li><i class="cap cap-facebook[^"]*"></i>\s*<a class="external-link" href="([^"]+?)">')
}

extra_regexps = [
  ("date_inscription", re.compile(r'<li><i class="cap cap-calendar-1"></i>\s*Inscrit depuis le (\d+)/(\d+)/(\d+)\s*</li>'), lambda x: "%s-%s-%s" % (x.group(3), x.group(2), x.group(1))),
  ("picture", re.compile(r'<img title[^>]*? src="(/media/cache/default_profile/[^"]+)"[\s/]*>'), lambda x: buildUrl(x.group(1)))
]

re_propals = lambda project: re.compile(r'<li class="opinion has-chart[^"]*?" data-ok="(\d+)" data-nok="(\d+)" data-mitige="(\d+)" data-pie-id="(\d+)">.*?<a href="(/projects/%s/consultation/consultation(?:-\d+)?/opinions/((([^/]+)/[^/"]+)[^"]*))">\s*([^<]+)\s*</a>.*?<span>(\d+) vote.*?<span>(\d+) argument.*?<span>(\d+) source' % project)
re_votes = lambda project: re.compile(ur'</a> a voté sur <a href="/projects/%s/consultation/consultation(?:-\d+)?/opinions/([^"]+)">[^<]+</a>.*?<span class="label label-(warning|success|danger)">' % project)

def processUser(userId, all_contribs, users, contributions, project):
    if userId in users:
        return

    userUrl = buildUrl("/profile/%s" % userId)
    user = {
      "id": userId,
      "url": userUrl,
      "contributions": [],
      "contributions_total": 0,
      "propositions_total": 0,
      "amendements_total": 0,
      "votes_pro": [],
      "votes_pro_total": 0,
      "votes_against": [],
      "votes_against_total": 0,
      "votes_unsure": [],
      "votes_unsure_total": 0,
      "votes_total": 0
    }

    content = cleaner(download(userUrl))

    for key, reg in meta_regexps.items():
        res = reg.search(content)
        user[key] = res.group(1).strip() if res else ""
    for key, reg, lmbda in extra_regexps:
        res = reg.search(content)
        user[key] = lmbda(res) if res else ""
    if not user["type"]:
        user["type"] = "Citoyen"

    for pr in re_propals(project).findall(content):
        if not pr[5] in all_contribs:
            print >> sys.stderr, "WARNING: found a mysterious propal", userId, pr[5], pr[8]
            continue
        typ = "v" if "/versions/" in pr[5] else "o"
        prop = {
          "id": all_contribs[pr[5]],
          "id_str": pr[5],
          "type": "amendement" if typ == "v" else "proposition",
          "section": pr[7],
          "parent": pr[6] if typ == "v" else "",
          "author": user["id"],
          "name": pr[8],
          "votes_pro": int(pr[0]),
          "votes_against": int(pr[1]),
          "votes_unsure": int(pr[2]),
          "votes_total": int(pr[0]) + int(pr[1]) + int(pr[2]),
          "arguments": int(pr[10]),
          "sources": int(pr[11]),
          "url": buildUrl(pr[4])
        }

        contributions[prop["id"]] = prop
        user['contributions'].append(prop["id"])

        user['contributions_total'] += 1
        if prop['type'] == 'proposition':
            user['propositions_total'] += 1
        else:
            user['amendements_total'] += 1

    for v in re_votes(project).findall(content):
        # Check votes are on existing contributions, not on arguments/sources/comments
        if not v[0] in all_contribs:
            continue
        vtyp = "pro" if v[1] == "success" else "against" if v[1] == "danger" else "unsure"
        user['votes_%s' % vtyp].append(all_contribs[v[0]])
        user['votes_%s_total' % vtyp] += 1
        user['votes_total'] += 1
    #print "-", userId, user['votes_total'], "votes", user['contributions_total'], "propals"

    users[userId] = user

def buildContribsFromAPI(repodir, project):
    all_contribs = {}
    for root, _, files in os.walk(repodir):
        for fil in files:
            if "opinion" not in root:
                continue
            with open(os.path.join(root, fil)) as f:
                data = json.load(f)
                try:
                    data = data['opinion']
                    cid = "o%s" % data["id"]
                except:
                    data = data['version']
                    cid = "v%s" % data["id"]
                if project not in data["_links"]["show"]:
                    continue
                cidstr = data["_links"]["show"]
                cidstr = cidstr[cidstr.find("/opinions/")+10:]
                all_contribs[cidstr] = cid
    return all_contribs

def anonymize_users(users, contributions):
    salt = unicode(random.random())
    anon_users = {}
    for uid, u in users.items():
        idmd5 = str(int(md5.new((u"%s%s%s%s" % (uid, u['name'], u['description'], salt)).encode('utf-8')).hexdigest()[:8], 16))
        u['id'] = idmd5
        if u['contributions_total'] or u['type'] != 'Citoyen':
            for cid, c in contributions.items():
                if c['author'] == uid:
                    c['author'] = idmd5
        else:
            for key in ['url', 'name', 'geoloc', 'description', 'website', 'twitter', 'facebook']:
                u[key] = ''
        anon_users[idmd5] = u
    return anon_users, contributions

def format_for_csv(val):
    if not val:
        return ""
    if type(val) == int:
        return str(val)
    elif "," in val:
        val = '"%s"' % val.replace('"', '""')
    return val.encode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        project = sys.argv[1]
    else:
        project = "projet-de-loi-pour-la-reconquete-de-la-biodiversite-de-la-nature-et-des-paysages"
    if not os.path.exists("data-contributions"):
        print >> sys.stderr, "ERROR: missing contributions data repository"
        print >> sys.stderr, 'Please build it first with "cd moissonneur-API && npm install && node fetch-json.js ../data-contributions"'
        exit(1)
    all_contribs = buildContribsFromAPI("data-contributions", project)

    nextPage, users, contributions = processList("/projects/%s/participants" % project, all_contribs, project)
    while nextPage:
        nextPage, users, contributions = processList(nextPage, all_contribs, project, users, contributions)

    print "Total users found:", len(users)
    print "contribs from scrap:", len(contributions)
    print "contribs from API with votes:", len(all_contribs)

    users, contributions = anonymize_users(users, contributions)

    if not os.path.exists("data"):
        os.makedirs("data")
    with open(os.path.join("data", "users.json"), 'w') as f:
        json.dump(users, f, indent=2)
    with open(os.path.join("data", "contributions.json"), 'w') as f:
        json.dump(contributions, f, indent=2)
    with open(os.path.join("data", "users.csv"), 'w') as f:
        headers = "id,name,type,date_inscription,geoloc,website,twitter,facebook,contributions_total,propositions_total,amendements_total,votes_total,votes_pro_total,votes_against_total,votes_unsure_total,description,picture,url"
        print >> f, headers
        for u in users.values():
            print >> f, ",".join([format_for_csv(u[h]) for h in headers.split(",")])

import json
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import re

def fixurl(url):
    if url[:2] == "//":
        return "https:" + url
    elif url[0] == "/":
        return "https://devpost.com" + url
    else:
        return url


def checkurl(url):
    return re.match(re.compile(
        '^(?:http|ftp)s?://(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\\.)+(?:[A-Z]{2,6}\\.?|[A-Z0-9-]{2,}\\.?)\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3})(?::\\d+)?(?:/?|[/?]\\S+)$',
        re.IGNORECASE), url) is not None

def project(mainreq, name):
    info = {}
    soup = BeautifulSoup(mainreq.text, 'html.parser')

    # Get project gallery (images, videos...)
    try:
        gallery = []
        for li in soup.find("div", {"id": "gallery"}).find("li"):
            try:
                url = fixurl(li.find("a")['href'])
                caption = li.p.i.text.lstrip().rstrip()
                gallery.append({"url": url, "caption": caption})
            except:
                url = fixurl(li.findChildren("iframe")[0]['src'])
                try:
                    caption = li.p.i.text.lstrip().rstrip()
                except:
                    caption = None
                gallery.append({"url": url, "caption": caption})
        info['gallery'] = gallery
    except:
        info['gallery'] = []


    # Get project title and description from the page's header
    try:
        project_header = soup.find("div", class_="small-12 columns")

        info['title'] = str(project_header.find("h1")).replace('<h1 id="app-title">', '').replace("</h1>", "")
        info['description'] = str(project_header.find("p", class_="large")).replace('<p class="large">', '').replace("</p>", "").strip()
    except:
        info['title'] = ''
        info['description'] = ''


    # Get technologies used
    try:
        built_with = []
        for li in soup.find("div", {"id": "built-with"}).findChildren("li"):
            built_with.append(li.text.lstrip().rstrip())
        info['built_with'] = built_with
    except:
        info['built_with'] = []


    # Get external links
    try:
        app_links = []
        for link in soup.find("nav", {"class": "app-links"}).findChildren("a"):
            app_links.append(link['href'])
        info['app_links'] = app_links
    except:
        info['app_links'] = []


    # Get parent hackathon
    try:
        submitted_to = []
        for hackathon in soup.findAll("div", class_="software-list-content"):
            submitted_to.append(hackathon.text.lstrip().rstrip().split("\n")[0])
        info['submitted_to'] = submitted_to
    except:
        info['submitted_to'] = []


    # Get creators of project
    created_by = []
    for hackathon in soup.findAll("li", class_="software-team-member"):
        created_by.append(hackathon.findChildren("img")[0]['title'])
    info['created_by'] = created_by


    # Get all updates and comments
    ids = []
    temphtml = []
    mastercomments = []
    users = []
    times = []
    for art in soup.findAll("article"):
        if "data-commentable-id" in dict(art.attrs).keys():
            templist = []
            ids.append(art['data-commentable-id'])
            for text in art.findChildren("p"):
                if len(dict(text.attrs).keys()) == 0:
                    templist.append(str(text))
            temphtml.append("\n".join(templist))
            try:
                users.append(art.find("a").attrs['href'].replace("https://devpost.com/", ""))
            except:
                users.append("Private user")
            times.append(datetime.strptime(art.time.attrs['datetime'].replace(
                art.time.attrs['datetime'].split(":")[-2:][0][2:] + ":" + art.time.attrs['datetime'].split(":")[-2:][1],
                art.time.attrs['datetime'].split(":")[-2:][0][2:] + art.time.attrs['datetime'].split(":")[-2:][1]),
                                           '%Y-%m-%dT%H:%M:%S%z').strftime("%Y-%m-%dT%H:%M:%S") + ".000Z")
    for mainid in ids:
        comments = []
        maindict = requests.get("https://devpost.com/software_updates/" + mainid + "/comments", headers={
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).json()
        for page in range(int(maindict['meta']['pagination']['total_pages'])):
            pagenum = page + 1
            commentdict = requests.get(
                "https://devpost.com/software_updates/" + mainid + "/comments?page=" + str(pagenum), headers={
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).json()
            for comment in commentdict['comments']:
                tempcomment = {}
                tempcomment['user'] = comment['user']['screen_name']
                tempcomment['comment'] = comment['html_body']
                temptime = datetime.strptime(comment['created_at'].replace(
                    comment['created_at'].split(":")[-2:][0][2:] + ":" + comment['created_at'].split(":")[-2:][1],
                    comment['created_at'].split(":")[-2:][0][2:] + comment['created_at'].split(":")[-2:][1]),
                                             '%Y-%m-%dT%H:%M:%S%z')
                # print(comment['created_at'].replace(comment['created_at'].split(":")[-2:][0][2:] + ":" + comment['created_at'].split(":")[-2:][1], comment['created_at'].split(":")[-2:][0][2:] + comment['created_at'].split(":")[-2:][1]))
                tempcomment['created_at'] = temptime.strftime("%Y-%m-%dT%H:%M:%S") + ".000Z"
                comments.append(tempcomment)
                # ?page=
        mastercomments.append(list(reversed(comments)))
    final = []
    for created_at, user, html, comments in zip(times, users, temphtml, mastercomments):
        final.append({"user": user, "update": html, "created_at": created_at, "comments": comments})
    info['updates'] = final

    
    # Get number of likes
    try:
        likes = soup.find("a", class_="like-button button radius secondary").find("span", class_="side-count").string
        info['likes'] = int(likes)
    except:
        info['likes'] = 0


    # Get all prizes that the project won
    info['prizes'] = []

    # Find all 'span' elements that are labeled as winners
    winner_spans = soup.find_all('span', class_='winner label radius small all-caps')
    if winner_spans:
        for winner_info in winner_spans:
            # Find the closest previous 'a' tag that might contain the hackathon name and URL
            hackathon_link_tag = winner_info.find_previous("a", href=True, string=lambda text: text and "Hackathon" in text)
            hackathon_name = hackathon_link_tag.text if hackathon_link_tag else "Hackathon name not found"
            hackathon_url = hackathon_link_tag['href'] if hackathon_link_tag else "URL not provided"

            # Find the parent 'li' of the 'winner_info' which contains the full prize details
            prize_li = winner_info.find_parent('li')
            if prize_li:
                prize_text = prize_li.get_text(strip=True)
                prize_detail = {
                    "prize_text": prize_text,
                    "hackathon_name": hackathon_name,
                    "hackathon_url": hackathon_url
                }
                info['prizes'].append(prize_detail)
    

    # Get project unique name as it is in the URL
    info['link'] = name

    return info


def lambda_handler(event, context):

    projectname = event['path'].replace("/project/", "")

    mainreq = requests.get('https://devpost.com/software/' + projectname, headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'})
    if mainreq.status_code == 404:
        return {
            "statusCode": 404,
            "body": json.dumps({
                "errors": ["Project not found", projectname]
            })
        }

    return {
        "statusCode": 200,
        "body": json.dumps(project(mainreq, projectname)),
    }
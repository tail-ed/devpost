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


def user(mainreq, username):
    info = {}

    soup_mainpage = BeautifulSoup(mainreq.text, 'html.parser')


    # Get user photo
    photo = fixurl(soup_mainpage.find("div", {"id": "portfolio-user-photo"}).img['src'])
    info['image'] = photo


    # Get user location
    for li in soup_mainpage.findAll("li", class_=None):
        location = li.findChildren("span", class_="ss-location")
        if len(location) != 0:
            location = li.text.lstrip().rstrip()
            break
    info['location'] = location


    # Get user skills
    skills = []
    for div in soup_mainpage.findAll("div", class_="tag-list"):
        if div.span.strong.text == "Skills":
            for skill in div.ul.findChildren("li"):
                skills.append(skill.text.lstrip().rstrip())
    info['skills'] = skills


    # Get user insterests
    interests = []
    for div in soup_mainpage.findAll("div", class_="tag-list"):
        if div.span.strong.text == "Interests":
            for interest in div.ul.findChildren("li"):
                interests.append(interest.text.lstrip().rstrip())
    info['interests'] = interests


    # Get user bio
    bio = soup_mainpage.find("p", {"id": "portfolio-user-bio"}).text.lstrip().rstrip()
    if len(bio) != 0:
        info['bio'] = bio
    else:
        info['bio'] = None


    # Get user header
    header = {}
    stylestr = soup_mainpage.find_all('style')[0].text
    styles = re.match(r'\s*([^{]+)\s*\{\s*([^}]*?)\s*}', stylestr)[2].split("\n")
    tempstyle = {}
    for style in styles:
        if len(style) != 0:
            name = style.lstrip().split(": ")[0]
            value = style.lstrip().split(": ")[1][:-1]
            tempstyle[name] = value
    header['color'] = tempstyle['background-color']
    if "background-image" in tempstyle.keys():
        header['image'] = tempstyle['background-image'][4:-1]
    info['header'] = header


    # Get user real name
    namestr = soup_mainpage.find("h1", {"id": "portfolio-user-name"})
    name = namestr.text.lstrip().rstrip().split("\n")[0].lstrip().rstrip()
    info['name'] = name


    # Get username
    namestr = soup_mainpage.find("h1", {"id": "portfolio-user-name"})
    username = namestr.text.lstrip().rstrip().split("\n")[1].lstrip().rstrip()[1:-1]
    info['username'] = username


    # Get user links: website, GitHub, Twitter, LinkedIn
    if soup_mainpage.find("span", class_="ss-link"):
        website = soup_mainpage.find("span", class_="ss-link").parent.a['href'].lstrip().rstrip()
    else:
        website = None
    info['website'] = website

    if soup_mainpage.find("span", class_="ss-octocat"):
        github = soup_mainpage.find("span", class_="ss-octocat").parent.a['href'].lstrip().rstrip()
    else:
        github = None
    info['github'] = github

    if soup_mainpage.find("span", class_="ss-twitter"):
        twitter = soup_mainpage.find("span", class_="ss-twitter").parent.a['href'].lstrip().rstrip()
    else:
        twitter = None
    info['twitter'] = twitter

    if soup_mainpage.find("span", class_="ss-linkedin"):
        linkedin = soup_mainpage.find("span", class_="ss-linkedin").parent.a['href'].lstrip().rstrip()
    else:
        linkedin = None
    info['linkedin'] = linkedin


    # Get user achievements
    # Maximum of 11 achievements, so only 1 page to parse
    soup_achievements = BeautifulSoup(requests.get('https://devpost.com/' + username + '/achievements', headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).text,
                          'html.parser')
    achievements = soup_achievements.find_all('div', class_='content')
    images = soup_achievements.find_all('img', class_='badge')
    achevlist = []
    for achievement, image in zip(achievements, images):
        tempachev = {}
        tempachev['name'] = achievement.findChildren("h5", recursive=False)[0].text.replace("  ", "").replace("\t",
                                                                                                              "").replace(
            "\n", " ").lstrip().rstrip().title()
        tempachev['description'] = achievement.findChildren("p", recursive=False)[0].text.lstrip().rstrip() + "."
        tempachev['achievedOn'] = datetime.strptime(achievement.findChildren("small", recursive=False)[0].text,
                                                    'Achieved %B %d, %Y').isoformat() + ".000Z"
        tempachev['icon'] = "https:" + image['srcset'][:-3]
        achevlist.append(tempachev)
    info['achievements'] = achevlist


    # Get user followers
    # We only fetch the number of followers, not all individual followers
    # This is to significantly decrease the number of requests (and, by extension, the amount of time to complete this function)
    # for very active profiles (since follower pages only display 32 entries)

    try:
        followers = soup_mainpage.find("a", href="/" + username + "/followers").find("span").string
        info['followers'] = int(followers)
    except:
        info['followers'] = 0


    # Get user following
    # We only fetch the number of followers, not all individual followers
    # This is to significantly decrease the number of requests (and, by extension, the amount of time to complete this function)
    # for very active profiles (since follower pages only display 32 entries)

    try:
        following = soup_mainpage.find("a", href="/" + username + "/following").find("span").string
        info['following'] = int(following)
    except:
        info['following'] = 0


    # Get user projects
    # May have more than 1 page (pages have 24 entries)
    info['projects'] = []
    current_page = 1
    
    continue_to_next_page = True
    while continue_to_next_page:
        # Very strict checking to avoid fetching more pages than needed: will break by default
        continue_to_next_page = False

        soup_projects = BeautifulSoup(requests.get('https://devpost.com/' + username + '?page=' + str(current_page), headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).text,
                          'html.parser')

        projs = []

        for proj in soup_projects.findAll("a", class_="link-to-software"):
            did_win = proj.find("img", class_="winner") != None

            full_project = {
                'link': proj['href'].replace("https://devpost.com/software/", ""),
                'did_win': did_win
            }

            projs.append(full_project)

        info['projects'] += projs

        if len(projs) == 24:
            continue_to_next_page = True
            current_page += 1


    # Get user likes
    # May have more than 1 page (pages have 24 entries)
    info['likes'] = []
    current_page = 1
    
    continue_to_next_page = True
    while continue_to_next_page:
        # Very strict checking to avoid fetching more pages than needed: will break by default
        continue_to_next_page = False

        soup_likes = BeautifulSoup(requests.get('https://devpost.com/' + username + '/likes?page=' + str(current_page), headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).text,
                          'html.parser')
        
        likes = []

        for like in soup_likes.findAll("a", class_="link-to-software"):
            likes.append(like['href'].replace("https://devpost.com/software/", ""))

        info['likes'] += likes

        if len(likes) == 24:
            continue_to_next_page = True
            current_page += 1


    # Get user participations
    # May have more than 1 page (pages have 24 entries)
    info['hackathons'] = []
    current_page = 1
    
    continue_to_next_page = True
    while continue_to_next_page:
        # Very strict checking to avoid fetching more pages than needed: will break by default
        continue_to_next_page = False

        soup_hackathons = BeautifulSoup(requests.get('https://devpost.com/' + username + '/challenges?page=' + str(current_page), headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}).text,
                          'html.parser')

        hackathons = []

        for hack in soup_hackathons.findAll("a", {"data-role": "featured_challenge"}):
            hackathons.append(urlparse(hack['href']).hostname.split('.')[0])

        info['hackathons'] += hackathons

        if len(hackathons) == 24:
            continue_to_next_page = True
            current_page += 1


    info['links'] = {}
    info['links']['github'] = info['github']
    info['links']['linkedin'] = info['linkedin']
    info['links']['twitter'] = info['twitter']
    info['links']['website'] = info['website']
    del info['github']
    del info['linkedin']
    del info['twitter']
    del info['website']

    return info


def lambda_handler(event, context):
    """Sample pure Lambda function

    Parameters
    ----------
    event: dict, required
        API Gateway Lambda Proxy Input Format

        Event doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html#api-gateway-simple-proxy-for-lambda-input-format

    context: object, required
        Lambda Context runtime methods and attributes

        Context doc: https://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html

    Returns
    ------
    API Gateway Lambda Proxy Output Format: dict

        Return doc: https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-proxy-integrations.html
    """

    username = event['path'].replace("/user/", "")

    mainreq = requests.get('https://devpost.com/' + username, headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'})
    if mainreq.status_code == 404:
        return {
            "statusCode": 404,
            "body": json.dumps({
                "errors": ["Username not found"]
            })
        }

    return {
        "statusCode": 200,
        "body": json.dumps(user(mainreq, username)),
    }

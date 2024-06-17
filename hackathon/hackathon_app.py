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

def hackathon(response, name):
    soup = BeautifulSoup(response.text, 'html.parser')
    info = {}

    try:
        # Extract Hackathon Name and Description
        header_image = soup.find('h1', class_='header-image')
        info['name'] = header_image.img['alt'] if header_image else "No Name Available"

        description_tag = soup.find('div', class_='content')
        info['description'] = description_tag.find('h3').text.strip() if description_tag and description_tag.find('h3') else "No Description Available"

        # Extract Dates and Deadline
        deadline_tag = soup.find('div', class_='deadline')
        info['deadline'] = deadline_tag.text.strip() if deadline_tag else "No Deadline Info"

        # Extract Participants
        participants_tag = soup.find('strong', string=re.compile(r'participants'))
        info['participants'] = participants_tag.parent.text.strip() if participants_tag else "Participant Info Not Available"

        # Extract Prizes
        prizes = []
        for prize in soup.find_all('div', class_='prize'):
            prizes.append({
                'title': prize.find('h6').text.strip(),
                'details': ' '.join([p.text.strip() for p in prize.find_all('p')])
            })
        info['prizes'] = prizes

        # Extraction of sponsors
        sponsors_v2 = []  # Detailed sponsor info including categories
        sponsorCategory = "Unknown"  # Default category if none is found

        # Find the div that contains the sponsor information
        sponsor_tiles_div = soup.find('div', id='sponsor-tiles')

        if sponsor_tiles_div:
            current_category = None
            for child in sponsor_tiles_div.children:
                if child.name == 'h5':  # Category header
                    current_category = child.get_text(strip=True)
                elif child.name == 'a':  # Sponsor link
                    img = child.find('img', class_='sponsor_logo_img')
                    if img:
                        sponsors_v2.append({
                            'name': img['alt'],
                            'logo': img['src'],
                            'link': child.get('href', 'No Link'),
                            'category': current_category if current_category else "No Category Specified"
                        })

        info['sponsors'] = sponsors_v2

        # Extract Rules Link (if any)
        rules_link = soup.find('a', href=re.compile(r'/rules'))
        info['rules_link'] = rules_link['href'] if rules_link else "No Rules Link"

    except Exception as e:
        print(f"Error parsing hackathon information: {e}")
        info['error'] = str(e)

    return info


def lambda_handler(event, context):

    hackathonname = event['path'].replace("/hackathon/", "")

    mainreq = requests.get(f'https://{hackathonname}.devpost.com/', headers={'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'})
    if mainreq.status_code == 404:
        return {
            "statusCode": 404,
            "body": json.dumps({
                "errors": ["Project not found"]
            })
        }

    return {
        "statusCode": 200,
        "body": json.dumps(hackathon(mainreq, hackathonname)),
    }
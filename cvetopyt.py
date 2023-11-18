from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse, urljoin
from collections import Counter

app = Flask(__name__)

def standardize_color(color):
    if len(color) == 4: # One additional character for "#"
        return "#" + color[1] * 2 + color[2] * 2 + color[3] * 2
    return color.lower()

def is_valid_url(url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and bool(parsed.scheme)

def get_all_website_links(url):
    urls = set()
    domain_name = urlparse(url).netloc
    soup = BeautifulSoup(requests.get(url).content, "html.parser")

    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")
        if href == "" or href is None:
            continue

        href = urljoin(url, href)
        parsed_href = urlparse(href)

        if parsed_href.netloc != domain_name:
            continue

        urls.add(href)
    return urls

def find_colors_on_website(url):
    colors = []
    all_website_links = get_all_website_links(url)

    for url in all_website_links:
        try:
            pattern = r'#(?:[0-9a-fA-F]{3}){1,2}|rgba?(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*(?:1|0?.\d+?)\s*)'
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            link_tags = soup.find_all('link', rel='stylesheet')
            css_urls = [urljoin(url, tag.get('href')) for tag in link_tags]

            style_tags = soup.find_all('style')
            styles = " ".join(tag.get_text(" ", strip=True) for tag in style_tags)
            colors.extend(map(standardize_color, re.findall(pattern, styles)))

            for css_url in css_urls:
                css_response = requests.get(css_url)
                css_response.raise_for_status()
                css_text = css_response.text
                colors.extend(map(standardize_color, re.findall(pattern, css_text)))
        except requests.exceptions.RequestException as e:
            print("An error occurred when accessing the website:", e)

    color_counts = dict(Counter(colors))
    sorted_colors = sorted(color_counts.items(), key=lambda item: item[1], reverse=True)
    return sorted_colors

@app.route("/colors", methods=["GET"])
def get_website_colors():
    website_url = request.args.get("url", default=None)
    if website_url and is_valid_url(website_url):
        colors = find_colors_on_website(website_url)
        return jsonify(colors)
    else:
        return jsonify({"error": "Invalid url"}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

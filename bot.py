#!/usr/bin/env python3

import argparse
import bs4
import requests
import discord
import http.cookiejar
from typing import List
import os
from comment import Comment

parser = argparse.ArgumentParser()
parser.add_argument('cookies', help='the cookies file')


def getFAPage(cookieloc: str) -> str:
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj

    page = s.get('https://www.furaffinity.net/msg/others/')
    return page.content


def parseFAPage(page: str) -> List[str]:
    soup = bs4.BeautifulSoup(page.content, 'html.parser')
    comments = soup.find('section', {'id': 'messages-comments'})
    foundComments = []
    for comment in comments.children:
        pass
    return foundComments


def runBot():
    client = discord.Client()
    try:
        discord_token = os.environ['DISCORDTOKEN']
    except IndexError:
        print("Discord API token could not be loaded")
        exit(1)

    @client.event
    async def on_ready():
        pass

    client.start(discord_token)
    while not client.is_ready():
        pass
    client.logout()


if __name__ == "__main__":
    args = parser.parse_args()
    comments = parseFAPage(getFAPage(args.cookies))
    if comments:
        pass

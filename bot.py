#!/usr/bin/env python3

import argparse
import bs4
import requests
import discord
import http.cookiejar
from typing import List
import os
from comment import Comment
import os.path
import logging

parser = argparse.ArgumentParser()
parser.add_argument('cookies', help='the cookies file')
parser.add_argument('--logging', default='debug', help='the logging level for the bot')


def getFAPage(cookieloc: str) -> str:
    '''Get the notifications page on FurAffinity'''
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj

    page = s.get('https://www.furaffinity.net/msg/others/')
    return page.content


def parseFAPage(page: bytes) -> List[str]:
    '''Find the comments on the page'''
    soup = bs4.BeautifulSoup(page, 'html.parser')
    comments = soup.find('section', {'id': 'messages-comments-submission'})
    subComments = comments.find('div', {'class': 'section-body js-section'}
                                ).find('ul', {'class': 'message-stream'}).findAll('li')
    foundComments = [comm.text for comm in subComments]

    comments = soup.find('section', {'id': 'messages-comments-journal'})
    journalComments = comments.find('div', {'class': 'section-body js-section'}
                                    ).find('ul', {'class': 'message-stream'}).findAll('li')
    for comm in journalComments:
        foundComments.append(comm.text)

    return foundComments


def runBot():
    '''Start up the discord bot'''
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

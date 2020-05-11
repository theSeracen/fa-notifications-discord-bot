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
    logging.debug('Atempting to load cookies')
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj
    logging.debug('Cookies loaded')

    page = s.get('https://www.furaffinity.net/msg/others/')
    logging.debug('FA page received')
    return page.content


def parseFAPage(page: bytes) -> List[str]:
    '''Find the comments on the page'''
    soup = bs4.BeautifulSoup(page, 'html.parser')

    logging.debug('Attempting to find submission comments')
    comments = soup.find('section', {'id': 'messages-comments-submission'})
    subComments = comments.find('div', {'class': 'section-body js-section'}
                                ).find('ul', {'class': 'message-stream'}).findAll('li')
    logging.debug('{} submission comments found'.format(len(subComments)))
    foundComments = [comm.text for comm in subComments]

    logging.debug('Attempting to find journal comments')
    comments = soup.find('section', {'id': 'messages-comments-journal'})
    journalComments = comments.find('div', {'class': 'section-body js-section'}
                                    ).find('ul', {'class': 'message-stream'}).findAll('li')
    logging.debug('{} journal comments found'.format(len(subComments)))
    for comm in journalComments:
        foundComments.append(comm.text)

    return foundComments


def runBot():
    '''Start up the discord bot'''
    client = discord.Client()
    try:
        logging.debug('Attempting to load Discord API key')
        discord_token = os.environ['DISCORDTOKEN']
        logging.debug('Discord token loaded')
    except IndexError:
        print("Discord API token could not be loaded")
        logging.critical('Discord token could not be found')
        exit(1)

    @client.event
    async def on_ready():
        logging.debug('Discord client ready')
        pass

    logging.debug('Starting Discord client')
    client.start(discord_token)
    while not client.is_ready():
        pass
    client.logout()
    logging.debug('Discord client closed')


if __name__ == "__main__":
    logging.basicConfig(filename='furaffinitybot.log', level=logging.DEBUG)
    args = parser.parse_args()
    logging.info('Getting FA page')
    comments = parseFAPage(getFAPage(args.cookies))
    if comments:
        pass

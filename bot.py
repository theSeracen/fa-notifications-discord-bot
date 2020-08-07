#!/usr/bin/env python3

import argparse
import bs4
import requests
import discord
import re
import http.cookiejar
from typing import List
import os
import sys
import os.path
import logging
from dotenv import load_dotenv

load_dotenv()
parser = argparse.ArgumentParser()
parser.add_argument('cookies', help='the cookies file')
parser.add_argument('--logging', default='debug', help='the logging level for the bot')

logger = logging.getLogger(__name__)
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    filename='furaffinitybot.log',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=logging.ERROR)
logging.getLogger(__name__).setLevel(logging.DEBUG)


def getFAPage(cookieloc: str, url: str) -> str:
    '''Get the notifications page on FurAffinity'''
    logger.debug('Attempting to load cookies')
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj
    logger.debug('Cookies loaded')

    page = s.get(url)
    logger.debug('FA page received')
    return page.content


def parseFANotesPage(page: bytes) -> List[str]:
    '''Find the unread notes on the page'''
    soup = bs4.BeautifulSoup(page, 'html.parser')
    logger.debug('Attempting to find unread notes')

    unreadNotes = []
    notes = soup.findAll('div', {'class': 'message-center-pms-note-list-view'})
    for note in notes:
        if note.find('img', {'class': 'unread'}):
            message = note.text.strip()
            message = re.sub(r'\s+', ' ', message)
            unreadNotes.append(message)
    logger.info('{} unread notes found'.format(len(unreadNotes)))
    return unreadNotes


def parseFAMessagePage(page: bytes) -> List[str]:
    '''Find the comments on the page'''
    soup = bs4.BeautifulSoup(page, 'html.parser')
    foundComments = []

    logger.debug('Attempting to find submission comments')
    try:
        comments = soup.find('section', {'id': 'messages-comments-submission'})
        subComments = comments.find('div', {'class': 'section-body js-section'}
                                    ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.debug('{} submission comments found'.format(len(subComments)))
        foundComments = [comm.text for comm in subComments]
    except AttributeError as e:
        logger.warning('No submission comments found')
    except Exception as e:
        logger.critical(e)

    journalComments = []
    try:
        logger.debug('Attempting to find journal comments')
        comments = soup.find('section', {'id': 'messages-comments-journal'})
        journalComments = comments.find('div', {'class': 'section-body js-section'}
                                        ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.debug('{} journal comments found'.format(len(journalComments)))
    except AttributeError:
        logger.warning('No journal comments found')
    except Exception as e:
        logger.critical(e)

    shouts = []
    try:
        logger.debug('Attempting to find shouts')
        comments = soup.find('section', {'id': 'messages-shouts'})
        journalComments = comments.find('div', {'class': 'section-body js-section'}
                                        ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.debug('{} shouts found'.format(len(shouts)))
    except AttributeError:
        logger.warning('No shouts found')
    except Exception as e:
        logger.critical(e)

    for comm in journalComments:
        foundComments.append(comm.text)

    return foundComments


def logCommentsToFile(comments: List):
    with open('.usedcomments', 'a') as file:
        for comment in comments:
            file.write(comment)
            file.write('\n')


def loadCommentsFromFile() -> List[str]:
    comments = []
    if os.path.exists('.usedcomments'):
        with open('.usedcomments', 'r') as file:
            for line in file:
                comments.append(line)
        return comments
    else:
        logger.warning('No logged comments file was found')
        return []


def filterUsedComments(foundComments: List, loggedComments: List) -> List[str]:
    loggedComments = [comm.strip() for comm in loggedComments]
    newComments = [comm for comm in foundComments if comm not in loggedComments]
    return newComments


def runBot(messages: List[str]):
    '''Start up the discord bot'''
    client = discord.Client()
    try:
        logger.debug('Attempting to load Discord API key')
        logger.debug('Discord token loaded')
    except IndexError:
        logger.critical('Discord token could not be found')
        exit(1)

    @client.event
    async def on_ready():
        await client.wait_until_ready()
        logger.debug('Discord client ready')
        channelid = int(os.getenv('DISCORD_CHANNEL'))
        channel = client.get_channel(channelid)

        for message in messages:
            logger.debug('Sending message')
            await channel.send(message)

        logger.info('Logging Discord bot out')
        await client.logout()

    logger.debug('Starting Discord client')
    secret = os.getenv('DISCORDTOKEN')
    client.run(secret)

    logger.debug('Discord client closed')


if __name__ == "__main__":
    args = parser.parse_args()
    logger.info('Getting FA page')
    foundNotes = parseFANotesPage(getFAPage(args.cookies, 'https://www.furaffinity.net/msg/pms/'))
    foundNotifications = parseFAMessagePage(getFAPage(args.cookies, 'https://www.furaffinity.net/msg/others/'))

    newNotifs = foundNotifications + foundNotes
    newNotifs = filterUsedComments(newNotifs, loadCommentsFromFile())

    if newNotifs:
        logger.info('New comments found')
        runBot(newNotifs)
        logCommentsToFile(newNotifs)
        logger.debug('Comments written to file')
    else:
        logger.info('No new comments found')
    logger.info('Script complete')

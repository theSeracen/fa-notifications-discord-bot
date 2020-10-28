#!/usr/bin/env python3

import argparse
import http.cookiejar
import logging
import os
import pathlib
import re
import sys
import time
from typing import List

import bs4
import discord
import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()


def getFAPage(cookieloc: str, url: str) -> str:
    '''Get the notifications page on FurAffinity'''
    logger.debug('Attempting to load cookies')
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj
    logger.debug('Cookies loaded')

    try:
        page = s.get(url)
    except requests.ConnectionError:
        logger.error('Failed to get page {}, retrying in 60 seconds'.format(url))
        time.sleep(60)
        try:
            page = s.get(url)
        except requests.ConnectionError as e:
            logger.critical('Failed to get page {}: {}'.format(url, e))
            raise e

    logger.debug('FA page received')
    return page.content


def parseFANotesPage(page: bytes) -> List[str]:
    '''Find the unread notes on the page'''
    soup = bs4.BeautifulSoup(page, 'html.parser')

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
        logger.info('{} submission comments found'.format(len(subComments)))
        foundComments = [comm.text for comm in subComments]
    except AttributeError as e:
        logger.info('No submission comments found')
    except Exception as e:
        logger.critical(e)

    journalComments = []
    try:
        logger.debug('Attempting to find journal comments')
        comments = soup.find('section', {'id': 'messages-comments-journal'})
        journalComments = comments.find('div', {'class': 'section-body js-section'}
                                        ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.info('{} journal comments found'.format(len(journalComments)))
    except AttributeError:
        logger.info('No journal comments found')
    except Exception as e:
        logger.critical(e)

    shouts = []
    try:
        logger.debug('Attempting to find shouts')
        comments = soup.find('section', {'id': 'messages-shouts'})
        shouts = comments.find('div', {'class': 'section-body js-section'}
                               ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.info('{} shouts found'.format(len(shouts)))
    except AttributeError:
        logger.info('No shouts found')
    except Exception as e:
        logger.critical(e)

    foundComments.extend([comm.text for comm in journalComments])
    foundComments.extend([shout.text for shout in shouts])

    return foundComments


def logCommentsToFile(comments: List):
    with open('.usedcomments', 'a') as file:
        for comment in comments:
            file.write(comment)
            file.write('\n')


def loadCommentsFromFile() -> List[str]:
    comments = []
    if pathlib.Path('.usedcomments').exists():
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
        sys.exit(1)

    @client.event
    async def on_ready():
        await client.wait_until_ready()
        logger.debug('Discord client ready')

        try:
            channelid = int(os.getenv('DISCORD_CHANNEL'))
        except ValueError:
            logger.critical('Invalid channel ID given, must be integer: {}'.format(os.getenv('DISCORD_CHANNEL')))
            sys.exit(1)

        channel = client.get_channel(channelid)

        for message in messages:
            logger.debug('Sending message')
            await channel.send(message)

        logger.info('Logging Discord bot out')
        await client.logout()

    logger.debug('Starting Discord client')
    secret = os.getenv('DISCORDTOKEN')
    client.run(secret)


if __name__ == "__main__":
    parser.add_argument('cookies', help='the cookies file')
    parser.add_argument('-v', '--verbose', default=0, action='count')

    logger = logging.getLogger()
    logger.setLevel(1)
    stream = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] - %(message)s')
    stream.setFormatter(formatter)
    stream.setLevel(logging.INFO)
    logger.addHandler(stream)

    args = parser.parse_args()

    if args.verbose > 0:
        stream.setLevel(logging.DEBUG)

    args.cookies = pathlib.Path(args.cookies).resolve()
    if not args.cookies.exists():
        raise Exception('Cannot find cookies file')

    logger.info('Getting FA page')
    foundNotes = parseFANotesPage(getFAPage(args.cookies, 'https://www.furaffinity.net/msg/pms/'))
    foundNotifications = parseFAMessagePage(getFAPage(args.cookies, 'https://www.furaffinity.net/msg/others/'))

    newNotifs = foundNotifications + foundNotes
    newNotifs = filterUsedComments(newNotifs, loadCommentsFromFile())

    if newNotifs:
        logger.info('New notifications found')
        runBot(newNotifs)
        logCommentsToFile(newNotifs)
        logger.debug('Notifications written to file')
    else:
        logger.info('No new notifications found')

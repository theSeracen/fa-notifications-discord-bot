#!/usr/bin/env python3

import argparse
import http.cookiejar
import logging
import os
import pathlib
import re
import sys
import time

import bs4
import discord
import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()
logger = logging.getLogger()


def getFAPage(cookieloc: str, url: str) -> str:
    """Get the notifications page on FurAffinity"""
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
    return page.text


def parseFANotesPage(page: str) -> list[str]:
    """Find the unread notes on the page"""
    soup = bs4.BeautifulSoup(page, 'html.parser')

    unread_notes = []
    notes = soup.findAll('div', {'class': 'message-center-pms-note-list-view'})
    for note in notes:
        if note.find('img', {'class': 'unread'}):
            message = note.text.strip()
            message = re.sub(r'\s+', ' ', message)
            unread_notes.append(message)

    logger.info('{} unread notes found'.format(len(unread_notes)))
    return unread_notes


def parseFAMessagePage(page: str) -> list[str]:
    """Find the comments on the page"""
    soup = bs4.BeautifulSoup(page, 'html.parser')
    found_comments = []

    logger.debug('Attempting to find submission comments')
    try:
        comments = soup.find('section', {'id': 'messages-comments-submission'})
        sub_comments = comments.find('div', {'class': 'section-body js-section'}
                                     ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.info('{} submission comments found'.format(len(sub_comments)))
        found_comments = [comm.text for comm in sub_comments]
    except AttributeError:
        logger.info('No submission comments found')
    except Exception as e:
        logger.critical(e)

    journal_comments = []
    try:
        logger.debug('Attempting to find journal comments')
        comments = soup.find('section', {'id': 'messages-comments-journal'})
        journal_comments = comments.find('div', {'class': 'section-body js-section'}
                                         ).find('ul', {'class': 'message-stream'}).findAll('li')
        logger.info('{} journal comments found'.format(len(journal_comments)))
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

    found_comments.extend([comm.text for comm in journal_comments])
    found_comments.extend([shout.text for shout in shouts])

    return found_comments


def logCommentsToFile(comments: list):
    with open('.usedcomments', 'a') as file:
        for comment in comments:
            file.write(comment)
            file.write('\n')


def loadCommentsFromFile() -> list[str]:
    comments = []
    if pathlib.Path('.usedcomments').exists():
        with open('.usedcomments', 'r') as file:
            for line in file:
                comments.append(line)
        return comments
    else:
        logger.warning('No logged comments file was found')
        return []


def filterUsedComments(found_comments: list, logged_comments: list) -> list[str]:
    logged_comments = [comm.strip() for comm in logged_comments]
    new_comments = [comm for comm in found_comments if comm not in logged_comments]
    return new_comments


def runBot(messages: list[str]):
    """Start up the discord bot"""
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

#!/usr/bin/env python3

import argparse
import http.cookiejar
import logging
import os
import pathlib
import re
import sys

import bs4
import discord
import requests
from dotenv import load_dotenv

load_dotenv()

parser = argparse.ArgumentParser()
logger = logging.getLogger()


def getFAPage(cookieloc: str, url: str) -> str:
    """Get the notifications page on FurAffinity"""
    s = _make_session(cookieloc)
    logger.debug('Cookies loaded')
    try:
        page = s.get(url)
    except Exception as e:
        logger.critical('Failed to get page {}'.format(url))
        raise e
    logger.debug('FA page received')
    return page.text


def _make_session(cookieloc):
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj
    return s


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

    submission_comments = _find_notification_in_page(soup, 'messages-comments-submission')
    logger.info('{} submission comments found'.format(len(submission_comments)))

    journal_comments = _find_notification_in_page(soup, 'messages-comments-journal')
    logger.info('{} journal comments found'.format(len(journal_comments)))

    shouts = _find_notification_in_page(soup, 'messages-shouts')
    logger.info('{} shouts found'.format(len(shouts)))

    found_comments = [comm.text for comm in submission_comments]
    found_comments.extend([comm.text for comm in journal_comments])
    found_comments.extend([shout.text for shout in shouts])

    return found_comments


def _find_notification_in_page(soup: bs4.BeautifulSoup, id_value: str):
    try:
        comments = soup.find('section', {'id': id_value})
        found_notifications = comments.find('div', {'class': 'section-body js-section'}).find(
            'ul', {'class': 'message-stream'}).findAll('li')
    except AttributeError:
        # thrown when nothing is found
        return []
    return found_notifications


def logCommentsToFile(comments: list[str]):
    with open('.usedcomments', 'a') as file:
        file.writelines(comments)


def loadCommentsFromFile() -> list[str]:
    if pathlib.Path('.usedcomments').exists():
        with open('.usedcomments', 'r') as file:
            comments = file.readlines()
        return comments
    else:
        logger.warning('No logged comments were found')
        return []


def filterUsedComments(found_comments: list[str], logged_comments: list[str]) -> list[str]:
    logged_comments = [comm.strip() for comm in logged_comments]
    new_comments = [comm for comm in found_comments if comm not in logged_comments]
    return new_comments


def runBot(messages: list[str]):
    """Start up the discord bot"""
    client = discord.Client()

    @client.event
    async def on_ready():
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
    if secret := os.getenv('DISCORDTOKEN'):
        client.run(secret)
    else:
        raise Exception('Could not load Discord token from environment')


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

    logger.info('Getting FA pages')
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

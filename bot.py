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


def get_fa_page(cookieloc: pathlib.Path, url: str) -> str:
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


def _make_session(cookieloc: pathlib.Path) -> requests.Session:
    cj = http.cookiejar.MozillaCookieJar(cookieloc)
    cj.load()
    s = requests.session()
    s.cookies = cj
    return s


def parse_fa_notes_page(page: str) -> list[str]:
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


def parse_fa_message_page(page: str) -> list[str]:
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


def _find_notification_in_page(soup: bs4.BeautifulSoup, id_value: str) -> list[bs4.Tag]:
    try:
        comments = soup.find('section', {'id': id_value})
        found_notifications = comments.find('div', {'class': 'section-body js-section'}).find(
            'ul', {'class': 'message-stream'}).findAll('li')
    except AttributeError:
        # thrown when nothing is found
        return []
    return found_notifications


def log_comments_to_file(comments_file: pathlib.Path, comments: list[str]):
    with open(comments_file, 'a') as file:
        for comment in comments:
            file.write(comment + '\n')


def load_comments_from_file(comment_file: pathlib.Path) -> list[str]:
    if comment_file.exists():
        with open(comment_file, 'r') as file:
            comments = file.readlines()
        return comments
    else:
        return []


def filter_used_comments(found_comments: list[str], logged_comments: list[str]) -> list[str]:
    logged_comments = [comm.strip() for comm in logged_comments]
    new_comments = [comm for comm in found_comments if comm not in logged_comments]
    return new_comments


def run_bot(messages: list[str]):
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


def _setup_logging(verbosity: int):
    logger.setLevel(1)
    stream = logging.StreamHandler(sys.stdout)
    if verbosity > 0:
        stream.setLevel(logging.DEBUG)
    formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s] - %(message)s')
    stream.setFormatter(formatter)
    stream.setLevel(logging.INFO)

    logging.getLogger('discord').setLevel(logging.ERROR)

    logger.addHandler(stream)


def _setup_arguments():
    parser.add_argument('cookies', help='the cookies file')
    parser.add_argument('-v', '--verbose', default=0, action='count')
    parser.add_argument('-l', '--comments-log-file', default='.usedcomments')
    parser.add_argument('-d', '--discord', action='store_true')


def main(args: argparse.Namespace):
    _setup_logging(args.verbose)

    args.cookies = pathlib.Path(args.cookies).resolve()
    args.comments_log_file = pathlib.Path(args.comments_log_file).resolve()
    if not args.cookies.exists():
        logger.critical('Cannot find cookies file')
        sys.exit(1)
    if not args.comments_log_file.exists():
        logger.warning('Cannot find previous notifications log')

    logger.info('Getting FA pages')
    found_notes = parse_fa_notes_page(get_fa_page(args.cookies, 'https://www.furaffinity.net/msg/pms/'))
    found_notifications = parse_fa_message_page(get_fa_page(args.cookies, 'https://www.furaffinity.net/msg/others/'))
    new_notifs = found_notifications + found_notes
    new_notifs = filter_used_comments(new_notifs, load_comments_from_file(args.comments_log_file))

    if new_notifs:
        logger.info('New notifications found')
        if args.discord:
            run_bot(new_notifs)
        log_comments_to_file(args.comments_log_file, new_notifs)
        logger.debug('Notifications written to file')
    else:
        logger.info('No new notifications found')


if __name__ == "__main__":
    _setup_arguments()
    args = parser.parse_args()
    main(args)

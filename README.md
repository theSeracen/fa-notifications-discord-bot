# FurAffinity Bot for Notes and Comments Notifications

This is a bot to send notifications to a Discord server when there is a new comment or note on an FA account. This allows someone to schedule the bot to run regularly so that they receive notifications for communication on FA regularly and in an automated fashion, without having to check the FurAffinity site itself.

## Arguments and Options

There are the following arguments and options:

- `cookies`, a cookies file for the account to be checked
- `-v,--verbose`

## .env File

The program operates by loading several variables from an `.env` file. These variables are what specify the channel for the bot to post in, as well as the API key required by Discord for the bot to work. The following variables need to be specified in this file:

- `DISCORD_CHANNEL`
- `DISCORDTOKEN`

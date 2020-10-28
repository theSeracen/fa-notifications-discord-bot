# FurAffinity Bot for Notes and Comments Notifications

This is a bot to send notifications to a Discord server when there is a new comment or note on an FA account. This allows someone to schedule the bot to run regularly so that they receive notifications for communication on FA regularly and in an automated fashion, without having to check the FurAffinity site itself. The following notifications are checked:

- Notes
- Submission Comments and Replies
- Journal Comments
- Shouts

Due to the nature of the notifications, it is recommended that a private server be used to create a space where the bot can send messages. Additionally a Discord bot will need to be created so that the token can be supplied to this bot, giving it the ability to send messages to the designated server channel.

## Arguments and Options

There are the following arguments and options:

- `cookies`, a cookies file for the account to be checked
- `-v,--verbose`

## .env File

The program operates by loading several variables from an `.env` file. These variables are what specify the channel for the bot to post in, as well as the API key required by Discord for the bot to work. The following variables need to be specified in this file:

- `DISCORD_CHANNEL`
- `DISCORDTOKEN`

# varna

This is software as a fork of https://github.com/orbitalimpact/hipmost, but a bit better and on Python2 (sorry, I like this language).
The most important difference from Hipmost is:
- You need a bit more preparing for well-done Mattermost-import;
- You'll import almost full HipChat export;
- With attachments or not - it's your choice;
- You'll have an ability to incremental import if you have been imported the first version and it looks like you wanted to migrate fully;
- The Mattermost import is correct, you don't need to think about the format or some restrictions from the Mattermost;
- The users will be added to some public channels if the public channel contains over 1000 messages or if the user wrote to in the last 3 months;
- Skip messages over 16383 symbols;
- Skip images if the heigh or width over 5000 pixels;
- Skip attachment if there isn't file on the disk;
- There is some hacks for converting special symbols from the rooms names to suitable.

The convertation process contains some stages. Firstly you have to prepare the source files.
In the repository there is a script for preparing additional file with the Crowd users - export.sh.

The main stages of convertation process:
1. Make a json with relationship of user and public rooms:
`python varna.py --team=Your_default_team --type=public_room_users`

2. Make a users jsonl:
`python varna.py --team=Your_default_team --type=users`

3. Make a channels jsonl:
`python varna.py --team=Your_default_team --type=channels`

4. Make a jsonl from the export of rooms (Public and Private channels):
`python varna.py --team=Your_default_team --type=history_rooms`

5. Make a jsonl from the export of users history (Direct channels):
`python varna.py --team=Your_default_team --type=direct_posts`

Jsonl files by the channel's (direct, private, public) history could be generated with or without attachments as well as an incremental option.

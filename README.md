# 24HS-Bot
A custom Discord Bot written in Python that helps with tech support!

## Features
 * Support commands (as Slash Commands):  
   Commands are read from the 'commands' directory by default (which can be configured, more on that in a bit).  
   The format is as follows:
    * Filename -> Command name (so "cleanboot.txt" would create a "/cleanboot" command)
    * First line -> Command description (displayed below the command in the commands list when pressing / in Discord)
    * Any lines after that -> Command text (which gets sent by the bot when the command is ran)
 * `msinfo32` parsing:  
   When a file exported by msinfo32 is sent into any channel the bot can see, it offers to parse the file. Only users with certain roles are allowed to answer this prompt (the role list is again freely configurable).
    * If "Yes" is selected, important information is read from the file and presented using Embeds. Windows and NVIDIA GPU driver versions are also checked and, if out-of-date, a 2nd "Quick Fixes" embed is created. Lastly, the file gets converted to utf-8, since some editors (especially on Linux) struggle with utf-16 text
    * If "No" is selected or a 10 minute timeout is reached, the bots message is deleted (to not clog up the chat).

## Configuration/Setup
Configuration is done in the bots `const.py` file.  
To first run the bot, you'll have to paste in your bot token into the `bot_token` variable. The commands dir, the roles that can interact with the `msinfo32` prompt, and the Embed color can also be configured there.

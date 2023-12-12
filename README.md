# 24HourSupportBot


## Usage
### Intended Users
Those willing to download the repo, configure plugins as they see fit, and build themselves.

### Bot functions
It's built to be modular with the plugins, such as commands or activities.

Out of the box:
* Supports setting bot activities
* Settings are saved in the bot_config.json file
* Supports commands (as Slash Commands)
* Commands are read from the 'commands.json' file
* Built-in commands:
    * add-command - provides a GUI for adding a new command, will be saved to commands.json
    * edit-command - provides a GUI for editing an existing command, changes will update commands.json
    * stop - halts all bot processes and scripts, shuts down the bot

Example bot_config.json:
``` json
{
    "botToken":"botID",
    "slashCommands":{"admins":["userID"]},
    "activity":{"type":2, "name":"Music"}
}
```
## Troubleshooting
If a command is formatted improperly, it will not load. If a command is added to commands.json without using the built-in add-command function or is malformed when being added, the following structure should be used for fixing the commands.json:
* commands - An array containing multiple commands
* Each command needs the following:
    * name - A non-empty string
    * description - A non-empty string
    * response - The response to send in the channel
    * imageAttachments - Any images to send with response
    * videoAttachments - Any videos to send with response

Example command:
``` json
{
  "commands":[
    {
    "name": "say-hi",
    "description": "Says Hi",
    "response": "Hi",
    "imageAttachments": [],
    "videoAttachments": []
  }]
}
```

## Contributing
Decent documentation on how to read the code and various concepts: https://sabe.io/tutorials/how-to-build-discord-bot-typescript

Scripts are available for building and running

```npm run build```
* Builds the project to the build/ directory 

```npm start```
* Runs the build command then starts the bot

```npm run dist```
* Runs the build and packages the bot to the dist/ directory

```npm run clean```
* Removes both dist and build directories

```npm run codecheck```
* Runs tsc

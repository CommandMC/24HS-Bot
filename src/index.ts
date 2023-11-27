import { readFile, access, writeFile } from 'fs/promises'
import { Client, GatewayIntentBits } from 'discord.js'

import { Settings } from './schemas'
import { logCritical, logError, logInfo, logWarning } from './logger'
import enabledPlugins from './plugins/index'

const CONFIG_FILE_NAME = 'bot_config.json'

async function readSettings(): Promise<Settings | null> {
  let settings
  try {
    const settingsString = await readFile(CONFIG_FILE_NAME, 'utf-8').catch(
      () => '{}'
    )
    settings = Settings.parse(JSON.parse(settingsString))
  } catch (e) {
    try {
      await access(CONFIG_FILE_NAME)
      logCritical(
        `Failed to parse settings file (${CONFIG_FILE_NAME}), is it valid JSON? Does it contain a botToken?`
      )
    } catch {
      logCritical(`Config file (${CONFIG_FILE_NAME}) does not exist`)
      await writeFile(CONFIG_FILE_NAME, JSON.stringify({}))
    }
    return null
  }
  return settings
}

async function main() {
  const settings = await readSettings()
  if (!settings) return
  const client = new Client({
    intents: [
      GatewayIntentBits.Guilds,
      GatewayIntentBits.GuildMessages,
      GatewayIntentBits.MessageContent
    ]
  })

  client.once('ready', async (client) => {
    await Promise.allSettled(
      enabledPlugins.map((plugin) => plugin.init(client, settings))
    )
    logInfo('Plugin init complete, welcome! Logged in as', client.user.tag)
  })

  client.on('warn', logWarning)
  client.on('error', logError)

  await client.login(settings.botToken)
}

main().catch(logError)

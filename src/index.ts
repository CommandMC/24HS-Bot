import { Client, GatewayIntentBits } from 'discord.js'

import { logError, logInfo, logWarning } from './logger'
import { readSettings } from './settings'

import enabledPlugins from './plugins/index'

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

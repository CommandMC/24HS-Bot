import { readSettings } from '../src/settings'
import { Client, GatewayIntentBits, Routes } from 'discord.js'

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

  client.once('ready', async () => {
    await client.rest.put(
      Routes.applicationCommands((client as Client<true>).application.id),
      { body: [] }
    )

    const guilds = await client.guilds.fetch()
    await Promise.all(
      guilds.map(async (guild) =>
        client.rest.put(
          Routes.applicationGuildCommands(
            (client as Client<true>).application.id,
            guild.id
          ),
          { body: [] }
        )
      )
    )
    void client.destroy()
  })
  await client.login(settings.botToken)
}

main().catch(console.error)

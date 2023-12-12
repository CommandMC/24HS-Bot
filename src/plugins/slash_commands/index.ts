import { readFile, writeFile } from 'fs/promises'
import {
  ModalBuilder,
  TextInputStyle,
  ComponentType,
  ApplicationCommandOptionType
} from 'discord.js'
import type {
  Client,
  ApplicationCommand,
  ChatInputCommandInteraction,
  APIEmbed,
  InteractionReplyOptions
} from 'discord.js'

import type { Plugin } from '../../types'
import { logError, logWarning } from '../../logger'
import { getApplicationCommands, registerCommand } from '../../helpers'

import { Command, Settings } from './schemas'
import { createTextInput, isAdmin } from './helpers'
import { z } from 'zod'

const name = 'SlashCommands'

const COMMANDS_FILE = 'commands.json'

const commands = new Map<string, Command>()
const upstreamCommands = new Map<string, ApplicationCommand>()

function loadSettings(settings: unknown): Settings | null {
  const result = Settings.safeParse(settings)
  return result.success ? result.data : null
}

/**
 * Loads the list of commands from {@link COMMANDS_FILE}
 */
async function loadCommands(): Promise<boolean> {
  // Strategy here is: First of all verify the general structure of the commands file, then ensure the shape of every
  // command one-by-one. That way, even if one command gets corrupted somehow, we only lose that one command

  const commandListString = await readFile(COMMANDS_FILE, 'utf-8')
  let commandFileParsed: unknown
  try {
    commandFileParsed = JSON.parse(commandListString)
  } catch {}
  const commandFileVerified = z
    .object({
      commands: z.array(z.unknown())
    })
    .safeParse(commandFileParsed)
  if (!commandFileVerified.success) return false

  for (const command of commandFileVerified.data.commands) {
    const parsedCommand = Command.safeParse(command)
    if (!parsedCommand.success) {
      logError('Failed to parse', command)
      continue
    }
    commands.set(parsedCommand.data.name, parsedCommand.data)
  }
  return true
}

async function registerCustomCommand(client: Client<true>, command: Command) {
  const embeds = makeEmbeds(command)
  const videoLinks = command.videoAttachments.join('\n')
  const handler = async (interaction: ChatInputCommandInteraction) => {
    const messages: (string | InteractionReplyOptions)[] = []
    if (embeds.length)
      messages.push({
        embeds
      })
    if (videoLinks) messages.push(videoLinks)

    const message1 = messages.shift()
    if (message1) await interaction.reply(message1)
    const message2 = messages.shift()
    if (message2) await interaction.followUp(message2)
  }
  const addedCommand = await registerCommand(
    client,
    command.name,
    command.description,
    handler,
    {
      cache: Array.from(upstreamCommands.values())
    }
  )
  commands.set(command.name, command)
  upstreamCommands.set(command.name, addedCommand)
}

/**
 * Creates the response (consisting of one or more embeds) for a given command
 * @param command
 */
function makeEmbeds(command: Command): APIEmbed[] {
  // Some commands only have video attachments, in this case we don't have
  // any embeds to send
  if (!command.imageAttachments.length && !command.response) return []

  // Add as many embeds as there are images for this command. If there are none,
  // add at least one for the description
  const embedsToAdd = command.imageAttachments.length || 1

  const embeds: APIEmbed[] = []
  embeds.length = embedsToAdd
  embeds.fill({})

  // Add the description to the first embed
  const firstEmbed: APIEmbed = {}
  firstEmbed.description = command.response
  embeds[0] = firstEmbed

  // Add images
  command.imageAttachments.forEach((imageUrl, index) => {
    const currentEmbed = embeds[index]
    // NOTE: This can't really happen (since the array is filled above)
    if (!currentEmbed) return
    currentEmbed.image = { url: imageUrl }
    embeds[index] = currentEmbed
  })

  // NOTE: You'd expect the videos to be added here as well, however Discord
  //       does not allow setting the `video` tag on embeds yourself
  /*
  command.videoAttachments.forEach((videoUrl, index) => {
    const currentEmbed = embeds[index]
    if (!currentEmbed) return
    currentEmbed.video = { url: videoUrl }
    embeds[index] = currentEmbed
  })
  */

  return embeds
}

function getCommandInputs() {
  const titleInput = createTextInput('commandName', 'Command Name')
  const descriptionInput = createTextInput(
    'commandDescription',
    'Description',
    'One-line description shown in the command list'
  )
  const responseInput = createTextInput(
    'commandResponse',
    'Response',
    "Response text that'll be sent by the bot",
    TextInputStyle.Paragraph,
    false
  )
  const imageAttachmentsInput = createTextInput(
    'commandImages',
    'Image Attachments',
    'Any images that should be attached to the response message; image URLs, one per line',
    TextInputStyle.Paragraph,
    false
  )
  const videoAttachmentsInput = createTextInput(
    'commandVideos',
    'Video Attachments',
    'Any videos that should be attached to the response message; video URLs, one per line',
    TextInputStyle.Paragraph,
    false
  )
  return {
    titleInput,
    descriptionInput,
    responseInput,
    imageAttachmentsInput,
    videoAttachmentsInput
  }
}

/**
 * Takes a modal response (from either `add-command` or `edit-command`) and builds a {@link Command} based on it
 * @param interaction The interaction that just sent the modal
 * @param idToWaitFor The id of the modal
 * @param commandName The command name; known for `edit-command`, unknown for `add-command`
 */
async function addOrModifyCommandFromModal(
  interaction: ChatInputCommandInteraction,
  idToWaitFor: string | undefined,
  commandName?: string
) {
  const modalResponse = await interaction
    .awaitModalSubmit({
      time: 1000 * 60 * 20,
      filter: (i) =>
        i.customId === idToWaitFor && i.user.id === interaction.user.id
    })
    // This catch is invoked if the user either cancels the modal or takes longer than `time` to reply
    // In this case, we just want to do nothing then
    .catch(() => null)
  if (!modalResponse) return {}

  // Helper function to get a field (this needs to be done below a few times)
  const getField = (id: string) =>
    modalResponse.fields.getField(id, ComponentType.TextInput).value

  const newCommand: Command = {
    name: commandName ?? getField('commandName'),
    description: getField('commandDescription'),
    response: getField('commandResponse'),
    imageAttachments: getField('commandImages').split('\n').filter(Boolean),
    videoAttachments: getField('commandVideos').split('\n').filter(Boolean)
  }
  await registerCustomCommand(modalResponse.client, newCommand)
  // Write the modified command list to disk
  await writeFile(
    COMMANDS_FILE,
    JSON.stringify({ commands: Array.from(commands.values()) }, undefined, 2)
  )
  return { submitInteraction: modalResponse, newCommand }
}

/**
 * Handler for the `add-command` command
 */
async function addNewCommand(
  interaction: ChatInputCommandInteraction,
  settings: Settings['slashCommands']
): Promise<void> {
  if (!isAdmin(interaction, settings)) {
    await interaction.reply({
      content: 'You are not authorized to add commands!',
      ephemeral: true
    })
    return
  }

  const commandInputModal = new ModalBuilder()
    .setCustomId(`addCommand-${Date.now()}`)
    .setTitle('Add a new Embed command')

  const inputs = getCommandInputs()

  commandInputModal.addComponents(...Object.values(inputs))

  await interaction.showModal(commandInputModal)
  const { submitInteraction, newCommand } = await addOrModifyCommandFromModal(
    interaction,
    commandInputModal.data.custom_id
  )
  if (submitInteraction)
    await submitInteraction.reply({
      content: `Added new command \`/${newCommand.name}\`, your client might need a reload for it to show up`,
      ephemeral: true
    })
}

/**
 * Handler for the `edit-command` command
 */
async function editCommand(
  interaction: ChatInputCommandInteraction,
  settings: Settings['slashCommands']
) {
  if (!isAdmin(interaction, settings)) {
    await interaction.reply({
      content: 'You are not authorized to modify commands!',
      ephemeral: true
    })
    return
  }

  const commandName = interaction.options.getString('command-name', true)
  const commandObj = commands.get(commandName)
  if (!commandObj) {
    await interaction.reply({
      content: `The command you provided (\`/${commandName}\`) does not exist`,
      ephemeral: true
    })
    return
  }

  const commandEditModal = new ModalBuilder()
    .setCustomId(`editCommand-${Date.now()}`)
    .setTitle(`Editing ${commandName}`)

  const {
    descriptionInput,
    responseInput,
    imageAttachmentsInput,
    videoAttachmentsInput
  } = getCommandInputs()
  descriptionInput.components[0]?.setValue(commandObj.description)
  responseInput.components[0]?.setValue(commandObj.response)
  imageAttachmentsInput.components[0]?.setValue(
    commandObj.imageAttachments.join('\n')
  )
  videoAttachmentsInput.components[0]?.setValue(
    commandObj.videoAttachments.join('\n')
  )

  commandEditModal.addComponents(
    descriptionInput,
    responseInput,
    imageAttachmentsInput,
    videoAttachmentsInput
  )
  await interaction.showModal(commandEditModal)
  const { submitInteraction, newCommand } = await addOrModifyCommandFromModal(
    interaction,
    commandEditModal.data.custom_id,
    commandName
  )
  if (submitInteraction)
    await submitInteraction.reply({
      content: `Edited command \`/${newCommand.name}\``,
      ephemeral: true
    })
}

async function stopBot(
  interaction: ChatInputCommandInteraction,
  settings: Settings['slashCommands']
) {
  if (!isAdmin(interaction, settings)) {
    await interaction.reply({
      content: 'You are not authorized to stop the bot!',
      ephemeral: true
    })
    return
  }
  await interaction.reply({
    content: 'Calling `client.destroy`, goodbye',
    ephemeral: true
  })
  void interaction.client.destroy()
}

const init: Plugin['init'] = async (client, generalSettings) => {
  const settings = loadSettings(generalSettings)
  if (!settings) {
    logError(`${name}:`, 'Settings malformed, not adding/handling commands!')
    return
  }

  await loadCommands()
  if (!commands.size) {
    logWarning(`${name}:`, 'No custom commands found')
  }

  const currentCommands = await getApplicationCommands(client)
  currentCommands.forEach((command) =>
    upstreamCommands.set(command.name, command)
  )

  await Promise.allSettled([
    ...Array.from(commands.values()).map((command) =>
      registerCustomCommand(client, command)
    ),
    registerCommand(
      client,
      'add-command',
      'Add a new Embed command',
      (interaction) => addNewCommand(interaction, settings.slashCommands),
      { cache: currentCommands }
    ),
    registerCommand(
      client,
      'edit-command',
      'Edit an existing Embed command',
      (interaction) => editCommand(interaction, settings.slashCommands),
      {
        cache: currentCommands,
        options: [
          {
            type: ApplicationCommandOptionType.String,
            name: 'command-name',
            description: 'The name of the command you want to edit',
            required: true
          }
        ]
      }
    ),
    registerCommand(
      client,
      'stop',
      'Shut down the bot',
      (interaction) => stopBot(interaction, settings.slashCommands),
      { cache: currentCommands }
    )
  ])
}

export default { name, init }

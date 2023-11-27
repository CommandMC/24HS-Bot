import { ApplicationCommandType, Routes } from 'discord.js'
import type {
  ApplicationCommand,
  ChatInputCommandInteraction,
  Client,
  Interaction,
  PermissionsBitField,
  ApplicationCommandOption
} from 'discord.js'

import { logDebug, logError, logInfo } from './logger'

interface AddOrPatchOptions {
  permissions?: PermissionsBitField
  options?: ApplicationCommandOption[]
}

async function addCommand(
  client: Client<true>,
  name: string,
  description: string,
  { permissions, options }: AddOrPatchOptions = {}
) {
  return (await client.rest.post(
    Routes.applicationCommands(client.application.id),
    {
      body: {
        type: ApplicationCommandType.ChatInput,
        name,
        description,
        default_member_permissions: permissions,
        options
      }
    }
  )) as ApplicationCommand
}

async function patchCommand(
  client: Client<true>,
  commandId: string,
  description: string,
  { permissions, options }: AddOrPatchOptions = {}
) {
  return (await client.rest.patch(
    Routes.applicationCommand(client.application.id, commandId),
    {
      body: {
        type: ApplicationCommandType.ChatInput,
        description,
        default_member_permissions: permissions,
        options
      }
    }
  )) as ApplicationCommand
}

function arrayEquals<T>(
  arr1: T[],
  arr2: T[],
  checkFunc: (val1: T, val2: T) => boolean = (val1, val2) => val1 === val2
): boolean {
  if (arr1.length !== arr2.length) return false
  return arr1.every((value1, index) => {
    const value2 = arr2[index]
    // NOTE: This can't happen, since we verify the length above
    if (!value2) return false
    return checkFunc(value1, value2)
  })
}

interface RegisterCommandOptions extends AddOrPatchOptions {
  cache?: ApplicationCommand[]
}

const registeredHandlers = new Map<
  string,
  (interaction: ChatInputCommandInteraction) => Promise<unknown>
>()
let hasAddedListener = false

function addListenerIfNecessary(client: Client<true>) {
  if (hasAddedListener) return
  const listener = async (interaction: Interaction) => {
    if (!interaction.isChatInputCommand()) return
    const name = interaction.commandName
    logInfo(`Command /${name} ran by ${interaction.user.username}`)
    const handler = registeredHandlers.get(name)
    if (handler) {
      await handler(interaction)
    } else {
      logError(`Command /${name} has no handler?`)
      await interaction.reply('Unknown command, how did you get here?')
    }
  }
  client.on('interactionCreate', listener)
  hasAddedListener = true
}

/**
 * Adds or overwrites a Chat Input command
 * @param client The client the command is added to
 * @param name The name of the command to add
 * @param description The description of the command to add
 * @param handler The function that gets executed when the command is executed
 * @param permissions The default permissions
 * @param cache A cache for the client's already-added commands, to avoid fetching them again
 * @param options The command's options (parameters)
 * @returns ApplicationCommand The created/modified command
 */
export async function registerCommand(
  client: Client<true>,
  name: string,
  description: string,
  handler: (interaction: ChatInputCommandInteraction) => Promise<unknown>,
  { permissions, cache, options }: RegisterCommandOptions = {}
): Promise<ApplicationCommand> {
  logInfo(`Registering command /${name}`)
  // Add/Update the command
  const alreadyAddedCommands = cache ?? (await getApplicationCommands(client))

  const alreadyAddedCommand = alreadyAddedCommands.find(
    ({ name: potName }) => potName === name
  )
  let newlyAddedOrModifiedCommand: ApplicationCommand
  if (alreadyAddedCommand) {
    // If a command with this name already exists, only patch the
    // properties of it (if necessary)
    const commandDidChange =
      alreadyAddedCommand.description !== description ||
      alreadyAddedCommand.defaultMemberPermissions !== permissions ||
      !arrayEquals(
        // NOTE: Type definitions seem to be wrong here, this can be `undefined`
        // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
        alreadyAddedCommand.options ?? [],
        options ?? [],
        // FIXME: Add a dedicated compare function here
        (val1, val2) => JSON.stringify(val1) === JSON.stringify(val2)
      )
    if (commandDidChange) {
      logDebug(`Patching command /${name}`)
      newlyAddedOrModifiedCommand = await patchCommand(
        client,
        alreadyAddedCommand.id,
        description,
        { permissions, options }
      )
    } else {
      logDebug(`Command /${name} did not change`)
      newlyAddedOrModifiedCommand = alreadyAddedCommand
    }
  } else {
    logDebug(`Adding new command /${name}`)
    // If we don't have a command with this name, add a new one
    newlyAddedOrModifiedCommand = await addCommand(client, name, description, {
      permissions,
      options
    })
  }

  addListenerIfNecessary(client)

  registeredHandlers.set(name, handler)

  return newlyAddedOrModifiedCommand
}

export async function getApplicationCommands(client: Client<true>) {
  return (await client.rest.get(
    Routes.applicationCommands(client.application.id)
  )) as ApplicationCommand[]
}

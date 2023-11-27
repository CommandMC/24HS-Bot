import { ActionRowBuilder, TextInputBuilder, TextInputStyle } from 'discord.js'
import type { ChatInputCommandInteraction } from 'discord.js'

import type { Settings } from './schemas'

export function createTextInput(
  customId: string,
  label: string,
  placeholder = '',
  style = TextInputStyle.Short,
  required = true,
  value = ''
) {
  return new ActionRowBuilder<TextInputBuilder>().addComponents(
    new TextInputBuilder()
      .setCustomId(customId)
      .setLabel(label)
      .setPlaceholder(placeholder)
      .setStyle(style)
      .setRequired(required)
      .setValue(value)
  )
}

export function isAdmin(
  interaction: ChatInputCommandInteraction,
  settings: Settings['slashCommands']
) {
  return settings.admins.includes(interaction.user.id)
}

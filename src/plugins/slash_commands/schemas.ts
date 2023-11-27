import { z } from 'zod'

import { NonEmptyString } from '../../schemas'

export const Command = z.object({
  name: NonEmptyString,
  description: NonEmptyString,
  response: z.string(),
  imageAttachments: z.array(z.string().url()),
  videoAttachments: z.array(z.string().url())
})
export type Command = z.infer<typeof Command>

export const Settings = z.object({
  slashCommands: z.object({
    admins: z.array(z.string()).min(1)
  })
})
export type Settings = z.infer<typeof Settings>

import type { Client } from 'discord.js'

import type { Settings } from './schemas'

export interface Plugin {
  name: string
  init: (client: Client<true>, settings: Settings) => unknown
}

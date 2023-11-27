import { z } from 'zod'
import { ActivityType } from 'discord.js'

import { logInfo } from '../../logger'
import type { Plugin } from '../../types'

const name = 'SetActivity'

const ZActivityType = z.union([
  z.literal(ActivityType.Playing),
  z.literal(ActivityType.Streaming),
  z.literal(ActivityType.Listening),
  z.literal(ActivityType.Watching),
  z.literal(ActivityType.Competing)
])

const ActivitySettings = z.object({
  activity: z.object({
    type: ZActivityType,
    name: z.string(),
    url: z.string().optional()
  })
})

const init: Plugin['init'] = (client, settings) => {
  const activitySettingsParse = ActivitySettings.safeParse(settings)
  if (!activitySettingsParse.success) {
    logInfo([
      `${name}:`,
      'Activity settings not specified/malformed, deactivating'
    ])
    return
  }
  const activitySettings = activitySettingsParse.data

  client.user.setActivity(activitySettings.activity)
}

export default { name, init }

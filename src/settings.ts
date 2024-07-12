import { access, readFile, writeFile } from 'fs/promises'

import { logCritical } from './logger'
import { Settings } from './schemas'

const CONFIG_FILE_NAME = 'bot_config.json'

export async function readSettings(): Promise<Settings | null> {
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

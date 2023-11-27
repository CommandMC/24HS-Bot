import type { Plugin } from '../types'

import activity from './activity/index'
import slash_commands from './slash_commands/index'

const enabledPlugins: Plugin[] = [activity, slash_commands]

export default enabledPlugins

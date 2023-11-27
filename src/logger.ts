function toLoggableString(message: unknown): string {
  if (Array.isArray(message)) return message.map(toLoggableString).join(' ')
  if (message instanceof Error)
    return message.stack ?? `${message.name}: ${message.message}`
  if (
    message === null ||
    message === undefined ||
    typeof message === 'boolean' ||
    typeof message === 'number' ||
    typeof message === 'bigint' ||
    typeof message === 'string'
  )
    return `${message}`
  return JSON.stringify(message)
}

function logBase(
  level: string,
  logFunc = console.log
): (...message: unknown[]) => void {
  return (...message) => {
    logFunc(`[${level}]`, toLoggableString(message))
  }
}

export const logDebug = logBase('Debug')
export const logInfo = logBase('Info')
export const logWarning = logBase('Warning', console.warn)
export const logError = logBase('Error', console.error)
export const logCritical = logBase('Critical', console.error)

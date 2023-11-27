import { z } from 'zod'

export const NonEmptyString = z.string().superRefine((arg, ctx) => {
  if (arg.length < 1)
    ctx.addIssue({
      code: 'too_small',
      type: 'string',
      minimum: 1,
      inclusive: true
    })
})
export type NonEmptyString = z.infer<typeof NonEmptyString>

export const Settings = z
  .object({
    botToken: NonEmptyString
  })
  .passthrough()
export type Settings = z.infer<typeof Settings>

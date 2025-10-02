import { Store } from '@tanstack/store'

export const authStore = new Store({
  accessToken: null as string | null,
})

export function setAccessToken(token: string | null) {
  authStore.setState((s) => ({ ...s, accessToken: token }))
}

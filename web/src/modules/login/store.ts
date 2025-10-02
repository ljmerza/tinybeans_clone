import { Store } from '@tanstack/store'

const ACCESS_TOKEN_KEY = 'access_token'

// Load initial token from localStorage
function loadToken(): string | null {
  try {
    return localStorage.getItem(ACCESS_TOKEN_KEY)
  } catch {
    return null
  }
}

// Save token to localStorage
function saveToken(token: string | null) {
  try {
    if (token) {
      localStorage.setItem(ACCESS_TOKEN_KEY, token)
    } else {
      localStorage.removeItem(ACCESS_TOKEN_KEY)
    }
  } catch (error) {
    console.error('Failed to save token to localStorage:', error)
  }
}

export const authStore = new Store({
  accessToken: loadToken(),
})

export function setAccessToken(token: string | null) {
  authStore.setState((s) => ({ ...s, accessToken: token }))
  saveToken(token)
}

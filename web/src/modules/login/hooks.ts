import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from '@tanstack/react-router'
import { api, refreshAccessToken } from './client'
import { setAccessToken, authStore } from './store'

export function useMe() {
  return useQuery({
    queryKey: ['auth', 'me', authStore.state.accessToken],
    queryFn: async () => {
      await refreshAccessToken()
      const data = await api.get<{ user: any }>('/users/me/')
      return data.user
    },
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}

export function useLogin() {
  const qc = useQueryClient()
  const navigate = useNavigate()
  
  return useMutation({
    mutationFn: async (body: { username: string; password: string }) => {
      // Clear any existing auth token before attempting login
      // This prevents 403 errors when user already has a valid token but wants to re-login
      setAccessToken(null)
      return api.post<any>('/auth/login/', body)
    },
    onSuccess: (data) => {
      console.log('Login response:', data) // Debug log
      
      // Check if 2FA is required
      if (data.requires_2fa) {
        const verifyData = {
          partialToken: data.partial_token,
          method: data.method,
          message: data.message,
        }
        
        navigate({ 
          to: '/2fa/verify',
          state: verifyData,
        })
      } else if (data.trusted_device) {
        // Trusted device - 2FA was skipped, login successful
        setAccessToken(data.tokens.access)
        qc.invalidateQueries({ queryKey: ['auth'] })
        navigate({ to: '/' })
      } else {
        // Normal login without 2FA
        setAccessToken(data.tokens.access)
        qc.invalidateQueries({ queryKey: ['auth'] })
        navigate({ to: '/' })
      }
    },
    onError: (error) => {
      console.error('Login error:', error) // Debug log
    },
  })
}

export function useSignup() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { username: string; email: string; password: string }) =>
      api.post<{ user: any; tokens: { access: string } }>('/auth/signup/', body),
    onSuccess: (data) => {
      setAccessToken(data.tokens.access)
      qc.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async () => {
      await api.post('/auth/logout/')
      setAccessToken(null)
      return true
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['auth'] })
    },
  })
}

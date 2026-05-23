import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getMe, login, logout, register, type User } from '@/api/auth'

const TOKEN_KEY   = 'gm_token'
const REFRESH_KEY = 'gm_refresh'

export function storeTokens(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access)
  localStorage.setItem(REFRESH_KEY, refresh)
}

export function clearTokens() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_KEY)
}

export function hasToken() {
  return !!localStorage.getItem(TOKEN_KEY)
}

export function useAuth() {
  const qc = useQueryClient()
  const navigate = useNavigate()

  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: ['auth-me'],
    queryFn: async () => {
      if (!hasToken()) return null
      return getMe()
    },
    retry: false,
    staleTime: 60_000,
  })

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      login(email, password),
    onSuccess: (data) => {
      storeTokens(data.access_token, data.refresh_token)
      qc.setQueryData(['auth-me'], data.user)
      navigate('/')
    },
  })

  const registerMutation = useMutation({
    mutationFn: ({
      email,
      password,
      display_name,
    }: {
      email: string
      password: string
      display_name?: string
    }) => register(email, password, display_name),
    onSuccess: (data) => {
      storeTokens(data.access_token, data.refresh_token)
      qc.setQueryData(['auth-me'], data.user)
      navigate('/')
    },
  })

  const logoutMutation = useMutation({
    mutationFn: logout,
    onSettled: () => {
      clearTokens()
      qc.setQueryData(['auth-me'], null)
      navigate('/')
    },
  })

  return {
    user: user ?? null,
    isLoading,
    isAuthenticated: !!user,
    login:    loginMutation,
    register: registerMutation,
    logout:   logoutMutation,
  }
}

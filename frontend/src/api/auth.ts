import api from './client'

export interface User {
  id: number
  email: string
  display_name: string | null
}

export interface AuthResponse {
  user: User
  access_token: string
  refresh_token: string
}

export async function register(
  email: string,
  password: string,
  display_name?: string,
): Promise<AuthResponse> {
  const { data } = await api.post('/auth/register', { email, password, display_name })
  return data
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const { data } = await api.post('/auth/login', { email, password })
  return data
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function getMe(): Promise<User> {
  const { data } = await api.get('/auth/me')
  return data
}

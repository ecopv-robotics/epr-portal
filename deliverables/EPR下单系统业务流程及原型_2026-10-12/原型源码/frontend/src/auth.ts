import type { User } from './types'

export function getUser(): User | null {
  const value = localStorage.getItem('epr_user')
  return value ? JSON.parse(value) as User : null
}

export function isAuthenticated() {
  return Boolean(localStorage.getItem('epr_token'))
}

export function setSession(token: string, user: User) {
  localStorage.setItem('epr_token', token)
  localStorage.setItem('epr_user', JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem('epr_token')
  localStorage.removeItem('epr_user')
}


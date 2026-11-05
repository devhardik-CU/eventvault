import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler } from './api'

const AuthContext = createContext(null)
export const useAuth = () => useContext(AuthContext)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(!getToken()) // if a token exists we must verify it first

  const logout = useCallback(() => { setToken(null); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout) // an expired/invalid token anywhere logs the user out
    if (!getToken()) return
    api.me().then(setUser).catch(() => setToken(null)).finally(() => setReady(true))
  }, [logout])

  const accept = (res) => { setToken(res.access_token); setUser(res.user); return res.user }
  const value = useMemo(() => ({
    user, ready, logout,
    login: async (email, password) => accept(await api.login({ email, password })),
    register: async (data) => accept(await api.register(data)),
  }), [user, ready, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('admin_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    // Neúspešné prihlásenie je tiež 401, ale presmerovať tu nesmieme:
    // reload stránky by zahodil chybovú správu, ktorú chceme adminovi ukázať.
    const isLogin = err.config?.url?.endsWith('/auth/login')

    if (err.response?.status === 401 && !isLogin) {
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_company_slug')
      window.location.href = '/admin/login'
    }
    return Promise.reject(err)
  }
)

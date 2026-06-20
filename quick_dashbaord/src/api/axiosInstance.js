import axios from 'axios'
import toast from 'react-hot-toast'
import { API_BASE_URL } from '@/config/env'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15_000,
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.message || err.message || 'Request failed'
    toast.error(msg, { id: 'api-error' })
    return Promise.reject(err)
  }
)

export default api

import axios from 'axios'

import toast from 'react-hot-toast'

import { API_BASE_URL } from '@/config/env'



const api = axios.create({

  baseURL: API_BASE_URL,

  timeout: 30_000,

  withCredentials: true,

})



api.interceptors.response.use(

  (res) => res,

  (err) => {

    const status = err.response?.status

    const msg = err.response?.data?.message || err.message || 'Request failed'



    if (status === 401) {

      try {

        sessionStorage.removeItem('impact_tracker_user')

      } catch {

        // ignore

      }

      // Avoid redirect loop when already on login

      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {

        window.location.assign('/login')

      }

      return Promise.reject(err)

    }



    toast.error(msg, { id: 'api-error' })

    return Promise.reject(err)

  }

)



export default api


import api from './axiosInstance'
import axios from 'axios'
import { API_BASE_URL } from '@/config/env'

const baseURL = API_BASE_URL.replace(/\/api$/, '')

export const fetchDatabases       = ()       => axios.get(`${baseURL}/databases`).then((r) => r.data)
export const fetchRFilesList      = (params) => api.get('/rFileslist',      { params }).then((r) => r.data)
export const fetchRDocViewHistory = (params) => api.get('/rdocviewhistory', { params }).then((r) => r.data)
export const fetchRLinkSharing    = (params) => api.get('/rlinksharing',    { params }).then((r) => r.data)
export const fetchActivity        = (params) => api.get('/activity',        { params }).then((r) => r.data)

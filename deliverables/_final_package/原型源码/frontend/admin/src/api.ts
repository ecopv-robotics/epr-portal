import axios from 'axios'
const api=axios.create({baseURL:import.meta.env.VITE_API_BASE_URL??'http://localhost:8000/api',timeout:15000})
api.interceptors.request.use(config=>{const token=localStorage.getItem('epr_admin_token');if(token) config.headers.Authorization=`Bearer ${token}`;return config})
api.interceptors.response.use(r=>r,e=>{if(e.response?.status===401){localStorage.clear();window.location.href='/login'}return Promise.reject(e)})
export function fileUrl(value:string){if(/^(https?:|data:|blob:)/i.test(value))return value;return new URL(value,new URL(String(api.defaults.baseURL),window.location.origin).origin).href}
export default api

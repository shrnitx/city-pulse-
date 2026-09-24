import axios from 'axios';
export const api = axios.create({ baseURL: `${process.env.REACT_APP_BACKEND_URL}/api` });
api.interceptors.request.use(config => { const token=localStorage.getItem('citypulse-token'); if(token) config.headers.Authorization=`Bearer ${token}`; return config; });
api.interceptors.response.use(r=>r, err=>{ if(err.response?.status===401 && !err.config.url.includes('/auth/login')) {localStorage.removeItem('citypulse-token'); window.dispatchEvent(new Event('citypulse-expired'));} return Promise.reject(err); });
export const fetcher = path => api.get(path).then(r=>r.data);
export const errorText = error => { const d=error?.response?.data?.detail; return typeof d==='string'?d:Array.isArray(d)?d.map(x=>`${x.loc?.slice(-1)}: ${x.msg}`).join('. '):'Something went wrong. Please try again.'; };
export const relative = date => {if(!date)return '';const m=Math.max(0,Math.floor((Date.now()-new Date(date))/60000));return m<1?'Just now':m<60?`${m}m ago`:m<1440?`${Math.floor(m/60)}h ago`:`${Math.floor(m/1440)}d ago`;};
export const initials = name => (name||'CP').split(' ').slice(0,2).map(s=>s[0]).join('').toUpperCase();
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from './api';
import { mutate } from 'swr';
const AuthContext = createContext();
export function AuthProvider({ children }) {
  const [user,setUser]=useState(null), [society,setSociety]=useState(null), [loading,setLoading]=useState(true);
  const refresh=useCallback(async()=>{if(!localStorage.getItem('citypulse-token')) {setLoading(false);return;}try{const {data}=await api.get('/auth/me');setUser(data.user);setSociety(data.society);}catch{setUser(null);}finally{setLoading(false);}},[]);
  useEffect(()=>{refresh();const expire=()=>{setUser(null);setSociety(null);mutate(()=>true,undefined,{revalidate:false});};window.addEventListener('citypulse-expired',expire);return()=>window.removeEventListener('citypulse-expired',expire);},[refresh]);
  useEffect(()=>{if(!user)return;const timer=setInterval(refresh,15000);return()=>clearInterval(timer);},[user?.id,refresh]);
  const accept=async data=>{await mutate(()=>true,undefined,{revalidate:false});localStorage.setItem('citypulse-token',data.token);setUser(data.user);setSociety(data.society);};
  const logout=async()=>{try{await api.post('/auth/logout');}finally{localStorage.removeItem('citypulse-token');setUser(null);setSociety(null);await mutate(()=>true,undefined,{revalidate:false});}};
  return <AuthContext.Provider value={{user,society,loading,refresh,accept,logout,isAdmin:user?.role==='admin'||user?.role==='initial_admin',isOwner:user?.role==='initial_admin'}}>{children}</AuthContext.Provider>;
}
export const useAuth=()=>useContext(AuthContext);
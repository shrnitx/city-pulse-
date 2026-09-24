import { useEffect,useState } from 'react';
import { ImageOff,Loader2,ZoomIn,Play } from 'lucide-react';
import { api } from '../lib/api';
import { Modal } from './Common';
export const EvidenceImage=({file,onOpen})=>{
 const [url,setUrl]=useState(''),[failed,setFailed]=useState(false);
 useEffect(()=>{let active=true,objectUrl;api.get(`/files/${file.id}`,{responseType:'blob'}).then(({data})=>{objectUrl=URL.createObjectURL(data);if(active)setUrl(objectUrl);}).catch(()=>active&&setFailed(true));return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl);};},[file.id]);
 const video=file.content_type?.startsWith('video');
 return <button data-testid={`evidence-${file.id}`} type="button" title={file.original_filename} className="evidence-thumb" onClick={()=>url&&onOpen({file,url})} disabled={!url}>
 {url?(video?<video src={url} muted preload="metadata"/>:<img src={url} alt={file.original_filename} loading="lazy"/>):<span className="evidence-loading">{failed?<ImageOff size={20}/>:<Loader2 size={20} className="spin"/>}</span>}<span className="evidence-caption">{file.demo?'SAMPLE EVIDENCE':video?'VIDEO EVIDENCE':'RESIDENT EVIDENCE'}</span><span className="evidence-zoom">{video?<Play size={16}/>:<ZoomIn size={16}/>}</span></button>;
};
export const EvidenceGallery=({files,compact=false,caseId})=>{const [selected,setSelected]=useState(null);return <><div className={`evidence-gallery ${compact?'compact':''}`}>{(compact?files.slice(0,3):files).map(f=><EvidenceImage key={f.id} file={f} onOpen={setSelected}/>)}</div><Modal open={!!selected} onClose={()=>setSelected(null)} title={selected?.file.original_filename||'Evidence'} description={selected?.file.demo?'Synthetic demonstration evidence. Not a live incident photograph.':'Evidence submitted by a society resident. Administrator verification is separate.'} id={`evidence-modal-${caseId}`}>{selected&&(selected.file.content_type?.startsWith('video')?<video data-testid="evidence-video-viewer" src={selected.url} controls className="evidence-full"/>:<img data-testid="evidence-image-viewer" className="evidence-full" src={selected.url} alt={selected.file.original_filename}/>)}</Modal></>;};
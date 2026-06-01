<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'

const CC={function:'#00FFD4',async_function:'#00C4A4',class:'#818CF8',method:'#A5B4FC',interface:'#F472B6',type:'#EC4899',namespace:'#FBBF24',enum:'#F59E0B',struct:'#34D399',trait:'#6EE7B7',impl:'#86EFAC',module:'#94A3B8',arrow_function:'#2DD4BF'}
const CL={function:'Fn',async_function:'Async',class:'Class',method:'Method',interface:'Interface',type:'Type',namespace:'NS',enum:'Enum',struct:'Struct',trait:'Trait',impl:'Impl',module:'Module',arrow_function:'Arrow'}
const FI={python:'🐍',js:'📜',jsx:'⚛️',ts:'🔷',tsx:'⚛️',java:'☕',go:'🐹',rust:'🦀',cpp:'⚙️',c:'⚙️',h:'⚙️',html:'🌐',css:'🎨',vue:'💚',ruby:'💎',php:'🐘',markdown:'📝',md:'📝',json:'📋',yaml:'📋',yml:'📋',sh:'⚡',bash:'⚡',txt:'📄'}
const LC=['#00FFD4','#818CF8','#F472B6','#FBBF24','#FB923C','#34D399','#F87171','#60A5FA','#E879F9','#2DD4BF','#A78BFA','#FCD34D']
const fi=(l)=>FI[(l||'').toLowerCase()]||'📄'
const er=(s)=>s.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')

// ── State ───────────────────────────────────────────────────────
const currentView=ref('auth'), activeTab=ref('chat')
const authToken=ref(''), currentUser=ref(null)
const authLoading=ref(false), authError=ref(''), authSuccess=ref(''), authMode=ref('login')
const loginForm=reactive({email:'',password:'',show:false})
const regForm=reactive({username:'',email:'',password:'',confirm:'',show:false})
const forgotForm=reactive({email:'',sent:false,resetToken:''})
const resetForm=reactive({token:'',password:'',confirm:'',show:false})
const repoUrl=ref(''), repoBranch=ref('main'), repoId=ref(''), repoStatus=ref(''), isIndexing=ref(false)
const structureData=ref(null), structureLoading=ref(false)
const selectedChunk=ref(null), selectedFile=ref(null)
const expandedDirs=ref(new Set()), expandedFiles=ref(new Set()), structSearch=ref('')
const graphSubTab=ref('graph'), graphFilter=ref('all')
const canvasRef=ref(null), kgWrapRef=ref(null)
const graphTooltip=ref(null), ttPos=reactive({x:0,y:0})
const graphStats=reactive({nodes:0,edges:0})
let simNodes=[],simEdges=[],animFrame=null,gt={x:0,y:0,s:1}
let isPan=false,panStart={x:0,y:0},dragNode=null,hovNode=null,resizeObs=null
const visualSubTab=ref('treemap'), hovTmFile=ref(null)
const callCanvasRef=ref(null), callWrapRef=ref(null)
const callTooltip=ref(null), ctPos=reactive({x:0,y:0})
let callNodes=[],callEdges=[],callFrame=null,cgt={x:0,y:0,s:1}
let cisPan=false,cpan={x:0,y:0},cdrag=null,chov=null,callResObs=null
const previewFile=ref(null), previewSearch=ref('')
const chatMessages=ref([]), chatInput=ref(''), isAnswering=ref(false), chatEndRef=ref(null)
const msgSources=ref({})
let twQ='',twRaf=null,twMsg=null

// ─── Upload state ────────────────────────────────────────────────
const uploadedFiles=ref([])   // {id,name,ext,icon,size,loading,error,contentType,text,base64,mediaType,charCount,pageCount,truncated}
const isDragOver=ref(false)
const fileInputRef=ref(null)

// ── Computed ────────────────────────────────────────────────────
const pwdStr=computed(()=>{const p=regForm.password;if(!p)return 0;return[p.length>=8,p.length>=12,/[A-Z]/.test(p),/[0-9]/.test(p),/[^A-Za-z0-9]/.test(p)].filter(Boolean).length})
const pwdLbl=computed(()=>['','很弱','弱','中等','强','很强'][pwdStr.value]||'')
const pwdClr=computed(()=>['','#f87171','#fb923c','#facc15','#4ade80','#00FFD4'][pwdStr.value])

const flatTree=computed(()=>{
  if(!structureData.value?.files)return[]
  const q=structSearch.value.toLowerCase()
  const files=q?structureData.value.files.filter(f=>f.path.toLowerCase().includes(q)||f.chunks.some(c=>c.name.toLowerCase().includes(q))):structureData.value.files
  const roots=[]
  for(const file of files){
    const parts=file.path.split('/');let cur=roots;let pf=''
    for(let i=0;i<parts.length-1;i++){
      pf=pf?`${pf}/${parts[i]}`:parts[i]
      let nd=cur.find(n=>n.type==='dir'&&n.path===pf)
      if(!nd){nd={type:'dir',name:parts[i],path:pf,children:[]};cur.push(nd)}
      cur=nd.children
    }
    cur.push({type:'file',name:parts[parts.length-1],path:file.path,language:file.language,chunks:file.chunks})
  }
  const flat=[]
  const walk=(nodes,depth)=>{
    const s=[...nodes].sort((a,b)=>a.type===b.type?a.name.localeCompare(b.name):a.type==='dir'?-1:1)
    for(const n of s){
      flat.push({...n,depth})
      if(n.type==='dir'&&expandedDirs.value.has(n.path))walk(n.children,depth+1)
      if(n.type==='file'&&expandedFiles.value.has(n.path)){
        const cq=q?n.chunks.filter(c=>c.name.toLowerCase().includes(q)):n.chunks
        cq.forEach(c=>flat.push({type:'chunk',depth:depth+1,chunk:c,filePath:n.path}))
      }
    }
  }
  walk(roots,0);return flat
})

const previewLines=computed(()=>{
  if(!previewFile.value||!structureData.value)return[]
  const file=structureData.value.files.find(f=>f.path===previewFile.value)
  if(!file)return[]
  const content=file.chunks.map(c=>c.content||c.content_preview||'').join('\n')
  const q=previewSearch.value.toLowerCase()
  return content.split('\n').map((text,i)=>({num:i+1,text,hl:q&&text.toLowerCase().includes(q)}))
})

const treemapData=computed(()=>{
  const files=structureData.value?.files;if(!files?.length)return[]
  const nodes=files.map((f,i)=>({id:f.path,name:f.path.split('/').pop(),path:f.path,lang:f.language,chunks:f.chunks.length,value:Math.max(1,f.chunks.length),color:LC[i%LC.length]}))
  nodes.sort((a,b)=>b.value-a.value)
  const total=nodes.reduce((s,n)=>s+n.value,0)
  return sliceDice(nodes,0,0,780,450,total,true)
})

const metricsData=computed(()=>{
  const files=structureData.value?.files;if(!files?.length)return null
  const langs={},types={},async_={total:0,async:0};let totalLines=0
  for(const f of files){
    langs[f.language||'other']=(langs[f.language||'other']||0)+1
    for(const c of f.chunks){
      types[c.chunk_type]=(types[c.chunk_type]||0)+1
      if(['function','method','arrow_function'].includes(c.chunk_type)){async_.total++;if(c.is_async)async_.async++}
      totalLines+=Math.max(0,(c.end_line||0)-(c.start_line||0))
    }
  }
  const langE=Object.entries(langs).sort((a,b)=>b[1]-a[1]).slice(0,8)
  const langT=langE.reduce((s,[,v])=>s+v,0)
  const cx=95,cy=95,r=72,ir=44;let ang=-Math.PI/2
  const donut=langE.map(([lang,cnt],i)=>{
    const da=(cnt/langT)*2*Math.PI,ea=ang+da,lg=da>Math.PI?1:0
    const d=`M${cx+r*Math.cos(ang)},${cy+r*Math.sin(ang)} A${r},${r},0,${lg},1,${cx+r*Math.cos(ea)},${cy+r*Math.sin(ea)} L${cx+ir*Math.cos(ea)},${cy+ir*Math.sin(ea)} A${ir},${ir},0,${lg},0,${cx+ir*Math.cos(ang)},${cy+ir*Math.sin(ang)}Z`
    const mid=ang+da/2;ang=ea
    return{lang,cnt,d,color:LC[i%LC.length],mid}
  })
  const typeE=Object.entries(types).sort((a,b)=>b[1]-a[1]).slice(0,8)
  const maxT=typeE[0]?.[1]||1
  const topFiles=[...files].sort((a,b)=>b.chunks.length-a.chunks.length).slice(0,10)
  const maxC=topFiles[0]?.chunks.length||1
  return{langs,langE,donut,langT,types,typeE,maxT,topFiles,maxC,async_,totalLines,
    totalFiles:files.length,totalChunks:files.reduce((s,f)=>s+f.chunks.length,0)}
})

// ── API ─────────────────────────────────────────────────────────
const api=async(path,opts={})=>{
  const h={'Content-Type':'application/json',...(opts.headers||{})}
  if(authToken.value)h['Authorization']=`Bearer ${authToken.value}`
  const res=await fetch(`/api${path}`,{...opts,headers:h})
  const txt=await res.text();const d=txt?JSON.parse(txt):{}
  if(!res.ok)throw new Error(Array.isArray(d.detail)?d.detail.map(e=>e.msg||JSON.stringify(e)).join('\n'):d.detail||`Error ${res.status}`)
  return d
}

// ── Auth ────────────────────────────────────────────────────────
const switchAuth=(m)=>{authMode.value=m;authError.value='';authSuccess.value=''}
const handleLogin=async()=>{
  authError.value='';if(!loginForm.email||!loginForm.password){authError.value='请填写邮箱和密码';return}
  authLoading.value=true
  try{const d=await api('/auth/login',{method:'POST',body:JSON.stringify({email:loginForm.email,password:loginForm.password})});authToken.value=d.access_token;currentUser.value=d.user;localStorage.setItem('auth_token',d.access_token);localStorage.setItem('auth_user',JSON.stringify(d.user));currentView.value='main'}
  catch(e){authError.value=e.message}finally{authLoading.value=false}
}
const handleRegister=async()=>{
  authError.value='';if(!regForm.username||!regForm.email||!regForm.password){authError.value='请填写所有字段';return}
  if(regForm.password!==regForm.confirm){authError.value='两次密码不一致';return}
  authLoading.value=true
  try{await api('/auth/register',{method:'POST',body:JSON.stringify({username:regForm.username,email:regForm.email,password:regForm.password})});authSuccess.value='注册成功，请登录';loginForm.email=regForm.email;authMode.value='login'}
  catch(e){authError.value=e.message}finally{authLoading.value=false}
}
const handleForgot=async()=>{
  authError.value='';if(!forgotForm.email){authError.value='请输入邮箱';return};authLoading.value=true
  try{const d=await api('/auth/forgot-password',{method:'POST',body:JSON.stringify({email:forgotForm.email})});forgotForm.sent=true;if(d.reset_token){forgotForm.resetToken=d.reset_token;resetForm.token=d.reset_token}}
  catch(e){authError.value=e.message}finally{authLoading.value=false}
}
const handleReset=async()=>{
  authError.value='';if(!resetForm.token||!resetForm.password){authError.value='请填写令牌和新密码';return}
  if(resetForm.password!==resetForm.confirm){authError.value='密码不一致';return};authLoading.value=true
  try{await api('/auth/reset-password',{method:'POST',body:JSON.stringify({reset_token:resetForm.token,new_password:resetForm.password})});authSuccess.value='密码已重置，请登录';authMode.value='login'}
  catch(e){authError.value=e.message}finally{authLoading.value=false}
}
const handleLogout=()=>{authToken.value='';currentUser.value=null;localStorage.removeItem('auth_token');localStorage.removeItem('auth_user');currentView.value='auth';clearAll()}

// ── Repo ────────────────────────────────────────────────────────
const clearAll=()=>{
  chatMessages.value=[];msgSources.value={};structureData.value=null;selectedChunk.value=null
  selectedFile.value=null;previewFile.value=null;expandedDirs.value=new Set();expandedFiles.value=new Set()
  simNodes=[];simEdges=[];callNodes=[];callEdges=[]
  if(animFrame){cancelAnimationFrame(animFrame);animFrame=null}
  if(callFrame){cancelAnimationFrame(callFrame);callFrame=null}
  graphTooltip.value=null;callTooltip.value=null;graphStats.nodes=0;graphStats.edges=0
}
const handleIndexRepo=async()=>{
  if(!repoUrl.value.trim()||isIndexing.value)return
  isIndexing.value=true;repoStatus.value='⏳ 构建索引中…';clearAll()
  try{
    const p=repoUrl.value.startsWith('http')?{github_url:repoUrl.value.trim(),branch:repoBranch.value||'main'}:{local_path:repoUrl.value.trim(),branch:repoBranch.value||'main'}
    const d=await api('/repos/index',{method:'POST',body:JSON.stringify(p)})
    repoId.value=d.repo_id;repoStatus.value=`✅ 索引完成：${d.chunks} 片段`
    if(['structure','preview'].includes(activeTab.value))loadStructure()
    if(activeTab.value==='graph'){await nextTick();buildKGraph()}
    if(activeTab.value==='visual'){await nextTick();if(visualSubTab.value==='callgraph')buildCallGraph();if(visualSubTab.value==='treemap'&&structureData.value===null)loadStructure()}
  }catch(e){repoStatus.value=`❌ ${e.message}`}finally{isIndexing.value=false}
}

// ── Structure ───────────────────────────────────────────────────
const loadStructure=async()=>{
  if(!repoId.value)return;structureLoading.value=true
  try{structureData.value=await api(`/repos/${repoId.value}/structure`);if(structureData.value?.files?.length){const f=structureData.value.files[0];previewFile.value=f.path;expandedFiles.value=new Set([...expandedFiles.value,f.path])}}
  catch(e){repoStatus.value=`❌ 结构加载失败: ${e.message}`}finally{structureLoading.value=false}
}
const toggleDir=(p)=>{const s=new Set(expandedDirs.value);s.has(p)?s.delete(p):s.add(p);expandedDirs.value=s}
const toggleFile=(p)=>{const s=new Set(expandedFiles.value);s.has(p)?s.delete(p):s.add(p);expandedFiles.value=s;selectedChunk.value=null}
const selectChunk=(chunk,fp)=>{selectedChunk.value=chunk;selectedFile.value=fp}

const computeComplexity=(chunk)=>{
  if(!chunk)return 0
  const lines=(chunk.end_line||0)-(chunk.start_line||0)||1
  const params=chunk.params?chunk.params.split(',').filter(p=>p.trim()).length:0
  return Math.min(100,Math.round(lines*0.7+params*6))
}
const findCalls=(chunk)=>{
  if(!chunk?.content||!structureData.value)return[]
  return structureData.value.files.flatMap(f=>f.chunks.map(c=>({...c,fp:f.path}))).filter(c=>c!==chunk&&c.name&&new RegExp(`\\b${er(c.name)}\\s*[\\(\\[]`).test(chunk.content)).slice(0,6)
}
const findCalledBy=(chunk)=>{
  if(!chunk?.name||!structureData.value)return[]
  const re=new RegExp(`\\b${er(chunk.name)}\\s*[\\(\\[]`)
  return structureData.value.files.flatMap(f=>f.chunks.map(c=>({...c,fp:f.path}))).filter(c=>c!==chunk&&c.content&&re.test(c.content)).slice(0,6)
}
const explainChunk=(chunk)=>{
  if(!chunk||!repoId.value)return
  const code=(chunk.content||chunk.content_preview||'').slice(0,600)
  chatInput.value=`请详细解释以下代码片段的功能和实现思路：\n\`\`\`\n${code}\n\`\`\``
  activeTab.value='chat';nextTick(()=>sendMessage())
}

// ── Knowledge Graph ─────────────────────────────────────────────
const buildKGraph=()=>{
  const cv=canvasRef.value;if(!cv)return
  const W=cv.width||800,H=cv.height||500
  simNodes=[];simEdges=[]
  const files=(structureData.value?.files||[]).slice(0,22)
  files.forEach((file,fi)=>{
    const fid=`f${fi}`,a=(fi/Math.max(files.length,1))*2*Math.PI
    simNodes.push({id:fid,label:file.path.split('/').pop(),full:file.path,type:'file',extra:{lang:file.language,chunks:file.chunks.length},x:W/2+Math.cos(a)*175,y:H/2+Math.sin(a)*135,vx:0,vy:0,r:11})
    const maxC=graphFilter.value==='all'?6:10
    file.chunks.filter(c=>graphFilter.value==='all'||c.chunk_type===graphFilter.value).slice(0,maxC).forEach((chunk,ci)=>{
      const cid=`c${fi}_${ci}`,pa=simNodes[simNodes.length-1]
      simNodes.push({id:cid,label:chunk.name||chunk.chunk_type,full:`${file.path} · ${chunk.name}`,type:chunk.chunk_type,extra:{params:chunk.params,ret:chunk.return_type,lines:`${chunk.start_line}-${chunk.end_line}`,async:chunk.is_async,file:file.path,chunk},x:pa.x+(Math.random()-.5)*80,y:pa.y+(Math.random()-.5)*80,vx:0,vy:0,r:7})
      simEdges.push({s:fid,t:cid})
    })
  })
  graphStats.nodes=simNodes.length;graphStats.edges=simEdges.length
  if(animFrame)cancelAnimationFrame(animFrame)
  let tk=0
  const loop=()=>{tk++;runForces(cv.width,cv.height);drawKG(cv);if(tk<500&&canvasRef.value)animFrame=requestAnimationFrame(loop)}
  animFrame=requestAnimationFrame(loop)
}
const runForces=(W,H)=>{
  for(let i=0;i<simNodes.length;i++)for(let j=i+1;j<simNodes.length;j++){const dx=simNodes[j].x-simNodes[i].x,dy=simNodes[j].y-simNodes[i].y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(88*88)/(d*d)*.065;simNodes[i].vx-=dx*f/d;simNodes[i].vy-=dy*f/d;simNodes[j].vx+=dx*f/d;simNodes[j].vy+=dy*f/d}
  for(const e of simEdges){const s=simNodes.find(n=>n.id===e.s),t=simNodes.find(n=>n.id===e.t);if(!s||!t)continue;const dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-68)*.022*.065;s.vx+=dx*f;s.vy+=dy*f;t.vx-=dx*f;t.vy-=dy*f}
  for(const n of simNodes){if(n.fixed){n.vx=0;n.vy=0;continue}n.vx+=(W/2-n.x)*.003;n.vy+=(H/2-n.y)*.003;n.vx*=.87;n.vy*=.87;n.x+=n.vx;n.y+=n.vy;n.x=Math.max(n.r+3,Math.min(W-n.r-3,n.x));n.y=Math.max(n.r+3,Math.min(H-n.r-3,n.y))}
}
const drawKG=(cv)=>{
  const ctx=cv.getContext('2d');ctx.clearRect(0,0,cv.width,cv.height)
  ctx.save();ctx.translate(gt.x,gt.y);ctx.scale(gt.s,gt.s)
  for(const e of simEdges){const s=simNodes.find(n=>n.id===e.s),t=simNodes.find(n=>n.id===e.t);if(!s||!t)continue;const ih=hovNode&&(hovNode.id===e.s||hovNode.id===e.t);ctx.beginPath();ctx.moveTo(s.x,s.y);ctx.lineTo(t.x,t.y);ctx.strokeStyle=ih?'rgba(0,255,212,.5)':'rgba(129,140,248,.2)';ctx.lineWidth=ih?1.5:1;ctx.stroke()}
  for(const n of simNodes){const col=n.type==='file'?'#818CF8':(CC[n.type]||'#94A3B8'),ih=n===hovNode,r=ih?n.r*1.35:n.r;ctx.beginPath();ctx.arc(n.x,n.y,r,0,Math.PI*2);ctx.fillStyle=col+(ih?'44':'1A');ctx.fill();if(ih){ctx.shadowColor=col;ctx.shadowBlur=18}ctx.strokeStyle=col;ctx.lineWidth=n.type==='file'?(ih?2.5:2):(ih?2:1.5);ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle=ih?'#F0F8FF':'#B0CCE8';ctx.font=`${n.type==='file'?(ih?10:9.5):(ih?9:8.5)}px "Fira Code",monospace`;ctx.textAlign='center';const lb=n.label.length>15?n.label.slice(0,14)+'…':n.label;ctx.fillText(lb,n.x,n.y+r+13)}
  ctx.restore()
}
const gsp=(e)=>{const r=canvasRef.value.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
const fna=(sx,sy)=>simNodes.find(n=>{const s={x:n.x*gt.s+gt.x,y:n.y*gt.s+gt.y};const dx=sx-s.x,dy=sy-s.y;return Math.sqrt(dx*dx+dy*dy)<n.r*gt.s+6})
const onKgDown=(e)=>{const p=gsp(e),n=fna(p.x,p.y);if(n){dragNode=n;n.fixed=true}else{isPan=true;panStart={x:p.x-gt.x,y:p.y-gt.y}}}
const onKgMove=(e)=>{
  const p=gsp(e)
  if(dragNode){const g={x:(p.x-gt.x)/gt.s,y:(p.y-gt.y)/gt.s};dragNode.x=g.x;dragNode.y=g.y;if(canvasRef.value)drawKG(canvasRef.value);return}
  if(isPan){gt.x=p.x-panStart.x;gt.y=p.y-panStart.y;if(canvasRef.value)drawKG(canvasRef.value);return}
  const prev=hovNode;hovNode=fna(p.x,p.y)||null
  if(hovNode!==prev){
    graphTooltip.value=hovNode?{name:hovNode.label,full:hovNode.full,type:CL[hovNode.type]||hovNode.type,...hovNode.extra}:null
    if(hovNode){const s={x:hovNode.x*gt.s+gt.x,y:hovNode.y*gt.s+gt.y};ttPos.x=s.x+14;ttPos.y=s.y-10}
    if(canvasRef.value){canvasRef.value.style.cursor=hovNode?'pointer':'grab';drawKG(canvasRef.value)}
  }
}
const onKgUp=()=>{if(dragNode){dragNode.fixed=false;dragNode=null};isPan=false}
const onKgLeave=()=>{isPan=false;dragNode=null;hovNode=null;graphTooltip.value=null}
const onKgWheel=(e)=>{e.preventDefault();const p=gsp(e),d=e.deltaY>0?.87:1.15,ns=Math.max(.18,Math.min(4.5,gt.s*d));gt.x=p.x-(p.x-gt.x)*(ns/gt.s);gt.y=p.y-(p.y-gt.y)*(ns/gt.s);gt.s=ns;if(canvasRef.value)drawKG(canvasRef.value)}
const resetGraph=()=>{gt={x:0,y:0,s:1};if(canvasRef.value)drawKG(canvasRef.value)}
const zoomGraph=(d)=>{const cv=canvasRef.value;if(!cv)return;const cx=cv.width/2,cy=cv.height/2,ns=Math.max(.18,Math.min(4.5,gt.s*d));gt.x=cx-(cx-gt.x)*(ns/gt.s);gt.y=cy-(cy-gt.y)*(ns/gt.s);gt.s=ns;drawKG(cv)}
const clickKgNode=(e)=>{const p=gsp(e),n=fna(p.x,p.y);if(!n)return;if(n.extra?.chunk&&n.extra?.file){selectedChunk.value=n.extra.chunk;selectedFile.value=n.extra.file;expandedFiles.value=new Set([...expandedFiles.value,n.extra.file]);activeTab.value='structure'}}

// ── Treemap ─────────────────────────────────────────────────────
const sliceDice=(nodes,x,y,W,H,total,horiz)=>{
  if(!nodes.length)return[]
  if(nodes.length===1)return[{...nodes[0],x,y,w:Math.max(2,W),h:Math.max(2,H)}]
  let acc=0,split=0
  for(let i=0;i<nodes.length;i++){acc+=nodes[i].value;if(acc>=total/2){split=i+1;break}}
  split=Math.max(1,Math.min(split,nodes.length-1))
  const L=nodes.slice(0,split),R=nodes.slice(split)
  const lt=L.reduce((s,n)=>s+n.value,0),rt=R.reduce((s,n)=>s+n.value,0)
  const ratio=lt/total
  if(horiz){const lW=W*ratio;return[...sliceDice(L,x,y,lW,H,lt,!horiz),...sliceDice(R,x+lW,y,W-lW,H,rt,!horiz)]}
  const tH=H*ratio;return[...sliceDice(L,x,y,W,tH,lt,!horiz),...sliceDice(R,x,y+tH,W,H-tH,rt,!horiz)]
}

// ── Call Graph ───────────────────────────────────────────────────
const buildCallGraph=()=>{
  const cv=callCanvasRef.value;if(!cv||!structureData.value)return
  const W=cv.width||800,H=cv.height||500
  const fnChunks=structureData.value.files.flatMap(f=>f.chunks.filter(c=>['function','async_function','method','arrow_function'].includes(c.chunk_type)&&c.name).map(c=>({...c,fp:f.path}))).slice(0,50)
  callNodes=fnChunks.map((c,i)=>({id:c.name,label:c.name,type:c.chunk_type,file:c.fp,extra:{params:c.params,ret:c.return_type,lines:`${c.start_line}-${c.end_line}`,async:c.is_async,chunk:c},x:W/2+Math.cos(i/fnChunks.length*2*Math.PI)*190,y:H/2+Math.sin(i/fnChunks.length*2*Math.PI)*145,vx:0,vy:0,r:8}))
  callEdges=[]
  for(const src of fnChunks){if(!src.content)continue;for(const tgt of fnChunks){if(src===tgt||!tgt.name)continue;if(new RegExp(`\\b${er(tgt.name)}\\s*[\\(\\[]`).test(src.content))callEdges.push({s:src.name,t:tgt.name})}}
  if(callFrame)cancelAnimationFrame(callFrame)
  let tk=0
  const loop=()=>{tk++;runCForces(cv.width,cv.height);drawCG(cv);if(tk<500&&callCanvasRef.value)callFrame=requestAnimationFrame(loop)}
  callFrame=requestAnimationFrame(loop)
}
const runCForces=(W,H)=>{
  for(let i=0;i<callNodes.length;i++)for(let j=i+1;j<callNodes.length;j++){const dx=callNodes[j].x-callNodes[i].x,dy=callNodes[j].y-callNodes[i].y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(80*80)/(d*d)*.07;callNodes[i].vx-=dx*f/d;callNodes[i].vy-=dy*f/d;callNodes[j].vx+=dx*f/d;callNodes[j].vy+=dy*f/d}
  for(const e of callEdges){const s=callNodes.find(n=>n.id===e.s),t=callNodes.find(n=>n.id===e.t);if(!s||!t)continue;const dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)||1,f=(d-65)*.02*.07;s.vx+=dx*f;s.vy+=dy*f;t.vx-=dx*f;t.vy-=dy*f}
  for(const n of callNodes){if(n.fixed){n.vx=0;n.vy=0;continue}n.vx+=(W/2-n.x)*.003;n.vy+=(H/2-n.y)*.003;n.vx*=.87;n.vy*=.87;n.x+=n.vx;n.y+=n.vy;n.x=Math.max(n.r+3,Math.min(W-n.r-3,n.x));n.y=Math.max(n.r+3,Math.min(H-n.r-3,n.y))}
}
const drawCG=(cv)=>{
  const ctx=cv.getContext('2d');ctx.clearRect(0,0,cv.width,cv.height)
  ctx.save();ctx.translate(cgt.x,cgt.y);ctx.scale(cgt.s,cgt.s)
  for(const e of callEdges){
    const s=callNodes.find(n=>n.id===e.s),t=callNodes.find(n=>n.id===e.t);if(!s||!t)continue
    const ih=chov&&(chov.id===e.s||chov.id===e.t)
    const dx=t.x-s.x,dy=t.y-s.y,d=Math.sqrt(dx*dx+dy*dy)||1,ux=dx/d,uy=dy/d
    const sx2=s.x+ux*s.r,sy2=s.y+uy*s.r,tx2=t.x-ux*(t.r+7),ty2=t.y-uy*(t.r+7)
    ctx.beginPath();ctx.moveTo(sx2,sy2);ctx.lineTo(tx2,ty2)
    ctx.strokeStyle=ih?'rgba(0,255,212,.6)':'rgba(244,114,182,.25)';ctx.lineWidth=ih?1.8:1;ctx.stroke()
    const ang=Math.atan2(ty2-sy2,tx2-sx2),as=7
    ctx.beginPath();ctx.moveTo(tx2,ty2);ctx.lineTo(tx2-as*Math.cos(ang-.45),ty2-as*Math.sin(ang-.45));ctx.lineTo(tx2-as*Math.cos(ang+.45),ty2-as*Math.sin(ang+.45));ctx.closePath()
    ctx.fillStyle=ih?'rgba(0,255,212,.6)':'rgba(244,114,182,.25)';ctx.fill()
  }
  for(const n of callNodes){const col=CC[n.type]||'#94A3B8',ih=n===chov,r=ih?n.r*1.35:n.r;ctx.beginPath();ctx.arc(n.x,n.y,r,0,Math.PI*2);ctx.fillStyle=col+(ih?'44':'1A');ctx.fill();if(ih){ctx.shadowColor=col;ctx.shadowBlur=16}ctx.strokeStyle=col;ctx.lineWidth=ih?2:1.5;ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle=ih?'#F0F8FF':'#B0CCE8';ctx.font=`${ih?9.5:8.5}px "Fira Code",monospace`;ctx.textAlign='center';const lb=n.label.length>14?n.label.slice(0,13)+'…':n.label;ctx.fillText(lb,n.x,n.y+r+13)}
  ctx.restore()
}
const cgsp=(e)=>{const r=callCanvasRef.value.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top}}
const cfna=(sx,sy)=>callNodes.find(n=>{const s={x:n.x*cgt.s+cgt.x,y:n.y*cgt.s+cgt.y};const dx=sx-s.x,dy=sy-s.y;return Math.sqrt(dx*dx+dy*dy)<n.r*cgt.s+6})
const onCgDown=(e)=>{const p=cgsp(e),n=cfna(p.x,p.y);if(n){cdrag=n;n.fixed=true}else{cisPan=true;cpan={x:p.x-cgt.x,y:p.y-cgt.y}}}
const onCgMove=(e)=>{
  const p=cgsp(e)
  if(cdrag){const g={x:(p.x-cgt.x)/cgt.s,y:(p.y-cgt.y)/cgt.s};cdrag.x=g.x;cdrag.y=g.y;if(callCanvasRef.value)drawCG(callCanvasRef.value);return}
  if(cisPan){cgt.x=p.x-cpan.x;cgt.y=p.y-cpan.y;if(callCanvasRef.value)drawCG(callCanvasRef.value);return}
  const prev=chov;chov=cfna(p.x,p.y)||null
  if(chov!==prev){callTooltip.value=chov?{name:chov.label,file:chov.file,type:CL[chov.type]||chov.type,...chov.extra}:null;if(chov){const s={x:chov.x*cgt.s+cgt.x,y:chov.y*cgt.s+cgt.y};ctPos.x=s.x+14;ctPos.y=s.y-10}if(callCanvasRef.value){callCanvasRef.value.style.cursor=chov?'pointer':'grab';drawCG(callCanvasRef.value)}}
}
const onCgUp=()=>{if(cdrag){cdrag.fixed=false;cdrag=null};cisPan=false}
const onCgLeave=()=>{cisPan=false;cdrag=null;chov=null;callTooltip.value=null}
const onCgWheel=(e)=>{e.preventDefault();const p=cgsp(e),d=e.deltaY>0?.87:1.15,ns=Math.max(.18,Math.min(4.5,cgt.s*d));cgt.x=p.x-(p.x-cgt.x)*(ns/cgt.s);cgt.y=p.y-(p.y-cgt.y)*(ns/cgt.s);cgt.s=ns;if(callCanvasRef.value)drawCG(callCanvasRef.value)}
const resetCG=()=>{cgt={x:0,y:0,s:1};if(callCanvasRef.value)drawCG(callCanvasRef.value)}
const clickCgNode=(e)=>{const p=cgsp(e),n=cfna(p.x,p.y);if(!n?.extra?.chunk)return;selectedChunk.value=n.extra.chunk;selectedFile.value=n.file;expandedFiles.value=new Set([...expandedFiles.value,n.file]);activeTab.value='structure'}

// ── Markdown / LaTeX ────────────────────────────────────────────
const renderMD=(text)=>{
  if(!text)return''
  const blks=[];let h=text
  h=h.replace(/```(\w*)\n?([\s\S]*?)```/g,(_,lang,code)=>{const safe=code.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');const i=blks.length;blks.push(`<div class="mdc"><span class="mdc-lang">${lang||'code'}</span><pre><code>${safe}</code></pre></div>`);return`\x01${i}\x01`})
  h=h.replace(/\$\$([\s\S]+?)\$\$/g,(_,m)=>{try{return`<div class="mmath">${window.katex?.renderToString(m,{displayMode:true,throwOnError:false})||`<code>$$${m}$$</code>`}</div>`}catch{return`<code class="mmf">$$${m.trim()}$$</code>`}})
  h=h.replace(/(?<!\$)\$([^$\n]{1,80}?)\$(?!\$)/g,(_,m)=>{try{return window.katex?.renderToString(m,{displayMode:false,throwOnError:false})||`<code>$${m}$</code>`}catch{return`<code class="mmf">$${m}$</code>`}})
  h=h.replace(/`([^`]+)`/g,'<code class="mic">$1</code>')
  h=h.replace(/\*\*\*([^*]+)\*\*\*/g,'<strong><em>$1</em></strong>').replace(/\*\*([^*\n]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*\n]+)\*/g,'<em>$1</em>')
  h=h.replace(/^#### (.+)$/gm,'<h4 class="mh">$1</h4>').replace(/^### (.+)$/gm,'<h3 class="mh">$1</h3>').replace(/^## (.+)$/gm,'<h2 class="mh">$1</h2>').replace(/^# (.+)$/gm,'<h1 class="mh">$1</h1>')
  h=h.replace(/^---+$/gm,'<hr class="mhr"/>').replace(/^> (.+)$/gm,'<blockquote class="mbq">$1</blockquote>')
  h=h.replace(/^[ \t]*[-*] (.+)$/gm,'<li>$1</li>').replace(/^[ \t]*\d+\. (.+)$/gm,'<li class="ol">$1</li>')
  h=h.replace(/(<li class="ol">[\s\S]+?<\/li>)(\n(?!<li)|$)/g,'<ol>$1</ol>').replace(/(<li>[\s\S]+?<\/li>)(\n(?!<li)|$)/g,'<ul>$1</ul>')
  h=h.replace(/\[(\d+)\]/g,'<sup class="mcite" data-n="$1">[$1]</sup>')
  const bTags=['<h1','<h2','<h3','<h4','<ul','<ol','<pre','<div','<blockquote','<hr']
  h=h.split('\n\n').map(p=>{const t=p.trim();if(!t)return'';if(bTags.some(b=>t.startsWith(b)))return t;return`<p class="mp">${t.replace(/\n/g,'<br/>')}</p>`}).join('\n')
  h=h.replace(/\x01(\d+)\x01/g,(_,i)=>blks[+i])
  return h
}

// ── File Upload ──────────────────────────────────────────────────
const UPL_ICONS={pdf:'📄',docx:'📝',doc:'📝',md:'📋',markdown:'📋',txt:'📃',rst:'📃',csv:'📊',png:'🖼',jpg:'🖼',jpeg:'🖼',gif:'🎞',webp:'🖼',bmp:'🖼',tiff:'🖼'}
const getUplIcon=(name)=>UPL_ICONS[name.split('.').pop().toLowerCase()]||'📎'
const fmtSize=(b)=>b<1024?`${b}B`:b<1048576?`${(b/1024).toFixed(1)}KB`:`${(b/1048576).toFixed(1)}MB`

const doUpload=async(file)=>{
  const entry={id:Date.now()+Math.random(),name:file.name,ext:file.name.split('.').pop().toLowerCase(),
    icon:getUplIcon(file.name),size:file.size,loading:true,error:null,
    contentType:null,text:null,base64:null,mediaType:null,charCount:0,pageCount:0,truncated:false}
  uploadedFiles.value=[...uploadedFiles.value,entry]
  try{
    const fd=new FormData();fd.append('file',file)
    const res=await fetch('/api/upload',{method:'POST',headers:authToken.value?{Authorization:`Bearer ${authToken.value}`}:{},body:fd})
    const d=await res.json()
    if(!res.ok)throw new Error(d.detail||'上传失败')
    Object.assign(entry,{loading:false,contentType:d.content_type,text:d.text,
      base64:d.image_base64,mediaType:d.image_media_type,
      charCount:d.char_count,pageCount:d.page_count,truncated:d.truncated})
  }catch(e){entry.error=e.message;entry.loading=false}
  uploadedFiles.value=[...uploadedFiles.value]   // trigger reactivity
}

const handleFiles=(files)=>{[...files].forEach(f=>doUpload(f))}

const onFileInput=(e)=>{if(e.target.files?.length)handleFiles(e.target.files);e.target.value=''}

const onDrop=(e)=>{e.preventDefault();isDragOver.value=false;const f=e.dataTransfer?.files;if(f?.length)handleFiles(f)}

const removeUplFile=(id)=>{uploadedFiles.value=uploadedFiles.value.filter(f=>f.id!==id)}

// ── Chat ────────────────────────────────────────────────────────
const drainTW=()=>{
  if(!twMsg||!twQ.length){twRaf=null;return}
  const batch=Math.min(7,twQ.length);twMsg.raw=(twMsg.raw||'')+twQ.slice(0,batch);twMsg.html=renderMD(twMsg.raw);twQ=twQ.slice(batch)
  nextTick(scrollChat);twRaf=requestAnimationFrame(drainTW)
}
const queueTW=(msg,txt)=>{twMsg=msg;twQ+=txt;if(!twRaf)twRaf=requestAnimationFrame(drainTW)}
const scrollChat=()=>chatEndRef.value?.scrollIntoView({behavior:'smooth'})
const handleKey=(e)=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}}
const quickAsk=(q)=>{chatInput.value=q;sendMessage()}

// ── Source extraction: supports multiple RAG output formats ──────
const extractSources=(text)=>{
  const res={}

  // Strategy 1: dedicated source block (most reliable)
  // Matches "来源:\n[1] path/to/file (行 X-Y)" style blocks
  const blockM=text.match(/(?:来源|Sources?|参考(?:文献|资料)?|References?)[：:\s]*\n((?:\[?\d+\]?[^\n]+\n?)+)/i)
  if(blockM){
    const re=/\[?(\d+)\]?\s+([^\n(（]+?)(?:\s*[\(（][^)\）]*?(\d+)\s*[-–~]\s*(\d+)[^)\）]*?[\)）])?$/gm
    let m
    while((m=re.exec(blockM[1]))!==null){
      const n=+m[1],path=m[2].trim().replace(/[，,;：:.。]\s*$|["""]/g,'')
      if(!res[n]&&path.length>1)res[n]={n,path,sl:m[3]?+m[3]:0,el:m[4]?+m[4]:0}
    }
  }

  // Strategy 2: inline [N] citations with file-like paths
  const inlineRe=/\[(\d+)\]\s+([^\s\[\n](?:[^\n\[\]]{1,78}?))(?:\s*[\(（][^\)）]*?(\d+)\s*[-–~]\s*(\d+)[^\)）]*?[\)）]|\s*[：:](\d+)[-–](\d+))?(?=\s|[，,。\n]|$)/gm
  let m
  while((m=inlineRe.exec(text))!==null){
    const n=+m[1];if(res[n])continue
    const raw=m[2].trim().replace(/[，,;：:.。]\s*$|["""]/g,'')
    // Accept only if it looks like a file path (contains / or .)
    if(!raw||raw.length<2||(!/[\/\.]/.test(raw)&&!raw.match(/\w+\.\w+/)))continue
    const sl=m[3]?+m[3]:m[5]?+m[5]:0,el=m[4]?+m[4]:m[6]?+m[6]:0
    res[n]={n,path:raw,sl,el}
  }

  return Object.values(res).sort((a,b)=>a.n-b.n)
}

// ── Jump to source: async, reactive Set updates, multi-strategy match ──
const jumpToSource=async(src)=>{
  if(!src?.path)return

  // Ensure structure is loaded
  if(!structureData.value){
    await loadStructure()
    if(!structureData.value)return
  }

  const files=structureData.value.files
  if(!files?.length)return

  // Multi-strategy file matching
  let file=null
  // 1. Exact path match
  file=files.find(f=>f.path===src.path)
  // 2. Filename match
  if(!file){const fn=src.path.split('/').pop();file=files.find(f=>f.path.split('/').pop()===fn)}
  // 3. Suffix / partial match
  if(!file)file=files.find(f=>f.path.endsWith('/'+src.path)||src.path.endsWith('/'+f.path.split('/').pop()))
  // 4. Last-two-segments overlap
  if(!file&&src.path.includes('/')){const tail=src.path.split('/').slice(-2).join('/');file=files.find(f=>f.path.includes(tail))}
  // 5. Fuzzy: most path segments in common
  if(!file){
    const srcSegs=new Set(src.path.split('/').filter(Boolean))
    let bestScore=-1
    files.forEach(f=>{const score=[...f.path.split('/').filter(Boolean)].filter(s=>srcSegs.has(s)).length;if(score>bestScore){bestScore=score;file=f}})
  }
  if(!file)return

  // Find best-matching chunk
  let chunk=null
  if(src.sl>0){
    // Prefer chunk that contains the line
    chunk=file.chunks.find(c=>c.start_line<=src.sl&&src.sl<=(c.end_line||src.sl))
    // Fallback: closest start_line
    if(!chunk)chunk=file.chunks.reduce((b,c)=>!b||Math.abs(c.start_line-src.sl)<Math.abs(b.start_line-src.sl)?c:b,null)
  }
  if(!chunk)chunk=file.chunks[0]
  if(!chunk)return

  // ── Vue-reactive Set updates (must assign new Set, not mutate) ──
  const newDirs=new Set(expandedDirs.value)
  let pf=''
  file.path.split('/').slice(0,-1).forEach(seg=>{pf=pf?`${pf}/${seg}`:seg;newDirs.add(pf)})
  expandedDirs.value=newDirs
  expandedFiles.value=new Set([...expandedFiles.value,file.path])

  // Set selection state
  selectedFile.value=file.path
  selectedChunk.value=chunk

  // Switch tab
  activeTab.value='structure'

  // Wait for Vue to fully re-render (two ticks: tab switch + tree re-render)
  await nextTick()
  await nextTick()

  // Scroll tree panel to show the file row
  const treeRow=document.querySelector(`.str-tree [data-path="${CSS.escape(file.path)}"]`)
  treeRow?.scrollIntoView({behavior:'smooth',block:'center'})

  // Scroll detail panel to top
  document.querySelector('.str-det')?.scrollTo({top:0,behavior:'smooth'})
}

// ── Chat click: cite [N] inline → jump to source ─────────────────
const onChatClick=(e)=>{
  const cite=e.target.closest('.mcite')
  if(!cite)return
  const n=+cite.dataset.n
  // Walk up DOM to get the enclosing message ID for scoped source lookup
  const msgEl=cite.closest('[data-msgid]')
  let src=null
  if(msgEl){
    const id=+msgEl.dataset.msgid
    src=(msgSources.value[id]||[]).find(s=>s.n===n)
  }
  // Fallback: search most-recent messages first
  if(!src){
    for(const id of Object.keys(msgSources.value).map(Number).sort((a,b)=>b-a)){
      src=(msgSources.value[id]||[]).find(s=>s.n===n)
      if(src)break
    }
  }
  if(src)jumpToSource(src)
}

const sendMessage=async()=>{
  const q=chatInput.value.trim()
  const readyFiles=uploadedFiles.value.filter(f=>!f.loading&&!f.error)
  if((!q&&!readyFiles.length)||!repoId.value||isAnswering.value)return

  // Build enriched question embedding file content
  const txtFiles=readyFiles.filter(f=>f.contentType==='text'&&f.text)
  const imgFiles=readyFiles.filter(f=>f.contentType==='image'&&f.base64)
  let fullQ=q

  if(txtFiles.length){
    const ctx=txtFiles.map(f=>[
      `📎 文件: ${f.name}${f.pageCount?` (${f.pageCount}页)`:''} · ${f.charCount}字${f.truncated?' [已截断]':''}`,
      '─'.repeat(40),f.text,'─'.repeat(40)
    ].join('\n')).join('\n\n')
    fullQ=`${ctx}\n\n${q||'请结合以上文件内容和代码库回答问题。'}`
  } else if(imgFiles.length){
    fullQ=`${imgFiles.map(f=>`📎 图片: ${f.name} (${fmtSize(f.size)})`).join('\n')}\n\n${q||'请分析以上图片，结合代码库回答问题。'}`
  }

  const attachments=[...uploadedFiles.value]
  uploadedFiles.value=[]
  chatInput.value=''

  chatMessages.value.push({role:'user',content:q||'（已上传文件）',id:Date.now(),attachments})
  isAnswering.value=true
  const aiMsg={role:'assistant',raw:'',html:'',id:Date.now()+1,streaming:true,sources:[]}
  chatMessages.value.push(aiMsg);twQ='';twMsg=null;await nextTick();scrollChat()

  const reqBody={repo_id:repoId.value,question:fullQ}
  if(imgFiles.length)reqBody.images=imgFiles.map(f=>({base64:f.base64,media_type:f.mediaType,filename:f.name}))

  try{
    const res=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json',...(authToken.value?{Authorization:`Bearer ${authToken.value}`}:{})},body:JSON.stringify(reqBody)})
    if(!res.ok||!res.body){const er=await res.json();aiMsg.raw=er.detail||'请求失败';aiMsg.html=renderMD(aiMsg.raw);return}
    const reader=res.body.getReader(),dec=new TextDecoder();let buf=''
    while(true){const{done,value}=await reader.read();if(done)break;buf+=dec.decode(value,{stream:true});const evts=buf.split('\n\n');buf=evts.pop()||'';for(const evt of evts){const txt=evt.split('\n').filter(l=>l.startsWith('data: ')).map(l=>l.slice(6)).join('\n');if(txt==='[DONE]')break;queueTW(aiMsg,txt)}}
    await new Promise(r=>{const ck=()=>{if(!twQ.length&&!twRaf)r();else setTimeout(ck,40)};ck()})
    const srcs=extractSources(aiMsg.raw);aiMsg.sources=srcs;msgSources.value[aiMsg.id]=srcs
  }catch(e){aiMsg.raw=e.message||'服务异常';aiMsg.html=renderMD(aiMsg.raw)}
  finally{aiMsg.streaming=false;isAnswering.value=false;await nextTick();scrollChat()}
}

// ── Lifecycle ───────────────────────────────────────────────────
const loadLibs=()=>{
  if(!document.getElementById('ktx-css')){const l=document.createElement('link');l.id='ktx-css';l.rel='stylesheet';l.href='https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.css';document.head.appendChild(l)}
  if(!document.getElementById('ktx-js')){const s=document.createElement('script');s.id='ktx-js';s.src='https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.9/katex.min.js';document.head.appendChild(s)}
}
onMounted(()=>{
  loadLibs()
  const tok=localStorage.getItem('auth_token'),usr=localStorage.getItem('auth_user')
  if(tok&&usr)try{authToken.value=tok;currentUser.value=JSON.parse(usr);currentView.value='main'}catch{handleLogout()}
  resizeObs=new ResizeObserver(()=>{const w=kgWrapRef.value,cv=canvasRef.value;if(!w||!cv)return;cv.width=w.clientWidth;cv.height=Math.max(380,w.clientHeight-56);if(simNodes.length)drawKG(cv)})
  callResObs=new ResizeObserver(()=>{const w=callWrapRef.value,cv=callCanvasRef.value;if(!w||!cv)return;cv.width=w.clientWidth;cv.height=Math.max(380,w.clientHeight-56);if(callNodes.length)drawCG(cv)})
})
onUnmounted(()=>{[animFrame,callFrame,twRaf].forEach(f=>f&&cancelAnimationFrame(f));[resizeObs,callResObs].forEach(o=>o?.disconnect())})
watch(activeTab,async(tab)=>{
  if(['structure','preview'].includes(tab)&&repoId.value&&!structureData.value)loadStructure()
  if(tab==='graph')await nextTick().then(()=>{if(kgWrapRef.value&&canvasRef.value){resizeObs?.observe(kgWrapRef.value);const cv=canvasRef.value,w=kgWrapRef.value;cv.width=w.clientWidth;cv.height=Math.max(380,w.clientHeight-56);if(repoId.value&&!simNodes.length&&structureData.value)buildKGraph();else if(simNodes.length)drawKG(cv)}})
  if(tab==='visual')await nextTick().then(()=>{if(callWrapRef.value&&callCanvasRef.value){callResObs?.observe(callWrapRef.value);const cv=callCanvasRef.value,w=callWrapRef.value;cv.width=w.clientWidth;cv.height=Math.max(380,w.clientHeight-56);if(visualSubTab.value==='callgraph'&&repoId.value&&!callNodes.length&&structureData.value)buildCallGraph();else if(callNodes.length)drawCG(cv)}if(visualSubTab.value==='treemap'&&repoId.value&&!structureData.value)loadStructure()})
})
watch(graphFilter,()=>{if(repoId.value&&structureData.value)buildKGraph()})
watch(visualSubTab,async(st)=>{if(st==='callgraph'){await nextTick();if(callCanvasRef.value&&callWrapRef.value){const cv=callCanvasRef.value,w=callWrapRef.value;cv.width=w.clientWidth;cv.height=Math.max(380,w.clientHeight-56);if(repoId.value&&structureData.value&&!callNodes.length)buildCallGraph();else if(callNodes.length)drawCG(cv)}}if(st==='treemap'&&repoId.value&&!structureData.value)loadStructure()})
</script>

<template>
<div v-if="currentView==='auth'" class="auth-wrap">
  <div class="auth-bg">
    <div class="abg-grid"></div>
    <div class="abg-glow g1"></div><div class="abg-glow g2"></div><div class="abg-glow g3"></div>
    <div class="abg-particles"><span v-for="i in 20" :key="i" :style="`--d:${(i-1)*18}deg;--sz:${6+i%4*3}px;--sp:${3+i%5}s;--dl:${i*.4}s`" class="particle"></span></div>
  </div>
  <div class="auth-card">
    <div class="ac-logo"><svg width="36" height="36" viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="17" stroke="url(#lg1)" stroke-width="1.5"/><path d="M10 18L18 10L26 18L18 26Z" fill="none" stroke="url(#lg1)" stroke-width="1.5"/><circle cx="18" cy="18" r="3.5" fill="url(#lg1)" opacity=".9"/><line x1="18" y1="10" x2="18" y2="6" stroke="#00FFD4" stroke-width="1.5" stroke-linecap="round"/><line x1="18" y1="26" x2="18" y2="30" stroke="#00FFD4" stroke-width="1.5" stroke-linecap="round"/><line x1="10" y1="18" x2="6" y2="18" stroke="#818CF8" stroke-width="1.5" stroke-linecap="round"/><line x1="26" y1="18" x2="30" y2="18" stroke="#818CF8" stroke-width="1.5" stroke-linecap="round"/><defs><linearGradient id="lg1" x1="0" y1="0" x2="36" y2="36" gradientUnits="userSpaceOnUse"><stop stop-color="#00FFD4"/><stop offset="1" stop-color="#818CF8"/></linearGradient></defs></svg><span class="ac-name">CodeCompass</span></div>
    <p class="ac-sub">面向初学者的 GitHub 仓库智能解析助手</p>
    <div v-if="authMode==='login'||authMode==='register'" class="ac-tabs"><button :class="['act',authMode==='login'&&'on']" @click="switchAuth('login')">登录</button><button :class="['act',authMode==='register'&&'on']" @click="switchAuth('register')">注册</button></div>
    <transition name="ale"><div v-if="authError"   class="ac-alert ae">⚠ {{ authError }}</div></transition>
    <transition name="ale"><div v-if="authSuccess" class="ac-alert ao">✓ {{ authSuccess }}</div></transition>
    <form v-if="authMode==='login'" class="acf" @submit.prevent="handleLogin">
      <div class="fld"><label>邮箱</label><input v-model="loginForm.email" type="email" placeholder="your@email.com" required/></div>
      <div class="fld"><label>密码</label><div class="pw"><input v-model="loginForm.password" :type="loginForm.show?'text':'password'" placeholder="••••••••" required/><button type="button" class="eye" @click="loginForm.show=!loginForm.show">{{ loginForm.show?'🙈':'👁' }}</button></div></div>
      <button type="submit" class="btn-prime" :disabled="authLoading"><span v-if="authLoading" class="sp"></span><span v-else>登录账号</span></button>
      <p class="ac-link"><a href="#" @click.prevent="switchAuth('forgot')">忘记密码？</a></p>
    </form>
    <form v-if="authMode==='register'" class="acf" @submit.prevent="handleRegister">
      <div class="fld"><label>用户名</label><input v-model="regForm.username" type="text" placeholder="coolcoder" required/></div>
      <div class="fld"><label>邮箱</label><input v-model="regForm.email" type="email" placeholder="your@email.com" required/></div>
      <div class="fld"><label>密码</label><div class="pw"><input v-model="regForm.password" :type="regForm.show?'text':'password'" placeholder="至少 8 位" required/><button type="button" class="eye" @click="regForm.show=!regForm.show">{{ regForm.show?'🙈':'👁' }}</button></div>
        <div v-if="regForm.password" class="pwm"><div class="pwb"><div :style="{width:(pwdStr/5*100)+'%',background:pwdClr}" class="pwf"></div></div><span :style="{color:pwdClr}" class="pwl">{{ pwdLbl }}</span></div>
      </div>
      <div class="fld"><label>确认密码</label><input v-model="regForm.confirm" :type="regForm.show?'text':'password'" placeholder="再次输入" required/><span v-if="regForm.confirm&&regForm.password!==regForm.confirm" class="ferr">密码不一致</span></div>
      <button type="submit" class="btn-prime" :disabled="authLoading"><span v-if="authLoading" class="sp"></span><span v-else>创建账号</span></button>
    </form>
    <form v-if="authMode==='forgot'" class="acf" @submit.prevent="handleForgot">
      <button type="button" class="bk-btn" @click="switchAuth('login')">← 返回</button><h3 class="ac-h">找回密码</h3>
      <div class="fld"><label>邮箱</label><input v-model="forgotForm.email" type="email" placeholder="your@email.com" required/></div>
      <div v-if="forgotForm.sent&&forgotForm.resetToken" class="dev-box"><span class="dev-b">开发模式</span>令牌：<code>{{ forgotForm.resetToken }}</code><button type="button" class="lnk" @click="switchAuth('reset')">使用此令牌 →</button></div>
      <button type="submit" class="btn-prime" :disabled="authLoading||forgotForm.sent"><span v-if="authLoading" class="sp"></span><span v-else>{{ forgotForm.sent?'已发送':'发送重置链接' }}</span></button>
    </form>
    <form v-if="authMode==='reset'" class="acf" @submit.prevent="handleReset">
      <button type="button" class="bk-btn" @click="switchAuth('forgot')">← 返回</button><h3 class="ac-h">设置新密码</h3>
      <div class="fld"><label>重置令牌</label><input v-model="resetForm.token" type="text" placeholder="粘贴重置令牌" required/></div>
      <div class="fld"><label>新密码</label><div class="pw"><input v-model="resetForm.password" :type="resetForm.show?'text':'password'" placeholder="至少 8 位" required/><button type="button" class="eye" @click="resetForm.show=!resetForm.show">{{ resetForm.show?'🙈':'👁' }}</button></div></div>
      <div class="fld"><label>确认密码</label><input v-model="resetForm.confirm" :type="resetForm.show?'text':'password'" placeholder="再次输入" required/></div>
      <button type="submit" class="btn-prime" :disabled="authLoading"><span v-if="authLoading" class="sp"></span><span v-else>重置密码</span></button>
    </form>
  </div>
</div>

<div v-else class="app">
  <aside class="sb">
    <div class="sb-logo"><svg width="28" height="28" viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="17" stroke="url(#slg)" stroke-width="1.5"/><path d="M10 18L18 10L26 18L18 26Z" fill="none" stroke="url(#slg)" stroke-width="1.5"/><circle cx="18" cy="18" r="3.5" fill="url(#slg)" opacity=".9"/><defs><linearGradient id="slg" x1="0" y1="0" x2="36" y2="36"><stop stop-color="#00FFD4"/><stop offset="1" stop-color="#818CF8"/></linearGradient></defs></svg><span>CodeCompass</span></div>
    <div class="sb-repo">
      <input v-model="repoUrl" class="si" type="text" placeholder="GitHub URL / 本地路径" @keyup.enter="handleIndexRepo"/>
      <div class="sbr-row"><input v-model="repoBranch" class="si br" type="text" placeholder="main"/><button class="btn-idx" :disabled="!repoUrl.trim()||isIndexing" @click="handleIndexRepo" title="开始索引"><span v-if="isIndexing" class="sp xs"></span><svg v-else width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg></button></div>
      <div v-if="repoStatus" class="rst">{{ repoStatus }}</div>
    </div>
    <nav class="sbnav">
      <button v-for="t in [{id:'preview',g:'🗂',l:'文件浏览',c:'#60A5FA'},{id:'structure',g:'🔍',l:'代码解析',c:'#00FFD4'},{id:'graph',g:'🧠',l:'图谱统计',c:'#818CF8'},{id:'visual',g:'🎨',l:'可视化',c:'#F472B6'},{id:'chat',g:'💬',l:'智能问答',c:'#FBBF24'}]"
        :key="t.id" :class="['snav',activeTab===t.id&&'on']" :style="activeTab===t.id?`--nc:${t.c}`:''" @click="activeTab=t.id">
        <span class="sni">{{ t.g }}</span><span class="snl">{{ t.l }}</span>
        <span v-if="t.id==='chat'&&chatMessages.filter(m=>m.role==='user').length" class="snbg">{{ chatMessages.filter(m=>m.role==='user').length }}</span>
      </button>
    </nav>
    <div class="sb-usr">
      <div class="uav">{{ (currentUser?.username||'?')[0].toUpperCase() }}</div>
      <div class="uif"><span class="unm">{{ currentUser?.username||'游客' }}</span><span class="uem">{{ currentUser?.email||'' }}</span></div>
      <button class="uout" @click="handleLogout" title="退出"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/></svg></button>
    </div>
  </aside>

  <main class="ma">

    <!-- ═══ FILE BROWSER ═══════════════════════════════════════ -->
    <div v-show="activeTab==='preview'" class="panel">
      <div class="ph"><h2 class="pt grd">🗂 文件浏览</h2><div class="pa"><input v-model="previewSearch" class="si sm" placeholder="搜索内容…"/><button v-if="repoId" class="btn-sm" @click="loadStructure" :disabled="structureLoading">{{ structureLoading?'…':'🔄' }}</button></div></div>
      <div v-if="!repoId" class="empty"><div class="eic">🗂</div><p>请先索引仓库</p></div>
      <div v-else-if="structureLoading" class="empty"><div class="sp lg"></div><p>加载中…</p></div>
      <div v-else-if="structureData" class="pv-lay">
        <div class="pv-tree">
          <div class="pv-hd">{{ structureData.total_files }} 个文件 · {{ structureData.total_chunks }} 片段</div>
          <button v-for="file in structureData.files" :key="file.path" :class="['pvf',previewFile===file.path&&'on']" :data-path="file.path" @click="previewFile=file.path">
            <span>{{ fi(file.language) }}</span><span class="pvfn" :title="file.path">{{ file.path }}</span><span class="pvfc">{{ file.chunks.length }}</span>
          </button>
        </div>
        <div class="pv-view">
          <div v-if="!previewFile" class="empty"><div class="eic" style="font-size:26px">←</div><p>从左侧选择文件</p></div>
          <template v-else>
            <div class="pv-fhd">
              <span class="pv-fi">{{ fi(structureData.files.find(f=>f.path===previewFile)?.language) }}</span>
              <span class="pv-fp">{{ previewFile }}</span>
              <span class="pv-fm">{{ previewLines.length }} 行</span>
              <span v-if="previewSearch" class="pv-mc">{{ previewLines.filter(l=>l.hl).length }} 处匹配</span>
            </div>
            <div class="pv-code-w"><div class="pv-code"><div v-for="l in previewLines" :key="l.num" :class="['pvl',l.hl&&'hl']"><span class="ln">{{ l.num }}</span><span class="lc">{{ l.text }}</span></div></div></div>
          </template>
        </div>
      </div>
      <div v-else class="empty"><p>点击加载文件内容</p><button class="btn-prime sm" style="margin-top:14px" @click="loadStructure">加载</button></div>
    </div>

    <!-- ═══ CODE ANALYSIS ══════════════════════════════════════ -->
    <div v-show="activeTab==='structure'" class="panel">
      <div class="ph"><h2 class="pt grd">🔍 代码解析</h2><div class="pa"><input v-model="structSearch" class="si sm" placeholder="搜索片段…"/><button v-if="repoId" class="btn-sm" @click="loadStructure" :disabled="structureLoading">{{ structureLoading?'…':'🔄' }}</button></div></div>
      <div v-if="!repoId" class="empty"><div class="eic">🔍</div><p>请先索引仓库</p></div>
      <div v-else-if="structureLoading" class="empty"><div class="sp lg"></div><p>解析结构中…</p></div>
      <div v-else-if="structureData" class="str-lay">
        <div class="str-tree">
          <div class="str-hd">📁 {{ structureData.total_files }} 文件 · {{ structureData.total_chunks }} 片段</div>
          <div v-for="node in flatTree" :key="node.type+node.path+(node.chunk?.chunk_id??'')" :style="{paddingLeft:(node.depth*13+8)+'px'}" :class="['tr',`tr-${node.type}`,node.type==='chunk'&&selectedChunk===node.chunk&&'on']">
            <button v-if="node.type==='dir'" class="trb" @click="toggleDir(node.path)"><span class="tra">{{ expandedDirs.has(node.path)?'▾':'▸' }}</span><span>📁</span><span class="trn">{{ node.name }}/</span></button>
            <button v-else-if="node.type==='file'" class="trb" :data-path="node.path" @click="toggleFile(node.path)"><span class="tra">{{ expandedFiles.has(node.path)?'▾':'▸' }}</span><span>{{ fi(node.language) }}</span><span class="trn">{{ node.name }}</span><span class="trc">{{ node.chunks.length }}</span></button>
            <button v-else class="trb trc-btn" @click="selectChunk(node.chunk,node.filePath)"><span class="ckb" :style="{background:(CC[node.chunk.chunk_type]||'#94A3B8')+'22',color:CC[node.chunk.chunk_type]||'#94A3B8',borderColor:(CC[node.chunk.chunk_type]||'#94A3B8')+'55'}">{{ CL[node.chunk.chunk_type]||node.chunk.chunk_type }}</span><span class="trn mono">{{ node.chunk.name||'(anonymous)' }}</span><span v-if="node.chunk.is_async" class="async-tag">A</span></button>
          </div>
        </div>
        <div class="str-det">
          <div v-if="!selectedChunk" class="empty"><div class="eic" style="font-size:26px">←</div><p>选择代码片段查看语义分析</p></div>
          <div v-else class="sdi">
            <div class="sdi-head">
              <div class="sdi-badges"><span class="ckb lg" :style="{background:(CC[selectedChunk.chunk_type]||'#94A3B8')+'22',color:CC[selectedChunk.chunk_type]||'#94A3B8'}">{{ CL[selectedChunk.chunk_type]||selectedChunk.chunk_type }}</span><span v-if="selectedChunk.is_async" class="async-tag lg">async</span><span v-if="selectedChunk.is_exported" class="exp-tag lg">export</span></div>
              <h3 class="sdi-title">{{ selectedChunk.name||'(anonymous)' }}</h3>
              <div class="sdi-loc"><code>{{ selectedFile }}</code> · 第 {{ selectedChunk.start_line }}–{{ selectedChunk.end_line }} 行</div>
            </div>
            <!-- Complexity gauge -->
            <div class="cmplx-row">
              <span class="mk">复杂度</span>
              <div class="cmplx-bar"><div class="cmplx-fill" :style="{width:computeComplexity(selectedChunk)+'%',background:`linear-gradient(90deg,#34D399,${computeComplexity(selectedChunk)>60?'#F87171':'#FBBF24'})`}"></div></div>
              <span class="cmplx-val" :style="{color:computeComplexity(selectedChunk)>60?'#F87171':computeComplexity(selectedChunk)>30?'#FBBF24':'#34D399'}">{{ computeComplexity(selectedChunk) }}</span>
            </div>
            <!-- Metadata grid -->
            <div class="mgrid">
              <div v-if="selectedChunk.params"       class="mc"><span class="mk">参数</span><code class="mv">{{ selectedChunk.params }}</code></div>
              <div v-if="selectedChunk.return_type"  class="mc"><span class="mk">返回值</span><code class="mv">{{ selectedChunk.return_type }}</code></div>
              <div v-if="selectedChunk.base_classes" class="mc"><span class="mk">继承</span><code class="mv">{{ selectedChunk.base_classes }}</code></div>
              <div v-if="selectedChunk.decorators"   class="mc"><span class="mk">装饰器</span><code class="mv">{{ selectedChunk.decorators }}</code></div>
              <div v-if="selectedChunk.access"       class="mc"><span class="mk">访问</span><code class="mv">{{ selectedChunk.access }}</code></div>
            </div>
            <!-- Docstring -->
            <div v-if="selectedChunk.docstring" class="sdi-doc"><span class="mk">文档注释</span><p>{{ selectedChunk.docstring }}</p></div>
            <!-- Call analysis -->
            <div class="call-analysis">
              <div v-if="findCalls(selectedChunk).length" class="call-sec">
                <span class="mk">调用了 →</span>
                <div class="cref-list">
                  <button v-for="c in findCalls(selectedChunk)" :key="c.chunk_id" class="cref" :style="{borderColor:(CC[c.chunk_type]||'#94A3B8')+'55',color:CC[c.chunk_type]||'#94A3B8'}" @click="selectChunk(c,c.fp)">{{ CL[c.chunk_type]||c.chunk_type }} · {{ c.name }}</button>
                </div>
              </div>
              <div v-if="findCalledBy(selectedChunk).length" class="call-sec">
                <span class="mk">被调用 ←</span>
                <div class="cref-list">
                  <button v-for="c in findCalledBy(selectedChunk)" :key="c.chunk_id" class="cref" :style="{borderColor:(CC[c.chunk_type]||'#94A3B8')+'55',color:CC[c.chunk_type]||'#94A3B8'}" @click="selectChunk(c,c.fp)">{{ CL[c.chunk_type]||c.chunk_type }} · {{ c.name }}</button>
                </div>
              </div>
            </div>
            <!-- Full code -->
            <div class="sdi-code">
              <div class="sdi-code-hd"><span class="mk">完整代码</span><span class="code-meta">{{ (selectedChunk.content||'').split('\n').length }} 行</span><button class="btn-explain" @click="explainChunk(selectedChunk)">🤖 AI 解释</button></div>
              <div class="code-scroller"><div class="pv-code"><div v-for="(ln,i) in (selectedChunk.content||selectedChunk.content_preview||'').split('\n')" :key="i" class="pvl"><span class="ln">{{ (selectedChunk.start_line||1)+i }}</span><span class="lc">{{ ln }}</span></div></div></div>
            </div>
            <!-- Related in same file -->
            <div v-if="structureData" class="sdi-rel">
              <span class="mk">同文件其他片段</span>
              <div class="rel-chips">
                <button v-for="c in (structureData.files.find(f=>f.chunks.includes(selectedChunk))?.chunks||[]).filter(c=>c!==selectedChunk).slice(0,10)" :key="c.chunk_id" class="rel-chip" :style="{borderColor:(CC[c.chunk_type]||'#94A3B8')+'55',color:CC[c.chunk_type]||'#94A3B8'}" @click="selectedChunk=c">{{ CL[c.chunk_type]||c.chunk_type }} · {{ c.name||'?' }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="empty"><p>点击加载代码结构</p><button class="btn-prime sm" style="margin-top:14px" @click="loadStructure">加载</button></div>
    </div>

    <!-- ═══ GRAPH + METRICS ════════════════════════════════════ -->
    <div v-show="activeTab==='graph'" class="panel" ref="kgWrapRef" style="position:relative">
      <div class="ph"><h2 class="pt grd">🧠 图谱 &amp; 统计</h2>
        <div class="pa" style="gap:6px;flex-wrap:wrap">
          <div class="sub-tabs"><button :class="['stab',graphSubTab==='graph'&&'on']" @click="graphSubTab='graph'">知识图谱</button><button :class="['stab',graphSubTab==='metrics'&&'on']" @click="graphSubTab='metrics'">代码统计</button></div>
          <template v-if="graphSubTab==='graph'">
            <select v-model="graphFilter" class="sel-sm"><option value="all">全部</option><option value="function">函数</option><option value="class">类</option><option value="interface">接口</option></select>
            <span class="stat-badge">{{ graphStats.nodes }}节点 · {{ graphStats.edges }}边</span>
            <button class="btn-sm" @click="zoomGraph(1.18)">＋</button><button class="btn-sm" @click="zoomGraph(.83)">－</button>
            <button class="btn-sm" @click="resetGraph">↺</button>
            <button v-if="repoId&&structureData" class="btn-sm" @click="buildKGraph">🔄</button>
          </template>
        </div>
      </div>
      <div v-if="!repoId" class="empty"><div class="eic">🧠</div><p>请先索引仓库</p></div>
      <template v-else>
        <!-- Graph view -->
        <div v-show="graphSubTab==='graph'" style="flex:1;position:relative;overflow:hidden;display:flex;flex-direction:column">
          <canvas ref="canvasRef" class="kg-cv" @mousedown="onKgDown" @mousemove="onKgMove" @mouseup="onKgUp" @mouseleave="onKgLeave" @wheel.prevent="onKgWheel" @dblclick="clickKgNode"></canvas>
          <div v-if="graphTooltip" class="kg-tip" :style="{left:ttPos.x+'px',top:ttPos.y+'px'}">
            <div class="ktt" :style="{color:CC[graphTooltip.type?.toLowerCase()]||'#818CF8'}">{{ graphTooltip.type }}</div>
            <div class="ktn">{{ graphTooltip.name }}</div>
            <div v-if="graphTooltip.full&&graphTooltip.full!==graphTooltip.name" class="ktf">{{ graphTooltip.full }}</div>
            <div v-if="graphTooltip.lang"   class="ktm">语言: {{ graphTooltip.lang }}</div>
            <div v-if="graphTooltip.chunks" class="ktm">片段: {{ graphTooltip.chunks }}</div>
            <div v-if="graphTooltip.params" class="ktm">参数: {{ graphTooltip.params }}</div>
            <div v-if="graphTooltip.ret"    class="ktm">返回: {{ graphTooltip.ret }}</div>
            <div v-if="graphTooltip.lines&&graphTooltip.lines!=='0-0'" class="ktm">行: {{ graphTooltip.lines }}</div>
            <div v-if="graphTooltip.async"  class="kta">⚡ 异步</div>
            <div class="ktd">双击跳转到代码解析</div>
          </div>
          <div class="kg-leg"><span v-for="(c,l) in {'文件':'#818CF8','函数':'#00FFD4','类':'#F472B6','接口':'#FBBF24','其他':'#94A3B8'}" :key="l" class="kll"><span :style="{background:c}" class="kld"></span>{{ l }}</span><span class="klh">拖拽 · 滚轮缩放 · 悬停查看 · 双击跳转</span></div>
        </div>
        <!-- Metrics view -->
        <div v-if="graphSubTab==='metrics'" class="metrics-wrap">
          <div v-if="!metricsData" class="empty"><p>请先加载仓库结构</p><button class="btn-prime sm" @click="loadStructure">加载</button></div>
          <div v-else class="metrics-inner">
            <div class="sc-row">
              <div class="sc" v-for="(v,l) in [{v:metricsData.totalFiles,l:'文件总数',c:'#00FFD4'},{v:metricsData.totalChunks,l:'代码片段',c:'#818CF8'},{v:Object.keys(metricsData.langs).length,l:'编程语言',c:'#F472B6'},{v:metricsData.async_.total?Math.round(metricsData.async_.async/metricsData.async_.total*100):0,l:'异步占比%',c:'#FBBF24'},{v:metricsData.totalLines.toLocaleString(),l:'代码行数',c:'#34D399'}]" :key="l.l"><div class="scv" :style="{color:l.c}">{{ l.v }}</div><div class="scl">{{ l.l }}</div></div>
            </div>
            <div class="mcharts">
              <div class="mc-card">
                <h3 class="mc-title">语言分布</h3>
                <div class="donut-wr">
                  <svg width="190" height="190" viewBox="0 0 190 190">
                    <path v-for="s in metricsData.donut" :key="s.lang" :d="s.d" :fill="s.color" opacity=".85" style="cursor:pointer;transition:opacity .2s" @mouseenter="hovTmFile=s.lang" @mouseleave="hovTmFile=null" :stroke="hovTmFile===s.lang?s.color:'none'" :stroke-width="hovTmFile===s.lang?2:0"/>
                    <text x="95" y="91" text-anchor="middle" fill="#E8F4FF" font-size="22" font-weight="700" font-family="Rajdhani,sans-serif">{{ metricsData.totalFiles }}</text>
                    <text x="95" y="108" text-anchor="middle" fill="#7EB8D0" font-size="10" font-family="DM Sans,sans-serif">文件</text>
                  </svg>
                  <div class="dleg">
                    <div v-for="(s,i) in metricsData.donut" :key="s.lang" class="dle" :class="hovTmFile===s.lang&&'hl'" @mouseenter="hovTmFile=s.lang" @mouseleave="hovTmFile=null">
                      <span :style="{background:s.color}" class="dld"></span><span class="dll">{{ s.lang }}</span><span class="dlc">{{ s.cnt }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div class="mc-card flex1">
                <h3 class="mc-title">Top 10 文件（片段数）</h3>
                <div class="bar-list">
                  <div v-for="(f,i) in metricsData.topFiles" :key="f.path" class="bar-row" @click="previewFile=f.path;activeTab='preview'" style="cursor:pointer" @mouseenter="hovTmFile=f.path" @mouseleave="hovTmFile=null">
                    <span class="blbl" :title="f.path">{{ f.path.split('/').pop() }}</span>
                    <div class="btr"><div class="bfill" :style="{width:(f.chunks.length/metricsData.maxC*100)+'%',background:LC[i%LC.length]+(hovTmFile===f.path?'ff':'cc'),boxShadow:hovTmFile===f.path?`0 0 8px ${LC[i%LC.length]}88`:''}"></div></div>
                    <span class="bval">{{ f.chunks.length }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="mc-card fullw">
              <h3 class="mc-title">片段类型分布</h3>
              <div class="tbars">
                <div v-for="([tp,cnt]) in metricsData.typeE" :key="tp" class="tbar-row">
                  <span class="ckb sm" :style="{background:(CC[tp]||'#94A3B8')+'22',color:CC[tp]||'#94A3B8',borderColor:(CC[tp]||'#94A3B8')+'55',minWidth:'80px',textAlign:'center'}">{{ CL[tp]||tp }}</span>
                  <div class="btr"><div class="bfill" :style="{width:(cnt/metricsData.maxT*100)+'%',background:CC[tp]||'#94A3B8'}"></div></div>
                  <span class="bval">{{ cnt }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══ VISUALIZATION ══════════════════════════════════════ -->
    <div v-show="activeTab==='visual'" class="panel" ref="callWrapRef">
      <div class="ph"><h2 class="pt grd">🎨 可视化</h2>
        <div class="pa">
          <div class="sub-tabs"><button :class="['stab',visualSubTab==='treemap'&&'on']" @click="visualSubTab='treemap'">📦 文件地图</button><button :class="['stab',visualSubTab==='callgraph'&&'on']" @click="visualSubTab='callgraph'">🔗 调用链路</button></div>
          <button v-if="visualSubTab==='callgraph'&&repoId&&structureData" class="btn-sm" @click="buildCallGraph">🔄</button>
          <button v-if="visualSubTab==='callgraph'" class="btn-sm" @click="resetCG">↺</button>
        </div>
      </div>
      <div v-if="!repoId" class="empty"><div class="eic">🎨</div><p>请先索引仓库</p></div>
      <!-- Treemap -->
      <div v-else-if="visualSubTab==='treemap'" class="tm-wrap">
        <div v-if="!structureData" class="empty"><div class="sp lg"></div></div>
        <template v-else>
          <p class="vis-hint">文件大小 = 代码片段数量 · 颜色 = 文件类型 · 点击跳转到文件浏览</p>
          <div class="tm-svg-w">
            <svg viewBox="0 0 780 450" class="tm-svg">
              <g v-for="nd in treemapData" :key="nd.id" style="cursor:pointer" @mouseenter="hovTmFile=nd.id" @mouseleave="hovTmFile=null" @click="previewFile=nd.path;activeTab='preview'">
                <rect :x="nd.x+1.5" :y="nd.y+1.5" :width="Math.max(0,nd.w-3)" :height="Math.max(0,nd.h-3)" :fill="nd.color+(hovTmFile===nd.id?'44':'18')" :stroke="nd.color" :stroke-width="hovTmFile===nd.id?2:1" rx="4" style="transition:all .2s"/>
                <text v-if="nd.w>48&&nd.h>22" :x="nd.x+nd.w/2" :y="nd.y+nd.h/2-(nd.h>38?7:0)" text-anchor="middle" dominant-baseline="middle" :fill="nd.color" font-size="10.5" font-family="Fira Code,monospace" style="pointer-events:none">{{ nd.name.length>nd.w/9?nd.name.slice(0,Math.max(3,Math.floor(nd.w/9)-1))+'…':nd.name }}</text>
                <text v-if="nd.w>56&&nd.h>42" :x="nd.x+nd.w/2" :y="nd.y+nd.h/2+8" text-anchor="middle" :fill="nd.color+'99'" font-size="9" font-family="DM Sans,sans-serif" style="pointer-events:none">{{ nd.chunks }} 片段</text>
              </g>
              <!-- Hover highlight -->
              <rect v-if="hovTmFile" :x="treemapData.find(n=>n.id===hovTmFile)?.x+1.5" :y="treemapData.find(n=>n.id===hovTmFile)?.y+1.5" :width="Math.max(0,(treemapData.find(n=>n.id===hovTmFile)?.w||0)-3)" :height="Math.max(0,(treemapData.find(n=>n.id===hovTmFile)?.h||0)-3)" fill="none" :stroke="treemapData.find(n=>n.id===hovTmFile)?.color||'#fff'" stroke-width="2.5" rx="4" style="pointer-events:none"/>
            </svg>
          </div>
          <div v-if="hovTmFile" class="tm-tooltip">
            {{ treemapData.find(n=>n.id===hovTmFile)?.path }} · {{ fi(treemapData.find(n=>n.id===hovTmFile)?.lang) }} · {{ treemapData.find(n=>n.id===hovTmFile)?.chunks }} 片段
          </div>
        </template>
      </div>
      <!-- Call graph -->
      <div v-else class="cg-wrap" style="position:relative;flex:1;display:flex;flex-direction:column">
        <div v-if="!structureData" class="empty"><div class="sp lg"></div></div>
        <template v-else-if="!callNodes.length">
          <div class="empty"><div class="eic">🔗</div><p>点击构建函数调用链路图</p><button class="btn-prime sm" style="margin-top:14px" @click="buildCallGraph">构建</button></div>
        </template>
        <template v-else>
          <canvas ref="callCanvasRef" class="kg-cv" @mousedown="onCgDown" @mousemove="onCgMove" @mouseup="onCgUp" @mouseleave="onCgLeave" @wheel.prevent="onCgWheel" @dblclick="clickCgNode"></canvas>
          <div v-if="callTooltip" class="kg-tip" :style="{left:ctPos.x+'px',top:ctPos.y+'px'}">
            <div class="ktt" :style="{color:CC[callTooltip.type?.toLowerCase()]||'#F472B6'}">{{ callTooltip.type }}</div>
            <div class="ktn">{{ callTooltip.name }}</div>
            <div v-if="callTooltip.file" class="ktf">{{ callTooltip.file }}</div>
            <div v-if="callTooltip.params" class="ktm">参数: {{ callTooltip.params }}</div>
            <div v-if="callTooltip.ret"    class="ktm">返回: {{ callTooltip.ret }}</div>
            <div v-if="callTooltip.lines&&callTooltip.lines!=='0-0'" class="ktm">行: {{ callTooltip.lines }}</div>
            <div v-if="callTooltip.async"  class="kta">⚡ 异步</div>
            <div class="ktd">双击跳转到代码解析</div>
          </div>
          <div class="kg-leg"><span class="klh">箭头方向 = 调用方向 · 节点数 {{ callNodes.length }} · 调用边 {{ callEdges.length }} · 拖拽 · 滚轮缩放 · 双击跳转</span></div>
        </template>
      </div>
    </div>

    <!-- ═══ CHAT ════════════════════════════════════════════════ -->
    <div v-show="activeTab==='chat'" class="panel chat-panel">
      <div class="ph"><h2 class="pt grd">💬 智能问答</h2>
        <span v-if="repoId" class="repo-pill">{{ repoId.slice(0,44) }}{{ repoId.length>44?'…':'' }}</span>
        <div class="pa">
          <span v-if="uploadedFiles.length" class="att-count">📎 {{ uploadedFiles.length }} 个文件待发送</span>
          <button v-if="chatMessages.length" class="btn-sm" @click="chatMessages=[];msgSources.value={}">清空</button>
        </div>
      </div>
      <div v-if="!repoId" class="empty"><div class="eic">💬</div><p>请先索引仓库，再开始问答</p></div>
      <div v-else class="chat-body" @click="onChatClick"
           @dragover.prevent="isDragOver=true" @dragleave.self="isDragOver=false" @drop="onDrop">
        <div v-if="isDragOver" class="drop-mask">
          <div class="drop-box"><span style="font-size:40px">📎</span><p>松开鼠标上传文件</p><p class="drop-sub">PDF · Word · Markdown · TXT · CSV · 图片</p></div>
        </div>
        <div v-if="!chatMessages.length" class="chat-wel">
          <div class="eic">👋</div>
          <h3 class="wt">你好，{{ currentUser?.username||'学习者' }}！</h3>
          <p class="ws">仓库已就绪，可直接提问或上传文件辅助解答</p>
          <div class="upl-hint"><span>📎</span> 支持 PDF · Word · Markdown · TXT · CSV · 图片  上传后可结合代码库一起解析</div>
          <div class="chips">
            <button v-for="s in ['这个项目的主要功能是什么？','项目用了哪些核心技术？','代码的整体架构？','有哪些重要的类和函数？']" :key="s" class="chip" @click="quickAsk(s)">{{ s }}</button>
          </div>
        </div>
        <template v-for="msg in chatMessages" :key="msg.id">
          <div :class="['msg',msg.role]" :data-msgid="msg.id">
            <div class="mav">{{ msg.role==='user'?(currentUser?.username||'U')[0].toUpperCase():'🤖' }}</div>
            <div class="mbody">
              <!-- Attachments display -->
              <div v-if="msg.attachments?.length" class="att-row">
                <div v-for="f in msg.attachments" :key="f.id" :class="['att-chip',f.error&&'att-err']">
                  <span class="att-ic">{{ f.icon }}</span>
                  <div class="att-info">
                    <span class="att-nm">{{ f.name }}</span>
                    <span class="att-sz" v-if="!f.error">{{ fmtSize(f.size) }}{{ f.pageCount?` · ${f.pageCount}页`:'' }}{{ f.charCount?` · ${f.charCount}字`:'' }}</span>
                    <span class="att-er" v-if="f.error">{{ f.error }}</span>
                  </div>
                  <img v-if="f.contentType==='image'&&f.base64" :src="`data:${f.mediaType};base64,${f.base64}`" class="att-thumb" alt=""/>
                </div>
              </div>
              <!-- User bubble -->
              <div v-if="msg.role==='user'" class="mbub user-b">{{ msg.content }}</div>
              <!-- AI bubble -->
              <div v-else class="mbub ai-b">
                <div class="mdc-wrap" v-html="msg.html||renderMD(msg.raw||msg.content||'')"></div>
                <span v-if="msg.streaming" class="tcur">▌</span>
                <div v-if="!msg.streaming&&msg.sources&&msg.sources.length" class="src-panel">
                  <div class="src-hd">📎 引用来源 <span class="src-cnt">{{ msg.sources.length }} 个</span></div>
                  <div class="src-grid">
                    <button v-for="src in msg.sources" :key="src.n" class="src-card" @click.stop="jumpToSource(src)">
                      <span class="src-num">[{{ src.n }}]</span>
                      <div class="src-info">
                        <span class="src-path">{{ src.path.split('/').pop() }}</span>
                        <span class="src-full">{{ src.path }}</span>
                        <span v-if="src.sl" class="src-lines">第 {{ src.sl }}–{{ src.el }} 行</span>
                      </div>
                      <span class="src-go">→ 跳转</span>
                    </button>
                  </div>
                  <details class="flow-det">
                    <summary class="flow-sum">⚡ 检索链路详情</summary>
                    <div class="flow-body">
                      <div class="fn fn-q">❓ {{ chatMessages[chatMessages.indexOf(msg)-1]?.content?.slice(0,80) }}{{ chatMessages[chatMessages.indexOf(msg)-1]?.content?.length>80?'…':'' }}</div>
                      <div class="farr">↓ 向量语义检索 + 关键词匹配</div>
                      <div class="fn-srcs">
                        <div v-for="s in msg.sources" :key="s.n" class="fn-src" @click="jumpToSource(s)" style="cursor:pointer">
                          <span class="src-num sm">[{{ s.n }}]</span>
                          <span class="fn-path">{{ s.path }}</span>
                          <span v-if="s.sl" class="fn-ln">行 {{ s.sl }}-{{ s.el }}</span>
                          <span class="fn-jmp">→</span>
                        </div>
                      </div>
                      <div class="farr">↓ LLM 上下文增强生成</div>
                      <div class="fn fn-ans">💡 基于 {{ msg.sources.length }} 个代码片段生成答案</div>
                    </div>
                  </details>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div ref="chatEndRef"></div>
      </div>
      <div v-if="repoId" class="chat-bottom">
        <!-- Pending file previews -->
        <div v-if="uploadedFiles.length" class="upl-preview">
          <div v-for="f in uploadedFiles" :key="f.id" :class="['upl-chip',f.loading&&'upl-loading',f.error&&'upl-err']">
            <span class="upl-ic">{{ f.loading?'⏳':f.error?'❌':f.icon }}</span>
            <div class="upl-meta">
              <span class="upl-nm">{{ f.name }}</span>
              <span class="upl-st" v-if="f.loading">解析中…</span>
              <span class="upl-st upl-er" v-else-if="f.error">{{ f.error }}</span>
              <span class="upl-st upl-ok" v-else>
                {{ f.contentType==='image' ? fmtSize(f.size) : `${f.charCount}字${f.pageCount?` · ${f.pageCount}页`:''}${f.truncated?' [截断]':''}` }}
              </span>
            </div>
            <img v-if="f.contentType==='image'&&f.base64&&!f.loading" :src="`data:${f.mediaType};base64,${f.base64}`" class="upl-thumb" alt=""/>
            <button class="upl-rm" @click="removeUplFile(f.id)" title="移除">×</button>
          </div>
        </div>
        <!-- Input area -->
        <div class="chat-in">
          <input ref="fileInputRef" type="file" multiple
            accept=".pdf,.docx,.doc,.md,.markdown,.txt,.rst,.csv,.png,.jpg,.jpeg,.gif,.webp,.bmp"
            style="display:none" @change="onFileInput"/>
          <button class="btn-attach" title="上传文件 (PDF · Word · Markdown · 图片)" @click="fileInputRef?.click()">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
            </svg>
          </button>
          <textarea v-model="chatInput" class="chat-ta" rows="2"
            placeholder="提问代码问题，或上传 PDF/Word/Markdown/图片辅助解答… (Enter 发送)"
            :disabled="isAnswering" @keydown="handleKey"></textarea>
          <button class="btn-send"
            :disabled="(!chatInput.trim()&&!uploadedFiles.filter(f=>!f.loading&&!f.error).length)||isAnswering"
            @click="sendMessage">
            <span v-if="isAnswering" class="sp xs"></span>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
      </div>
    </div>

  </main>
</div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@500;600;700&family=DM+Sans:wght@300;400;500;600&family=Fira+Code:wght@300;400;500&display=swap');

:root{
  --bg0:#03080F;--bg1:#050D18;--bg2:#080E1E;--bg3:#0D1526;--bg4:#162035;
  --bd:rgba(0,255,212,.07);--bd2:rgba(0,255,212,.18);--bd3:rgba(129,140,248,.25);
  --p:#00FFD4;--p1:rgba(0,255,212,.12);--p2:rgba(0,255,212,.22);
  --v:#818CF8;--v1:rgba(129,140,248,.12);
  --pk:#F472B6;--pk1:rgba(244,114,182,.12);
  --am:#FBBF24;--ok:#34D399;--er:#F87171;
  --t0:#F0F8FF;--t1:#B0CCE8;--t2:#6B8CAE;--t3:#2D4A6A;
  --fd:'Rajdhani',sans-serif;--fu:'DM Sans',sans-serif;--fm:'Fira Code',monospace;
  --r:12px;--rs:8px;--tr:.17s cubic-bezier(.4,0,.2,1);--sw:246px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden}
body{background:var(--bg0);color:var(--t1);font-family:var(--fu);font-size:14px;-webkit-font-smoothing:antialiased}
::-webkit-scrollbar{width:4px;height:4px}::-webkit-scrollbar-track{background:transparent}::-webkit-scrollbar-thumb{background:var(--bg4);border-radius:2px}
button,input,select,textarea{font-family:var(--fu)}

/* ── GRADIENTS ── */
.grd{background:linear-gradient(135deg,var(--p),var(--v));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}

/* ── AUTH ── */
.auth-wrap{min-height:100vh;display:flex;align-items:center;justify-content:center;position:relative;overflow:hidden;background:var(--bg0)}
.auth-bg{position:absolute;inset:0;pointer-events:none}
.abg-grid{position:absolute;inset:0;background-image:linear-gradient(rgba(0,255,212,.035) 1px,transparent 1px),linear-gradient(90deg,rgba(0,255,212,.035) 1px,transparent 1px);background-size:48px 48px}
.abg-glow{position:absolute;border-radius:50%;filter:blur(80px)}
.g1{width:560px;height:560px;background:radial-gradient(circle,rgba(0,255,212,.18),transparent);top:-150px;left:-100px;animation:gp 9s ease-in-out infinite}
.g2{width:440px;height:440px;background:radial-gradient(circle,rgba(129,140,248,.16),transparent);bottom:-100px;right:-80px;animation:gp 12s ease-in-out infinite reverse}
.g3{width:300px;height:300px;background:radial-gradient(circle,rgba(244,114,182,.12),transparent);top:50%;left:55%;animation:gp 15s ease-in-out infinite}
@keyframes gp{0%,100%{transform:scale(1) rotate(0deg);opacity:.9}50%{transform:scale(1.25) rotate(6deg);opacity:1}}
.abg-particles{position:absolute;inset:0;overflow:hidden}
.particle{position:absolute;top:50%;left:50%;width:var(--sz);height:var(--sz);border-radius:50%;background:rgba(0,255,212,.4);transform-origin:0 calc(-140px - var(--sz));animation:orbit var(--sp) linear var(--dl) infinite;transform:rotate(var(--d)) translateY(-140px)}
@keyframes orbit{0%{transform:rotate(calc(var(--d)+0deg)) translateY(-140px);opacity:.8}50%{opacity:.2}100%{transform:rotate(calc(var(--d)+360deg)) translateY(-140px);opacity:.8}}
.auth-card{position:relative;z-index:1;background:rgba(8,14,30,.85);backdrop-filter:blur(20px);border:1px solid var(--bd2);border-radius:20px;padding:38px;width:416px;box-shadow:0 24px 80px rgba(0,0,0,.7),0 0 0 1px rgba(0,255,212,.04);animation:fa .5s ease}
@keyframes fa{from{opacity:0;transform:translateY(24px)}to{opacity:1;transform:translateY(0)}}
.ac-logo{display:flex;align-items:center;gap:10px;margin-bottom:6px}
.ac-name{font-family:var(--fd);font-size:22px;font-weight:700;background:linear-gradient(135deg,#00FFD4,#818CF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:.5px}
.ac-sub{color:var(--t2);font-size:12.5px;margin-bottom:22px}
.ac-tabs{display:flex;gap:3px;background:var(--bg2);border-radius:10px;padding:3px;margin-bottom:16px}
.act{flex:1;padding:8px;border:none;border-radius:8px;font-size:13.5px;font-weight:500;color:var(--t2);background:transparent;cursor:pointer;transition:var(--tr)}
.act.on{background:linear-gradient(135deg,rgba(0,255,212,.15),rgba(129,140,248,.1));color:var(--p);border:1px solid var(--bd2)}
.ac-alert{padding:10px 14px;border-radius:var(--rs);font-size:13px;margin-bottom:14px;border-left:3px solid}
.ac-alert.ae{background:rgba(248,113,113,.1);border-color:var(--er);color:#fca5a5}
.ac-alert.ao{background:rgba(52,211,153,.1);border-color:var(--ok);color:#6ee7b7}
.ale-enter-active,.ale-leave-active{transition:.25s ease}.ale-enter-from,.ale-leave-to{opacity:0;transform:translateY(-6px)}
.acf{display:flex;flex-direction:column;gap:14px}
.fld{display:flex;flex-direction:column;gap:5px}
.fld label{font-size:10.5px;font-weight:600;color:var(--t2);text-transform:uppercase;letter-spacing:.6px}
.fld input,.si{background:var(--bg3);border:1px solid var(--bd);border-radius:var(--rs);color:var(--t0);font-size:13.5px;padding:10px 12px;outline:none;transition:var(--tr);width:100%}
.fld input:focus,.si:focus{border-color:var(--p);box-shadow:0 0 0 3px var(--p1)}
.fld input::placeholder,.si::placeholder{color:var(--t3)}
.ferr{font-size:11.5px;color:var(--er)}
.pw{position:relative}.pw input{padding-right:38px}
.eye{position:absolute;right:10px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;color:var(--t3);font-size:14px;transition:var(--tr)}.eye:hover{color:var(--t1)}
.pwm{display:flex;align-items:center;gap:8px;margin-top:5px}
.pwb{flex:1;height:3px;background:var(--bg4);border-radius:2px;overflow:hidden}
.pwf{height:100%;border-radius:2px;transition:width .35s,background .35s}.pwl{font-size:10.5px;font-weight:600}
.btn-prime{background:linear-gradient(135deg,#00FFD4,#00B89C);border:none;border-radius:var(--rs);color:#001A14;font-size:14px;font-weight:700;padding:12px;cursor:pointer;transition:var(--tr);display:flex;align-items:center;justify-content:center;gap:8px}
.btn-prime:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 8px 24px rgba(0,255,212,.3)}.btn-prime:disabled{opacity:.45;cursor:not-allowed}
.btn-prime.sm{padding:7px 16px;font-size:13px}
.ac-link{text-align:right;font-size:12.5px}.ac-link a,.lnk{color:var(--p);text-decoration:none;background:none;border:none;cursor:pointer;font-size:12.5px;padding:0}
.bk-btn{background:none;border:none;color:var(--t2);cursor:pointer;font-size:12.5px;align-self:flex-start;padding:0;transition:var(--tr)}.bk-btn:hover{color:var(--t1)}
.ac-h{font-family:var(--fd);font-size:17px;font-weight:700;color:var(--t0)}
.dev-box{background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.25);border-radius:var(--rs);padding:12px;font-size:12px;display:flex;flex-direction:column;gap:7px}
.dev-b{background:var(--am);color:#000;font-size:10px;font-weight:700;padding:2px 7px;border-radius:4px;align-self:flex-start}
.dev-box code{font-family:var(--fm);font-size:10.5px;word-break:break-all;color:var(--am)}

/* ── APP SHELL ── */
.app{display:flex;height:100vh;overflow:hidden}
.sb{width:var(--sw);min-width:var(--sw);background:var(--bg1);border-right:1px solid var(--bd);display:flex;flex-direction:column;padding:13px 11px;gap:13px;overflow-y:auto}
.sb-logo{display:flex;align-items:center;gap:9px;padding:2px 0 10px;border-bottom:1px solid var(--bd);font-family:var(--fd);font-size:16px;font-weight:700;background:linear-gradient(135deg,#00FFD4,#818CF8);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sb-repo{display:flex;flex-direction:column;gap:6px}
.sbr-row{display:flex;gap:5px}.si.br{flex:1;font-size:12px;padding:8px 9px}
.btn-idx{background:linear-gradient(135deg,var(--p),#00B89C);border:none;border-radius:var(--rs);color:#001A14;padding:0 11px;cursor:pointer;transition:var(--tr);display:flex;align-items:center;justify-content:center;min-width:34px;height:36px;font-weight:700}
.btn-idx:disabled{opacity:.4;cursor:not-allowed}.btn-idx:hover:not(:disabled){box-shadow:0 0 12px rgba(0,255,212,.4)}
.rst{font-size:10.5px;color:var(--t2);line-height:1.55}
.sbnav{display:flex;flex-direction:column;gap:1px;flex:1;padding-top:4px}
.snav{display:flex;align-items:center;gap:8px;padding:9px 11px;border:none;border-radius:var(--rs);background:transparent;color:var(--t2);font-size:13px;font-weight:500;cursor:pointer;transition:var(--tr);text-align:left;width:100%;position:relative}
.snav:hover{background:var(--bg3);color:var(--t1)}
.snav.on{background:linear-gradient(135deg,rgba(0,255,212,.08),rgba(129,140,248,.05));color:var(--nc,var(--p));border:1px solid rgba(0,255,212,.12)}
.snav.on::before{content:'';position:absolute;left:-1px;top:20%;bottom:20%;width:3px;background:var(--nc,var(--p));border-radius:0 3px 3px 0;box-shadow:0 0 8px var(--nc,var(--p))}
.sni{font-size:15px;flex-shrink:0}.snl{flex:1}
.snbg{background:var(--p);color:#001A14;font-size:9.5px;font-weight:700;padding:1px 6px;border-radius:10px}
.sb-usr{display:flex;align-items:center;gap:8px;padding:10px;background:rgba(255,255,255,.02);border-radius:var(--r);border:1px solid var(--bd)}
.uav{width:28px;height:28px;border-radius:50%;background:linear-gradient(135deg,var(--p),var(--v));display:flex;align-items:center;justify-content:center;font-weight:800;font-size:12px;color:#001A14;flex-shrink:0}
.uif{display:flex;flex-direction:column;gap:1px;min-width:0;flex:1}
.unm{font-size:12.5px;font-weight:600;color:var(--t0);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.uem{font-size:10px;color:var(--t3);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.uout{background:none;border:none;color:var(--t3);cursor:pointer;padding:4px;transition:var(--tr);display:flex}.uout:hover{color:var(--er)}

/* ── PANEL ── */
.ma{flex:1;overflow:hidden;display:flex;flex-direction:column}
.panel{flex:1;display:flex;flex-direction:column;height:100%;overflow:hidden}
.ph{padding:12px 18px 10px;border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:10px;flex-shrink:0;flex-wrap:wrap;background:rgba(0,0,0,.2)}
.pt{font-family:var(--fd);font-size:18px;font-weight:700}
.pa{margin-left:auto;display:flex;gap:6px;align-items:center}
.btn-sm{background:var(--bg3);border:1px solid var(--bd);color:var(--t1);padding:5px 10px;border-radius:6px;font-size:11.5px;cursor:pointer;transition:var(--tr)}
.btn-sm:hover:not(:disabled){border-color:var(--p);color:var(--p)}.btn-sm:disabled{opacity:.4;cursor:not-allowed}
.repo-pill{background:var(--p1);color:var(--p);border-radius:100px;padding:3px 10px;font-size:11px;font-family:var(--fm);border:1px solid var(--p2)}
.empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;color:var(--t2);text-align:center;padding:40px}
.eic{font-size:44px;opacity:.3}
.si.sm{width:180px;font-size:12px;padding:6px 10px}
.sel-sm{background:var(--bg3);border:1px solid var(--bd);border-radius:var(--rs);color:var(--t1);padding:5px 8px;font-size:12px;outline:none;cursor:pointer}
.stat-badge{font-size:11px;color:var(--t3);font-family:var(--fm)}
.sub-tabs{display:flex;gap:2px;background:var(--bg2);border-radius:8px;padding:3px}
.stab{padding:5px 12px;border:none;border-radius:6px;font-size:12px;font-weight:500;color:var(--t2);background:transparent;cursor:pointer;transition:var(--tr)}
.stab.on{background:var(--p1);color:var(--p);border:1px solid var(--bd2)}
.vis-hint{padding:8px 18px;font-size:11.5px;color:var(--t3);text-align:center;flex-shrink:0}

/* ── FILE BROWSER ── */
.pv-lay{flex:1;display:flex;overflow:hidden}
.pv-tree{width:220px;min-width:220px;border-right:1px solid var(--bd);overflow-y:auto;flex-shrink:0}
.pv-hd{padding:7px 11px;font-size:10.5px;font-weight:600;color:var(--t3);border-bottom:1px solid var(--bd)}
.pvf{width:100%;text-align:left;background:none;border:none;display:flex;align-items:center;gap:5px;padding:5px 11px;cursor:pointer;color:var(--t2);font-size:11px;transition:var(--tr);white-space:nowrap;overflow:hidden}
.pvf:hover{background:var(--bg3);color:var(--t1)}.pvf.on{background:var(--p1);color:var(--p)}
.pvfn{flex:1;overflow:hidden;text-overflow:ellipsis;font-family:var(--fm);font-size:10px}
.pvfc{background:var(--bg4);color:var(--t3);font-size:9.5px;padding:1px 5px;border-radius:9px;flex-shrink:0}
.pv-view{flex:1;overflow:hidden;display:flex;flex-direction:column}
.pv-fhd{display:flex;align-items:center;gap:9px;padding:7px 14px;background:var(--bg2);border-bottom:1px solid var(--bd);flex-shrink:0;flex-wrap:wrap}
.pv-fi{font-size:15px}
.pv-fp{font-family:var(--fm);font-size:11.5px;color:var(--t0);flex:1;overflow:hidden;text-overflow:ellipsis}
.pv-fm{font-size:10.5px;color:var(--t3)}.pv-mc{background:rgba(251,191,36,.15);color:var(--am);border-radius:4px;padding:2px 7px;font-size:10.5px;font-weight:600}
.pv-code-w{flex:1;overflow:auto;background:var(--bg1)}.pv-code{padding:6px 0;font-family:var(--fm);font-size:11.5px;line-height:1.7;min-width:max-content}
.pvl{display:flex;min-height:20px}.pvl.hl{background:rgba(251,191,36,.07)}
.ln{width:40px;text-align:right;padding-right:14px;color:var(--t3);font-size:10.5px;flex-shrink:0;user-select:none;line-height:1.7}
.lc{color:var(--t1);white-space:pre;padding-right:20px}

/* ── CODE STRUCTURE ── */
.str-lay{flex:1;display:flex;overflow:hidden}
.str-tree{width:252px;min-width:252px;border-right:1px solid var(--bd);overflow-y:auto}
.str-hd{padding:7px 11px;font-size:10.5px;font-weight:600;color:var(--t3);border-bottom:1px solid var(--bd)}
.tr{display:flex;align-items:center}
.trb{width:100%;text-align:left;background:none;border:none;display:flex;align-items:center;gap:5px;padding:5px 4px;cursor:pointer;color:var(--t2);font-size:11.5px;transition:var(--tr);white-space:nowrap;overflow:hidden}
.trb:hover{background:var(--bg3);color:var(--t1)}
.tr-dir .trb{color:var(--t1);font-weight:600}
.tr.on .trb{background:var(--p1);color:var(--p)}
.tra{font-size:9px;color:var(--t3);width:11px;flex-shrink:0}.trn{flex:1;overflow:hidden;text-overflow:ellipsis}.trn.mono{font-family:var(--fm);font-size:10.5px}.trc{background:var(--bg4);color:var(--t3);font-size:9.5px;padding:1px 4px;border-radius:9px;flex-shrink:0}
.ckb{flex-shrink:0;border-radius:4px;padding:1px 5px;font-size:9px;font-weight:700;border:1px solid}.ckb.lg{padding:3px 10px;font-size:12px;border-radius:6px}.ckb.sm{font-size:9.5px;padding:1px 5px}
.async-tag{font-size:9px;padding:1px 3px;border-radius:3px;font-weight:700;background:rgba(0,255,212,.12);color:var(--p);flex-shrink:0}.async-tag.lg{font-size:10.5px;padding:2px 7px}
.exp-tag{font-size:9px;padding:1px 3px;border-radius:3px;font-weight:700;background:rgba(129,140,248,.12);color:var(--v);flex-shrink:0}.exp-tag.lg{font-size:10.5px;padding:2px 7px}
.str-det{flex:1;overflow-y:auto}
.sdi{padding:16px 18px;display:flex;flex-direction:column;gap:13px}
.sdi-head{display:flex;flex-direction:column;gap:5px}
.sdi-badges{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.sdi-title{font-family:var(--fd);font-size:20px;font-weight:700;color:var(--t0);background:linear-gradient(135deg,var(--t0),var(--t1));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.sdi-loc{font-family:var(--fm);font-size:10.5px;color:var(--t3)}
.cmplx-row{display:flex;align-items:center;gap:8px}
.cmplx-bar{flex:1;height:6px;background:var(--bg4);border-radius:3px;overflow:hidden}
.cmplx-fill{height:100%;border-radius:3px;transition:width .5s}
.cmplx-val{font-family:var(--fm);font-size:12px;font-weight:700;min-width:24px;text-align:right}
.mgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(175px,1fr));gap:7px}
.mc{background:var(--bg3);border:1px solid var(--bd);border-radius:var(--rs);padding:9px 11px}
.mk{font-size:10px;font-weight:600;color:var(--t3);text-transform:uppercase;letter-spacing:.5px;display:block;margin-bottom:3px}
.mv{font-family:var(--fm);font-size:11.5px;color:var(--t0);display:block;word-break:break-all}
.sdi-doc{background:var(--bg3);border:1px solid var(--bd);border-radius:var(--rs);padding:11px}.sdi-doc p{font-size:12.5px;color:var(--t1);line-height:1.65;margin-top:4px}
.call-analysis{display:flex;flex-direction:column;gap:8px}
.call-sec{display:flex;flex-direction:column;gap:5px}
.cref-list{display:flex;flex-wrap:wrap;gap:5px}
.cref{border:1px solid;border-radius:6px;padding:3px 9px;font-size:11px;cursor:pointer;background:none;transition:var(--tr);font-family:var(--fm)}.cref:hover{background:var(--bg3)}
.sdi-code{display:flex;flex-direction:column;gap:6px}
.sdi-code-hd{display:flex;align-items:center;gap:8px}
.code-meta{font-size:10.5px;color:var(--t3);font-family:var(--fm)}
.btn-explain{background:linear-gradient(135deg,rgba(0,255,212,.12),rgba(129,140,248,.08));border:1px solid var(--bd2);color:var(--p);padding:4px 11px;border-radius:6px;font-size:11.5px;cursor:pointer;transition:var(--tr);margin-left:auto}.btn-explain:hover{box-shadow:0 0 10px rgba(0,255,212,.2);transform:translateY(-1px)}
.code-scroller{background:var(--bg1);border:1px solid var(--bd);border-radius:var(--rs);overflow:auto;max-height:320px}
.sdi-rel{display:flex;flex-direction:column;gap:7px;padding-bottom:16px}
.rel-chips{display:flex;flex-wrap:wrap;gap:5px}
.rel-chip{border:1px solid;border-radius:5px;padding:3px 9px;font-size:10.5px;cursor:pointer;background:none;transition:var(--tr);font-family:var(--fm)}.rel-chip:hover{background:var(--bg3)}

/* ── GRAPH + METRICS ── */
.kg-cv{position:absolute;top:0;left:0;width:100%;height:calc(100% - 44px);cursor:grab}.kg-cv:active{cursor:grabbing}
.kg-tip{position:absolute;background:rgba(8,14,30,.9);backdrop-filter:blur(12px);border:1px solid var(--bd2);border-radius:var(--r);padding:10px 13px;pointer-events:none;z-index:10;max-width:230px;box-shadow:0 8px 28px rgba(0,0,0,.6)}
.ktt{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.ktn{font-family:var(--fm);font-size:13.5px;font-weight:600;color:var(--t0);margin-bottom:5px;word-break:break-all}
.ktf{font-family:var(--fm);font-size:9.5px;color:var(--t3);margin-bottom:4px;word-break:break-all}
.ktm{font-size:11px;color:var(--t2);margin-top:2px}.kta{font-size:10px;color:var(--p);font-weight:700;margin-top:4px}
.ktd{font-size:9.5px;color:var(--t3);margin-top:6px;border-top:1px solid var(--bd);padding-top:5px}
.kg-leg{position:absolute;bottom:0;left:0;right:0;height:44px;display:flex;align-items:center;gap:14px;padding:0 14px;background:linear-gradient(transparent,var(--bg1));font-size:11.5px;flex-wrap:wrap}
.kll{display:flex;align-items:center;gap:5px}.kld{width:8px;height:8px;border-radius:50%;flex-shrink:0}.klh{margin-left:auto;color:var(--t3);font-size:10.5px}
.metrics-wrap{flex:1;overflow-y:auto;padding:2px 0}
.metrics-inner{padding:16px 18px;display:flex;flex-direction:column;gap:14px}
.sc-row{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px}
.sc{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);padding:14px 12px;text-align:center;transition:var(--tr)}.sc:hover{border-color:var(--bd2);transform:translateY(-2px);box-shadow:0 8px 20px rgba(0,0,0,.3)}
.scv{font-family:var(--fd);font-size:26px;font-weight:700;line-height:1}.scl{font-size:10.5px;color:var(--t3);margin-top:4px;font-weight:600;text-transform:uppercase;letter-spacing:.4px}
.mcharts{display:flex;gap:12px;flex-wrap:wrap}
.mc-card{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);padding:14px;min-width:190px}.mc-card.flex1{flex:1}.mc-card.fullw{width:100%}
.mc-title{font-family:var(--fd);font-size:13.5px;font-weight:700;color:var(--t0);margin-bottom:12px}
.donut-wr{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.dleg{display:flex;flex-direction:column;gap:5px}.dle{display:flex;align-items:center;gap:6px;font-size:11.5px;cursor:pointer;border-radius:5px;padding:2px 4px;transition:var(--tr)}.dle.hl{background:var(--bg3)}.dld{width:8px;height:8px;border-radius:50%;flex-shrink:0}.dll{color:var(--t1);flex:1}.dlc{color:var(--t3);font-family:var(--fm);font-size:10.5px}
.bar-list{display:flex;flex-direction:column;gap:7px}
.bar-row{display:flex;align-items:center;gap:9px;border-radius:5px;padding:2px 4px;transition:background .2s}.bar-row:hover{background:var(--bg3)}
.blbl{width:110px;font-size:11px;color:var(--t1);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex-shrink:0;font-family:var(--fm)}
.btr{flex:1;height:16px;background:var(--bg3);border-radius:4px;overflow:hidden}
.bfill{height:100%;border-radius:4px;transition:width .6s cubic-bezier(.4,0,.2,1)}
.bval{width:24px;text-align:right;font-size:10.5px;color:var(--t3);font-family:var(--fm);flex-shrink:0}
.tbars{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.tbar-row{display:flex;align-items:center;gap:7px}

/* ── VISUAL ── */
.tm-wrap{flex:1;overflow:hidden;display:flex;flex-direction:column;padding:0 14px 10px}
.tm-svg-w{flex:1;overflow:hidden;border:1px solid var(--bd);border-radius:var(--r);background:var(--bg1)}
.tm-svg{width:100%;height:100%}
.tm-tooltip{position:absolute;bottom:60px;left:50%;transform:translateX(-50%);background:rgba(8,14,30,.9);border:1px solid var(--bd2);border-radius:8px;padding:6px 14px;font-size:11.5px;color:var(--t1);pointer-events:none;white-space:nowrap;font-family:var(--fm)}
.cg-wrap{flex:1;position:relative;overflow:hidden;display:flex;flex-direction:column}

/* ── CHAT ── */
.chat-panel{display:flex;flex-direction:column}
.chat-body{flex:1;overflow-y:auto;padding:12px 16px;display:flex;flex-direction:column;gap:12px}
.chat-wel{padding:30px 0;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center}
.wt{font-family:var(--fd);font-size:20px;font-weight:700;background:linear-gradient(135deg,var(--t0),var(--p));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.ws{color:var(--t2);font-size:13.5px}
.chips{display:flex;flex-wrap:wrap;gap:7px;justify-content:center;margin-top:7px}
.chip{background:var(--bg3);border:1px solid var(--bd);color:var(--t1);padding:7px 14px;border-radius:100px;font-size:12.5px;cursor:pointer;transition:var(--tr)}.chip:hover{border-color:var(--p);color:var(--p);background:var(--p1)}
.msg{display:flex;gap:8px;animation:fa .22s ease}.msg.user{flex-direction:row-reverse}
.mav{width:28px;height:28px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:12.5px;font-weight:700}
.msg.user .mav{background:linear-gradient(135deg,var(--p),var(--v));color:#001A14}
.msg.assistant .mav{background:var(--bg4);border:1px solid var(--bd);font-size:15px}
.mbody{max-width:calc(100% - 70px);display:flex;flex-direction:column;gap:5px}.msg.user .mbody{align-items:flex-end}
.mbub{border-radius:var(--r);padding:10px 13px}
.user-b{background:var(--p1);border:1px solid var(--p2);color:var(--t0);font-size:13.5px;line-height:1.6;white-space:pre-wrap;word-break:break-word}
.ai-b{background:var(--bg2);border:1px solid var(--bd);color:var(--t1);max-width:820px;position:relative}
.tcur{animation:blink .8s step-end infinite;color:var(--p)}@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
/* Markdown */
.mdc-wrap{font-size:13.5px;line-height:1.72;color:var(--t1)}
.mdc-wrap .mp{margin:.45em 0}
.mdc-wrap .mh{font-family:var(--fd);color:var(--t0);margin:.8em 0 .35em}
.mdc-wrap h1.mh{font-size:18px}.mdc-wrap h2.mh{font-size:15.5px}.mdc-wrap h3.mh{font-size:14px;color:var(--p)}
.mdc-wrap ul,.mdc-wrap ol{padding-left:1.4em;margin:.4em 0}.mdc-wrap li{margin:.2em 0}
.mdc-wrap .mhr{border:none;border-top:1px solid var(--bd);margin:.8em 0}
.mdc-wrap .mbq{border-left:3px solid var(--v);padding:.4em .8em;background:var(--v1);border-radius:0 6px 6px 0;margin:.4em 0;color:var(--t2)}
.mdc-wrap .mic{background:var(--bg3);color:var(--p);border-radius:4px;padding:1px 5px;font-family:var(--fm);font-size:11.5px}
.mdc-wrap .mdc{background:var(--bg1);border:1px solid var(--bd);border-radius:var(--rs);margin:.6em 0;overflow:hidden}
.mdc-wrap .mdc-lang{padding:4px 10px;font-size:9.5px;font-weight:700;color:var(--t3);text-transform:uppercase;border-bottom:1px solid var(--bd);background:var(--bg2)}
.mdc-wrap .mdc pre{padding:11px;overflow-x:auto;margin:0}.mdc-wrap .mdc code{font-family:var(--fm);font-size:12px;color:var(--t1);line-height:1.65}
.mdc-wrap .mmath{text-align:center;padding:10px;overflow-x:auto;background:var(--v1);border-radius:6px;margin:.5em 0}
.mdc-wrap .mmf{font-family:var(--fm);font-size:11.5px;color:var(--v);background:var(--v1);padding:2px 6px;border-radius:4px}
.mdc-wrap .mcite{cursor:pointer;color:var(--p);font-size:10px;font-weight:700;padding:0 2px;transition:var(--tr);text-decoration:underline;text-underline-offset:2px}.mdc-wrap .mcite:hover{color:var(--t0)}
.mdc-wrap strong{color:var(--t0)}.mdc-wrap em{color:var(--v)}
/* Source panel */
.src-panel{margin-top:10px;padding-top:10px;border-top:1px solid var(--bd);display:flex;flex-direction:column;gap:8px}
.src-hd{font-size:11px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:6px}
.src-cnt{background:var(--bg3);border-radius:10px;padding:1px 7px;font-size:10px;color:var(--t2)}
.src-grid{display:flex;flex-direction:column;gap:5px}
.src-card{display:flex;align-items:center;gap:9px;background:var(--bg3);border:1px solid var(--bd);border-radius:8px;padding:8px 11px;cursor:pointer;transition:var(--tr);text-align:left;width:100%}
.src-card:hover{border-color:var(--p);background:var(--p1);transform:translateX(3px)}
.src-num{font-family:var(--fm);font-size:11px;font-weight:700;color:var(--p);min-width:24px;flex-shrink:0}
.src-num.sm{font-size:10px;min-width:20px}
.src-info{display:flex;flex-direction:column;gap:1px;flex:1;min-width:0;overflow:hidden}
.src-path{font-family:var(--fm);font-size:12px;font-weight:600;color:var(--t0);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.src-full{font-size:10px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-family:var(--fm)}
.src-lines{font-size:10px;color:var(--v)}
.src-go{font-size:12px;color:var(--t3);transition:var(--tr);flex-shrink:0}.src-card:hover .src-go{color:var(--p);transform:translateX(3px)}
.flow-det{margin-top:2px}
.flow-sum{padding:7px 11px;font-size:11.5px;color:var(--t2);cursor:pointer;list-style:none;user-select:none;border-radius:var(--rs);transition:var(--tr)}.flow-sum:hover{color:var(--t1);background:var(--bg3)}.flow-sum::-webkit-details-marker{display:none}
.flow-body{padding:10px 11px;display:flex;flex-direction:column;gap:7px;align-items:flex-start;border-top:1px solid var(--bd)}
.fn{background:var(--bg3);border:1px solid var(--bd);border-radius:7px;padding:7px 12px;font-size:12px;color:var(--t1);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;align-self:stretch}
.fn-q{border-color:rgba(251,191,36,.35)}.fn-ans{border-color:rgba(52,211,153,.3)}
.fn-srcs{display:flex;flex-direction:column;gap:4px;width:100%}
.fn-src{display:flex;align-items:center;gap:8px;padding:5px 8px;border-radius:6px;transition:var(--tr)}.fn-src:hover{background:var(--bg4)}
.fn-path{font-family:var(--fm);font-size:11px;color:var(--t2);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.fn-ln{font-size:10px;color:var(--v);flex-shrink:0}
.fn-jmp{font-size:11px;color:var(--t3);transition:var(--tr)}.fn-src:hover .fn-jmp{color:var(--p)}
.farr{font-size:11px;color:var(--t3);padding-left:10px}
.chat-in{padding:9px 16px 13px;border-top:1px solid var(--bd);display:flex;gap:8px;align-items:flex-end;flex-shrink:0;background:rgba(0,0,0,.15)}
.chat-ta{flex:1;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--r);color:var(--t0);font-size:13.5px;padding:9px 12px;outline:none;resize:none;transition:var(--tr);max-height:120px;overflow-y:auto}
.chat-ta:focus{border-color:var(--p);box-shadow:0 0 0 3px var(--p1)}.chat-ta::placeholder{color:var(--t3)}.chat-ta:disabled{opacity:.4}
.btn-send{background:linear-gradient(135deg,var(--p),#00B89C);border:none;border-radius:var(--rs);color:#001A14;padding:10px 14px;cursor:pointer;transition:var(--tr);display:flex;align-items:center;align-self:flex-end}
.btn-send:disabled{opacity:.4;cursor:not-allowed}.btn-send:hover:not(:disabled){box-shadow:0 0 14px rgba(0,255,212,.35);transform:translateY(-1px)}

/* ── FILE UPLOAD ── */
.chat-bottom{display:flex;flex-direction:column;flex-shrink:0;border-top:1px solid var(--bd);background:rgba(0,0,0,.15)}
.att-count{font-size:11px;color:var(--p);font-family:var(--fm);background:var(--p1);border-radius:10px;padding:2px 9px}
.drop-mask{position:absolute;inset:0;background:rgba(3,8,15,.82);backdrop-filter:blur(4px);z-index:20;display:flex;align-items:center;justify-content:center;border-radius:0;pointer-events:none}
.drop-box{display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;color:var(--p);border:2px dashed var(--p);border-radius:16px;padding:32px 48px;animation:gp 1.5s ease-in-out infinite}
.drop-sub{font-size:12px;color:var(--t2)}
.upl-hint{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--t3);background:var(--bg3);border:1px solid var(--bd);border-radius:8px;padding:7px 14px;margin-top:4px}
/* Pending file chips above input */
.upl-preview{display:flex;flex-wrap:wrap;gap:6px;padding:10px 14px 0;max-height:140px;overflow-y:auto}
.upl-chip{display:flex;align-items:center;gap:7px;background:var(--bg3);border:1px solid var(--bd);border-radius:9px;padding:7px 10px;max-width:260px;position:relative;transition:var(--tr)}
.upl-chip.upl-loading{opacity:.7;border-color:var(--t3)}
.upl-chip.upl-err{border-color:rgba(248,113,113,.4);background:rgba(248,113,113,.05)}
.upl-ic{font-size:17px;flex-shrink:0}
.upl-meta{display:flex;flex-direction:column;gap:2px;min-width:0;flex:1}
.upl-nm{font-size:12px;font-weight:600;color:var(--t0);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--fm)}
.upl-st{font-size:10.5px;color:var(--t3)}
.upl-ok{color:var(--ok)!important}
.upl-er{color:var(--er)!important}
.upl-thumb{width:40px;height:40px;object-fit:cover;border-radius:5px;flex-shrink:0;border:1px solid var(--bd)}
.upl-rm{background:none;border:none;color:var(--t3);cursor:pointer;font-size:14px;font-weight:700;padding:2px 4px;margin-left:2px;border-radius:4px;transition:var(--tr);flex-shrink:0}.upl-rm:hover{color:var(--er);background:rgba(248,113,113,.12)}
/* Input row */
.chat-in{padding:9px 14px 13px;display:flex;gap:8px;align-items:flex-end}
.btn-attach{background:var(--bg3);border:1px solid var(--bd);border-radius:var(--rs);color:var(--t2);padding:9px 10px;cursor:pointer;transition:var(--tr);display:flex;align-items:center;align-self:flex-end;flex-shrink:0}
.btn-attach:hover{border-color:var(--p);color:var(--p);background:var(--p1);box-shadow:0 0 10px var(--p1)}
/* Message attachment display */
.att-row{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:6px;max-width:600px}
.att-chip{display:flex;align-items:center;gap:7px;background:var(--bg3);border:1px solid var(--bd);border-radius:9px;padding:7px 11px;max-width:260px}
.att-chip.att-err{border-color:rgba(248,113,113,.35)}
.att-ic{font-size:18px;flex-shrink:0}
.att-info{display:flex;flex-direction:column;gap:1px;min-width:0;flex:1}
.att-nm{font-size:12px;font-weight:600;color:var(--t0);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--fm)}
.att-sz{font-size:10.5px;color:var(--ok)}
.att-er{font-size:10.5px;color:var(--er)}
.att-thumb{width:48px;height:48px;object-fit:cover;border-radius:6px;border:1px solid var(--bd);flex-shrink:0}

.sp{display:inline-block;border:2px solid currentColor;border-top-color:transparent;border-radius:50%;animation:spin .7s linear infinite;width:15px;height:15px}
.sp.xs{width:11px;height:11px;border-width:1.5px}.sp.lg{width:32px;height:32px;border-width:3px;color:var(--p)}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── RESPONSIVE ── */
@media(max-width:768px){
  :root{--sw:50px}
  .sb-logo span,.sb-repo,.uif,.snl,.rst{display:none}
  .snav{justify-content:center;padding:10px 0}
  .sb-usr{justify-content:center;padding:8px}
  .str-lay,.pv-lay{flex-direction:column}
  .str-tree,.pv-tree{width:100%;min-width:0;max-height:150px;border-right:none;border-bottom:1px solid var(--bd)}
  .auth-card{width:calc(100vw - 24px);padding:24px 16px}
}
</style>

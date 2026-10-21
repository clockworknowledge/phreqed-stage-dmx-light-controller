'use strict';
const $ = id => document.getElementById(id);
let token = '', catalog = null, state = null, draft = null, editingId = null, connected = false;
let queue = Promise.resolve();
let editingCue = null;
const copy = value => JSON.parse(JSON.stringify(value));
function node(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
function notify(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
async function request(path, options) { const response = await fetch(path, {cache:'no-store', ...options}); const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Controller request failed'); return result; }
function command(action, data = {}, refresh = false) {
  const work = queue.catch(() => {}).then(async () => {
    if (!token) throw new Error('Controller is disconnected. Wait for reconnection.');
    await request('/api/command', {method:'POST', headers:{'Content-Type':'application/json','X-Control-Token':token}, body:JSON.stringify({action,...data})});
    if (refresh) await loadCatalog();
  });
  queue = work;
  return work.catch(error => { notify(error.message, true); throw error; });
}
function act(action, data = {}, refresh = false) { command(action, data, refresh).catch(() => {}); }
function button(text, handler, className) { const e = node('button', text, className); e.type = 'button'; e.addEventListener('click', handler); return e; }
function option(select, value, text) { const o = node('option', text); o.value = value; select.append(o); }
function tab(name) { for (const e of document.querySelectorAll('.panel')) e.hidden = e.id !== name; for (const e of document.querySelectorAll('.tab')) { const active = e.dataset.tab === name; e.classList.toggle('active', active); e.setAttribute('aria-selected', String(active)); } }
for (const e of document.querySelectorAll('.tab')) e.addEventListener('click', () => tab(e.dataset.tab));
function fillPresets(select, selected) { select.replaceChildren(); for (const p of catalog.presets.filter(p => p.builtin || catalog.library.presets.some(u => u.preset_id === p.preset_id))) option(select, p.preset_id, p.name); if (selected) select.value = selected; }
async function loadCatalog() { catalog = await request('/api/catalog'); renderCatalog(); }
function renderCatalog() {
  fillPresets($('quick-preset'), state?.preset_id); fillPresets($('cue-preset'), $('cue-preset').value);
  $('preset-grid').replaceChildren();
  for (const p of catalog.presets.filter(p => p.builtin || catalog.library.presets.some(u => u.preset_id === p.preset_id))) {
    const card = node('article', undefined, 'preset'); card.dataset.preset = p.preset_id;
    card.append(node('div', undefined, 'swatch'));
    const body = node('div', undefined, 'preset-body'); body.append(node('span', p.builtin ? 'BUILT-IN LOOK' : 'YOUR LOOK', 'tag'), node('h3', p.name), node('p', p.description || `${p.layers.length} layer look`, 'hint'));
    const row = node('div', undefined, 'row'); row.append(button('Use look', () => act('preset',{value:p.preset_id})), button(p.builtin ? 'Make a copy' : 'Edit', () => openEditor(p)));
    if (!p.builtin) row.append(button('Delete', () => { if (confirm(`Delete “${p.name}”? Remove it from the scene list first if used there.`)) act('delete_preset',{value:p.preset_id},true); }));
    body.append(row); card.append(body); $('preset-grid').append(card);
  }
  renderCues();
}
function draw(canvas, rows, whiteLevel = 0) {
  const ctx = canvas.getContext('2d'); ctx.fillStyle = '#0c100d'; ctx.fillRect(0,0,canvas.width,canvas.height);
  const height = rows.length, width = rows[0]?.length || 0;
  if (!width || rows.some(row => row.length !== width)) return;
  const centerGap = height === 4 ? canvas.height*0.16 : 0;
  const cell = Math.min(canvas.width/width,(canvas.height-centerGap)/height), pad = Math.max(1,cell*0.12);
  const left = (canvas.width-width*cell)/2, top = (canvas.height-(height*cell+centerGap))/2;
  rows.forEach((row,y) => row.forEach((rgb,x) => {
    const rowTop = top+y*cell+(centerGap && y>=height/2 ? centerGap : 0);
    ctx.fillStyle = `rgb(${rgb.join(',')})`;
    ctx.fillRect(left+x*cell+pad,rowTop+pad,cell-pad*2,cell-pad*2);
  }));
  if (centerGap) {
    const lineHeight = Math.max(3,centerGap*0.22), lineGap = centerGap*0.12;
    const lineTop = top+(height/2)*cell+(centerGap-(lineHeight*2+lineGap))/2;
    const white = Math.round(89 + (255-89)*Math.max(0,Math.min(1,whiteLevel)));
    ctx.fillStyle = `rgb(${white},${white},${white})`;
    ctx.fillRect(left+pad,lineTop,width*cell-pad*2,lineHeight);
    ctx.fillRect(left+pad,lineTop+lineHeight+lineGap,width*cell-pad*2,lineHeight);
  }
}
function renderState(s) {
  state = s; connected = true;
  $('connection').textContent = s.live ? '● Live output' : s.live_allowed ? '● Live ready · stopped' : '● Simulation';
  $('connection').className = `badge ${s.live ? 'live' : 'connected'}`;
  $('output-label').textContent = s.blackout ? 'Blackout active' : s.live ? 'Live · 25 FPS' : 'Preview · no output';
  $('current-look').textContent = s.active_name || 'Custom look';
  $('master').max = s.brightness_ceiling;
  $('brightness-ceiling').textContent = `${Math.round(s.brightness_ceiling*100)}%`;
  $('live-warning').textContent = s.brightness_ceiling > 0.65
    ? `HIGH-OUTPUT MODE: the RGB ceiling is ${Math.round(s.brightness_ceiling*100)}%. Confirm the fixtures are safely positioned, people nearby are warned, and QLC+ blackout is available. Output still starts at 25% brightness or lower.`
    : 'Confirm the fixtures are safely positioned, people nearby are warned, and QLC+ blackout is available. Output starts at 25% brightness or lower.';
  if (document.activeElement !== $('master')) { $('master').value = s.brightness; $('master-value').textContent = `${Math.round(s.brightness*100)}%`; }
  if (document.activeElement !== $('quick-preset')) $('quick-preset').value = s.preset_id;
  $('bpm').textContent = Math.round(s.tempo);
  $('blackout-status').textContent = s.blackout ? 'Blackout is active.' : s.live ? 'Fixture output is live.' : 'Simulation. Fixtures are off.';
  $('release-blackout').hidden = !s.blackout; $('blackout').classList.toggle('latched',s.blackout);
  $('start-live').disabled = !s.live_allowed || s.live || Boolean(s.error); $('stop-live').disabled = !s.live;
  $('live-help').textContent = s.live ? 'Live output active. Keep this page connected; loss of all browser heartbeats stops output after 5 seconds.' : s.live_allowed ? 'Live is available. Output stays off until you choose Start live.' : 'Simulation only. Start the Pi controller with live --web to make live output available.';
  const cues = catalog?.library.scenes || [], cue = cues[s.scene_index];
  $('current-scene').textContent = cue ? `${s.scene_index+1}. ${cue.name}` : 'Manual control';
  $('sequence-status').textContent = s.playing ? 'Running timed scene list.' : cue ? 'Holding this scene.' : 'Select a scene or start the list.';
  $('play').disabled = !cues.length || s.playing || s.blackout; $('pause').disabled = !s.playing;
  $('next').disabled = $('prev').disabled = !cues.length;
  const audio = s.audio || {enabled:false,running:false,healthy:false,message:'Audio input disabled',loudness:0,onset:0,bass:0,mid:0,treble:0};
  $('audio-status').textContent = !audio.enabled ? 'Disabled' : audio.healthy ? 'Microphone active' : 'Input unavailable';
  $('audio-detail').textContent = audio.message;
  for (const key of ['loudness','onset','bass','mid','treble']) $(`audio-${key}`).value = audio[key] || 0;
  $('audio-motion').textContent = `${(audio.motion_multiplier ?? 1).toFixed(2)}x`;
  $('audio-brightness').textContent = `${Math.round((audio.brightness_multiplier ?? 1)*100)}%`;
  $('deep-dim').checked = Boolean(audio.deep_dim_enabled);
  if (document.activeElement !== $('quiet-floor')) $('quiet-floor').value = audio.quiet_floor ?? 0.03;
  $('quiet-floor-value').textContent = `${Math.round((audio.quiet_floor ?? 0.03)*100)}%`;
  $('quiet-floor').disabled = !audio.deep_dim_enabled;
  const white = s.white_preview || {enabled:false,threshold:0.65,level:0.8,active_level:0,commissioned:false,output_available:false,output_enabled:false,output_level:0.05,output_active_level:0,output_ceiling:0.10};
  $('white-output-level').max = white.output_ceiling;
  const highWhite = Boolean(white.high_output || white.output_ceiling > 0.10);
  $('white-output-warning').hidden = !highWhite;
  $('white-output-warning').textContent = highWhite
    ? `WARNING: high-output center whites are available up to ${Math.round(white.output_ceiling*100)}%. Use the lowest workable level; warn everyone nearby and keep blackout immediately available.`
    : '';
  $('white-output-hint').textContent = highWhite
    ? 'This process was explicitly armed above the normal 10% ceiling. Pulses remain onset-thresholded, at most 0.10 seconds and 4 Hz, and stop on blackout, output stop, failure, or lease loss.'
    : 'Physical whites require live output and this separate toggle. The default ceiling is 10%; pulses remain short, onset-thresholded, limited to no more than 4 Hz, and disabled by blackout, stop, or a lost browser lease.';
  if (highWhite) {
    $('live-warning').textContent += ` HIGH-OUTPUT CENTER WHITES are also available up to ${Math.round(white.output_ceiling*100)}% and require their separate in-page toggle.`;
  }
  $('white-preview').checked = Boolean(white.enabled);
  $('white-output').checked = Boolean(white.output_enabled);
  if (document.activeElement !== $('white-threshold')) $('white-threshold').value = white.threshold;
  if (document.activeElement !== $('white-level')) $('white-level').value = white.level;
  if (document.activeElement !== $('white-output-level')) $('white-output-level').value = white.output_level;
  $('white-threshold-value').textContent = `${Math.round(white.threshold*100)}%`;
  $('white-level-value').textContent = `${Math.round(white.level*100)}%`;
  $('white-output-level-value').textContent = `${Math.round(white.output_level*100)}%`;
  $('white-threshold').disabled = !(white.enabled || white.output_enabled);
  $('white-level').disabled = !white.enabled;
  $('white-output').disabled = !white.output_available;
  $('white-output-level').disabled = !white.output_available;
  $('white-preview-status').textContent = white.output_active_level > 0 ? 'LIVE WHITE PEAK' : white.output_enabled ? `Live whites armed · max ${Math.round(white.output_ceiling*100)}%` : white.commissioned ? 'Commissioned · output off' : 'Physical output locked';
  const foot = s.foot_control || {enabled:false,connected:false,message:'Foot control disabled',messages_received:0,reconnects:0};
  $('foot-status').textContent = foot.enabled ? `${foot.connected ? 'Pedal connected' : foot.message} · ${foot.messages_received} events · ${foot.reconnects} reconnects` : 'Foot control disabled';
  document.querySelectorAll('[data-cue]').forEach(e => e.classList.toggle('active', Number(e.dataset.cue) === s.scene_index));
  document.querySelectorAll('[data-preset]').forEach(e => e.classList.toggle('active', e.dataset.preset === s.preset_id));
  const displayWhite = Math.max(white.active_level, white.output_ceiling ? white.output_active_level/white.output_ceiling*0.8 : 0);
  const frames = Object.values(s.frames); if (frames[0]) draw($('cube-a'),frames[0],displayWhite); if (frames[1]) draw($('cube-b'),frames[1],displayWhite);
  if (s.error || s.notice) notify(s.error || s.notice, Boolean(s.error));
}
function newLayer() { return {effect_id:'plasma', fixtures:null, opacity:1, blend_mode:'alpha', parameters:{}}; }
function openEditor(p = null) {
  editingId = p && !p.builtin ? p.preset_id : null;
  draft = p ? copy(p) : {name:'',description:'',global_brightness:0.25,layers:[newLayer()]};
  $('look-name').value = p ? p.name + (p.builtin ? ' · My mix' : '') : '';
  $('look-description').value = draft.description; $('look-level').value = draft.global_brightness;
  $('editor').hidden = false; tab('looks'); renderLayers(); $('editor').scrollIntoView({behavior:'smooth',block:'start'});
}
function field(label, input) { const e = node('label',label); e.append(input); return e; }
function selectField(label, options, value, change) { const s = node('select'); for (const [key,text] of options) option(s,key,text); s.value = value; s.addEventListener('change', () => change(s.value)); return field(label,s); }
function numericField(label, value, min, max, step, change) { const input = node('input'); input.type='number'; input.value=value; input.min=min; input.max=max; input.step=step; input.required=true; input.addEventListener('change',() => change(Number(input.value))); return field(label,input); }
function renderLayers() {
  $('layers').replaceChildren();
  draft.layers.forEach((layer,index) => {
    const wrap = node('section',undefined,'layer'), heading = node('div',undefined,'section-title');
    heading.append(node('h3',`Layer ${index+1}`),button('Remove',() => { if(draft.layers.length>1){draft.layers.splice(index,1);renderLayers();} }));
    const fields = node('div',undefined,'form-grid');
    fields.append(selectField('Effect',catalog.effects.map(m=>[m.effect_id,m.name]),layer.effect_id,value=>{layer.effect_id=value;layer.parameters={};renderLayers();}),
      selectField('Fixture', [['both','Both cubes'],...Object.keys(state.frames).map(x=>[x,x])], layer.fixtures ? layer.fixtures[0] : 'both',value=>{layer.fixtures=value==='both'?null:[value];}),
      selectField('Blend',[['alpha','Alpha'],['additive','Additive'],['lighten','Lighten']],layer.blend_mode,value=>{layer.blend_mode=value;}),
      numericField('Opacity',layer.opacity,0,1,0.01,value=>{layer.opacity=value;}));
    const meta = catalog.effects.find(m=>m.effect_id===layer.effect_id);
    for(const spec of meta.parameters){ const value=layer.parameters[spec.key]??spec.default; const change=value=>{layer.parameters[spec.key]=value;}; fields.append(spec.choices.length ? selectField(spec.label,spec.choices.map(x=>[x,x]),value,change) : numericField(spec.label,value,spec.minimum,spec.maximum,spec.step||0.01,change)); }
    wrap.append(heading,fields); $('layers').append(wrap);
  });
  $('add-layer').disabled = draft.layers.length>=8;
}
function editorPreset() {
  const name=$('look-name').value.trim(); if(!name) throw new Error('Give this look a name.');
  for(const input of $('editor').querySelectorAll('input')) if(!input.reportValidity()) throw new Error('Check the highlighted look setting.');
  const slug=name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,64)||'custom';
  return {preset_id:editingId||`user-${slug}`,name,description:$('look-description').value,global_brightness:Number($('look-level').value),layers:copy(draft.layers)};
}
function saveScenes(scenes, done = () => {}) { command('save_scenes',{scenes},true).then(()=>{notify('Scene list saved on the Pi.');done();}).catch(()=>{}); }
function renderCues() {
  $('cue-list').replaceChildren(); const cues=catalog.library.scenes; $('empty-cues').hidden=Boolean(cues.length);
  cues.forEach((cue,index)=>{
    const card=node('article',undefined,'cue'); card.dataset.cue=index;
    const info=node('div'); info.append(node('h3',cue.name),node('p',`${catalog.presets.find(p=>p.preset_id===cue.preset_id)?.name || cue.preset_id} · ${cue.hold_seconds}s hold · ${cue.fade_seconds}s fade`,'hint'));
    const row=node('div',undefined,'row');
    row.append(button('Go',()=>act('select_scene',{index})),button('Edit',()=>{
      editingCue=index; $('cue-name').value=cue.name; $('cue-preset').value=cue.preset_id;
      $('cue-hold').value=cue.hold_seconds; $('cue-fade').value=cue.fade_seconds;
      $('cue-heading').textContent='Edit scene'; $('save-cue').textContent='Save scene';
      $('cancel-cue').hidden=false; $('add-cue').scrollIntoView({behavior:'smooth',block:'center'});
    }),button('↑',()=>{if(index>0){const next=copy(cues);[next[index-1],next[index]]=[next[index],next[index-1]];saveScenes(next);}}),button('↓',()=>{if(index<cues.length-1){const next=copy(cues);[next[index+1],next[index]]=[next[index],next[index+1]];saveScenes(next);}}),button('Remove',()=>{if(confirm(`Remove “${cue.name}” from the scene list?`))saveScenes(cues.filter((_,i)=>i!==index));}));
    row.children[2].disabled=index===0;row.children[3].disabled=index===cues.length-1;
    row.children[2].setAttribute('aria-label',`Move ${cue.name} up`);row.children[3].setAttribute('aria-label',`Move ${cue.name} down`);
    card.append(node('span',String(index+1).padStart(2,'0'),'cue-number'),info,row);$('cue-list').append(card);
  });
}
$('quick-preset').addEventListener('change',e=>act('preset',{value:e.target.value}));
$('master').addEventListener('input',e=>{$('master-value').textContent=`${Math.round(e.target.value*100)}%`;});
$('master').addEventListener('change',e=>act('brightness',{value:Number(e.target.value)}));
function updateAudioDimming(){act('audio_dimming',{enabled:$('deep-dim').checked,floor:Number($('quiet-floor').value)});}
$('deep-dim').addEventListener('change',updateAudioDimming);
$('quiet-floor').addEventListener('input',e=>{$('quiet-floor-value').textContent=`${Math.round(e.target.value*100)}%`;});
$('quiet-floor').addEventListener('change',updateAudioDimming);
function updateWhitePreview(){act('white_preview',{enabled:$('white-preview').checked,threshold:Number($('white-threshold').value),level:Number($('white-level').value)});}
$('white-preview').addEventListener('change',updateWhitePreview);
for(const id of ['white-threshold','white-level']){
  $(id).addEventListener('input',()=>{ $('white-threshold-value').textContent=`${Math.round($('white-threshold').value*100)}%`; $('white-level-value').textContent=`${Math.round($('white-level').value*100)}%`; });
  $(id).addEventListener('change',updateWhitePreview);
}
function updateWhiteOutput(){act('white_output',{enabled:$('white-output').checked,level:Number($('white-output-level').value)});}
$('white-output').addEventListener('change',updateWhiteOutput);
$('white-output-level').addEventListener('input',e=>{$('white-output-level-value').textContent=`${Math.round(e.target.value*100)}%`;});
$('white-output-level').addEventListener('change',updateWhiteOutput);
for(const [id,action] of Object.entries({prev:'previous_scene',next:'next_scene',play:'play',pause:'pause',tap:'tap','release-blackout':'resume','stop-live':'stop_live'})) $(id).addEventListener('click',()=>act(action));
// Blackout bypasses the edit queue so a pending save cannot delay it.
$('blackout').addEventListener('click',()=>{if(!token)return;request('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify({action:'blackout'})}).catch(error=>notify(`Blackout not confirmed: ${error.message}`,true));});
$('start-live').addEventListener('click',()=>$('live-dialog').showModal());
$('cancel-live').addEventListener('click',()=>$('live-dialog').close());
$('confirm-live').addEventListener('click',()=>{$('live-dialog').close();act('start_live');});
$('new-look').addEventListener('click',()=>openEditor());
$('close-editor').addEventListener('click',()=>{$('editor').hidden=true;});
$('add-layer').addEventListener('click',()=>{if(draft.layers.length<8){draft.layers.push(newLayer());renderLayers();}});
$('preview-look').addEventListener('click',()=>{try{act('preview',{preset:editorPreset()});}catch(e){notify(e.message,true);}});
$('save-look').addEventListener('click',()=>{try{const preset=editorPreset();if(!editingId&&catalog.library.presets.some(p=>p.preset_id===preset.preset_id)&&!confirm('A user look with this name already exists. Replace it?'))return;command('save_preset',{preset},true).then(()=>{editingId=preset.preset_id;notify('Look saved on the Pi.');}).catch(()=>{});}catch(e){notify(e.message,true);}});
function clearCueEdit(){editingCue=null;$('cue-heading').textContent='Add a scene';$('save-cue').textContent='+ Add scene';$('cancel-cue').hidden=true;$('cue-name').value='';}
$('cancel-cue').addEventListener('click',clearCueEdit);
$('add-cue').addEventListener('submit',e=>{e.preventDefault();const cue={name:$('cue-name').value,preset_id:$('cue-preset').value,hold_seconds:Number($('cue-hold').value),fade_seconds:Number($('cue-fade').value)};const scenes=copy(catalog.library.scenes);if(editingCue===null)scenes.push(cue);else scenes[editingCue]=cue;saveScenes(scenes,clearCueEdit);});
let lastBeat=0;
async function poll() {
  try {
    if(!token){token=(await request('/api/session')).token;await loadCatalog();}
    const s=await request('/api/state');renderState(s);
    if(Date.now()-lastBeat>1000){await request('/api/command',{method:'POST',headers:{'Content-Type':'application/json','X-Control-Token':token},body:JSON.stringify({action:'heartbeat'})});lastBeat=Date.now();}
    if(catalog&&Date.now()-(poll.lastCatalog||0)>4000){await loadCatalog();poll.lastCatalog=Date.now();}
  }catch(error){connected=false;token='';$('connection').textContent='Disconnected';$('connection').className='badge live';$('start-live').disabled=true;$('blackout-status').textContent='Controller connection lost.';$('safety-detail').textContent='Live output stops after 5 seconds without browser heartbeats.';notify('Connection lost. Reconnecting… Live output will not restart automatically.',true);}
  setTimeout(poll,250);
}
poll();

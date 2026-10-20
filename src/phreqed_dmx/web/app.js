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
function draw(canvas, rows) {
  const ctx = canvas.getContext('2d'); ctx.fillStyle = '#0c100d'; ctx.fillRect(0,0,canvas.width,canvas.height);
  const height = rows.length, width = rows[0]?.length || 0;
  if (!width || rows.some(row => row.length !== width)) return;
  const cell = Math.min(canvas.width/width,canvas.height/height), pad = Math.max(1,cell*0.12);
  const left = (canvas.width-width*cell)/2, top = (canvas.height-height*cell)/2;
  rows.forEach((row,y) => row.forEach((rgb,x) => { ctx.fillStyle = `rgb(${rgb.join(',')})`; ctx.fillRect(left+x*cell+pad,top+y*cell+pad,cell-pad*2,cell-pad*2); }));
}
function renderState(s) {
  state = s; connected = true;
  $('connection').textContent = s.live ? '● Live output' : s.live_allowed ? '● Live ready · stopped' : '● Simulation';
  $('connection').className = `badge ${s.live ? 'live' : 'connected'}`;
  $('output-label').textContent = s.blackout ? 'Blackout active' : s.live ? 'Live · 25 FPS' : 'Preview · no output';
  $('current-look').textContent = s.active_name || 'Custom look';
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
  document.querySelectorAll('[data-cue]').forEach(e => e.classList.toggle('active', Number(e.dataset.cue) === s.scene_index));
  document.querySelectorAll('[data-preset]').forEach(e => e.classList.toggle('active', e.dataset.preset === s.preset_id));
  const frames = Object.values(s.frames); if (frames[0]) draw($('cube-a'),frames[0]); if (frames[1]) draw($('cube-b'),frames[1]);
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

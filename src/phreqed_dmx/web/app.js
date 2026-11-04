'use strict';
const $ = id => document.getElementById(id);
let token = '', catalog = null, state = null, draft = null, editingId = null, connected = false;
let queue = Promise.resolve();
let editingCue = null;
let editingSongId = null, editingSongCueIndex = null, selectedSongId = null, selectedSetlistId = null;
const copy = value => JSON.parse(JSON.stringify(value));
const MONITOR_BRIGHTNESS_KEY = 'phreqed-monitor-brightness';
function savedMonitorBrightness() {
  try { const value=Number(localStorage.getItem(MONITOR_BRIGHTNESS_KEY)); return value>=1&&value<=5 ? value : 2; }
  catch (_) { return 2; }
}
let monitorBrightness = savedMonitorBrightness();
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
  const performanceSetlist=$('performance-setlist'),selectedPerformanceSetlist=state?.performance?.setlist_id||performanceSetlist.value;
  performanceSetlist.replaceChildren();for(const setlist of catalog.song_library.setlists)option(performanceSetlist,setlist.setlist_id,setlist.name);
  if(selectedPerformanceSetlist)performanceSetlist.value=selectedPerformanceSetlist;
  performanceSetlist.disabled=!catalog.song_library.setlists.length;
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
  fillPresets($('song-cue-preset'), $('song-cue-preset').value);
  renderSongs();
  renderSetlists();
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
    const previewRgb = rgb.map(channel => Math.min(255,Math.round(channel*monitorBrightness)));
    ctx.fillStyle = `rgb(${previewRgb.join(',')})`;
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
function clockTime(seconds){const total=Math.max(0,Math.floor(seconds||0)),minutes=Math.floor(total/60);return `${minutes}:${String(total%60).padStart(2,'0')}`;}
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
  if (document.activeElement !== $('contrast')) $('contrast').value = s.contrast ?? 1;
  $('contrast-value').textContent = `${(s.contrast ?? 1).toFixed(2)}x`;
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
  const performance=s.performance||{mode:'manual',state:'inactive',song_count:0,song_index:null,duration_seconds:0,elapsed_seconds:0,remaining_seconds:0,playable:false,running:false};
  if(document.activeElement!==$('performance-mode'))$('performance-mode').value=performance.mode;
  const setlistMode=performance.mode==='setlist';$('setlist-performance').hidden=!setlistMode;$('manual-transport').hidden=setlistMode;$('quick-preset').disabled=setlistMode;
  $('performance-heading').textContent=setlistMode?'Setlist performance':'Manual scene control';
  if(performance.setlist_id&&document.activeElement!==$('performance-setlist'))$('performance-setlist').value=performance.setlist_id;
  $('performance-song-number').textContent=performance.song_index===null?'NO SONG SELECTED':`${String(performance.song_index+1).padStart(2,'0')} / ${String(performance.song_count).padStart(2,'0')}`;
  $('performance-song-title').textContent=performance.song_title||'Choose a setlist';
  const performanceMessage=!performance.song_title?'Selection and mode changes never start playback.':!performance.playable?'No published cue sheet. Publish one in Song Builder before starting.':performance.running?'Running prepared cue timeline.':performance.state==='complete'?'Setlist complete. Start restarts the selected final song.':performance.state==='armed'?'Armed and waiting for explicit start.':'Stopped. Start begins again from the first cue.';
  $('performance-song-detail').textContent=performanceMessage;
  $('performance-song-progress').max=Math.max(1,performance.duration_seconds);$('performance-song-progress').value=performance.elapsed_seconds;
  $('performance-elapsed').textContent=clockTime(performance.elapsed_seconds);$('performance-remaining').textContent=`-${clockTime(performance.remaining_seconds)}`;
  $('performance-next').textContent=`Next: ${performance.next_song_title||'—'}`;
  $('toggle-song').textContent=performance.running?'Stop song':'Start song';
  $('toggle-song').disabled=!performance.song_title||(!performance.running&&(!performance.playable||s.blackout));
  $('previous-song').disabled=$('next-song').disabled=!performance.song_count;
  const audio = s.audio || {enabled:false,running:false,healthy:false,message:'Audio input disabled',loudness:0,onset:0,bass:0,mid:0,treble:0,auto_level_available:false,auto_level_enabled:false,gain_multiplier:1};
  $('audio-status').textContent = !audio.enabled ? 'Disabled' : audio.healthy ? 'Microphone active' : 'Input unavailable';
  $('audio-detail').textContent = audio.message;
  for (const key of ['loudness','onset','bass','mid','treble']) $(`audio-${key}`).value = audio[key] || 0;
  $('audio-motion').textContent = `${(audio.motion_multiplier ?? 1).toFixed(2)}x`;
  $('audio-brightness').textContent = `${Math.round((audio.brightness_multiplier ?? 1)*100)}%`;
  $('audio-auto-level').checked = Boolean(audio.auto_level_enabled);
  $('audio-auto-level').disabled = !audio.auto_level_available;
  $('audio-gain').textContent = audio.auto_level_available
    ? `Input gain ${(audio.gain_multiplier ?? 1).toFixed(2)}x · adapts slowly to sustained venue level`
    : 'Auto-level requires an explicitly configured microphone input.';
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
  $('foot-status').textContent = foot.enabled ? `${foot.connected ? 'Pedal connected' : foot.message} · ${foot.messages_received} events · ${foot.reconnects} reconnects · ${setlistMode?'song transport':'scene transport'}` : 'Foot control disabled';
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
function slug(prefix,name){const value=name.toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,58)||'untitled';return `${prefix}-${value}`;}
function songDocument(){return copy(catalog.song_library);}
function saveSongDocument(document,message,done=()=>{}){command('save_song_library',{song_library:document},true).then(()=>{notify(message);done();}).catch(()=>{});}
function songById(id){return catalog.song_library.songs.find(song=>song.song_id===id);}
function sheetsForSong(id){return catalog.song_library.cue_sheets.filter(sheet=>sheet.song_id===id);}
const songStyleNames={unspecified:'Unspecified',punk:'Punk',rock:'Rock',mellow:'Mellow',funk:'Funk',metal:'Metal',alternative:'Alternative',blues:'Blues',reggae:'Reggae',electronic:'Electronic'};
function songStyleName(song){return songStyleNames[song?.style||'unspecified']||'Unspecified';}
function timelineSheet(song){
  const sheets=sheetsForSong(song.song_id),drafts=sheets.filter(sheet=>!sheet.published).sort((a,b)=>b.revision-a.revision);
  return drafts[0]||sheets.find(sheet=>sheet.cue_sheet_id===song.active_cue_sheet_id)||null;
}
function renderSongs(){
  const library=catalog.song_library;$('song-list').replaceChildren();$('empty-songs').hidden=Boolean(library.songs.length);
  if(selectedSongId&&!songById(selectedSongId))selectedSongId=null;
  for(const song of library.songs){
    const card=node('article',undefined,'cue');
    const info=node('div');info.append(node('h3',song.title),node('p',`${song.artist} | ${songStyleName(song)} | ${song.duration_seconds}s | ${song.active_cue_sheet_id?'published timeline':'no published timeline'}`,'hint'));
    const row=node('div',undefined,'row');
    row.append(button('Timeline',()=>{selectedSongId=song.song_id;renderSongs();renderTimeline();}),button('Edit',()=>openSongEditor(song)),button('Delete',()=>deleteSong(song)));
    card.append(node('span',String(library.songs.indexOf(song)+1).padStart(2,'0'),'cue-number'),info,row);$('song-list').append(card);
  }
  renderTimeline();
}
function openSongEditor(song=null){
  editingSongId=song?.song_id||null;$('song-editor').hidden=false;$('song-editor-heading').textContent=song?'Edit song':'New song';
  $('song-title').value=song?.title||'';$('song-artist').value=song?.artist||'Phreqed';$('song-duration').value=song?.duration_seconds||'';$('song-id').value=song?.song_id||'';$('song-id').disabled=Boolean(song);$('song-style').value=song?.style||'unspecified';$('song-notes').value=song?.notes||'';
  $('song-editor').scrollIntoView({behavior:'smooth',block:'center'});
}
function deleteSong(song){
  if(sheetsForSong(song.song_id).length){notify('Songs with cue-sheet history cannot be deleted.',true);return;}
  if(catalog.song_library.setlists.some(setlist=>setlist.song_ids.includes(song.song_id))){notify('Remove this song from every setlist before deleting it.',true);return;}
  if(!confirm(`Delete ${song.title}?`))return;
  const document=songDocument();document.songs=document.songs.filter(item=>item.song_id!==song.song_id);saveSongDocument(document,'Song deleted.');
}
function renderTimeline(){
  const song=selectedSongId?songById(selectedSongId):null;$('timeline-editor').hidden=!song;if(!song)return;
  $('timeline-title').textContent=song.title;const sheet=timelineSheet(song),editable=Boolean(sheet&&!sheet.published);
  const styled=Boolean(song.style&&song.style!=='unspecified'),styleName=songStyleName(song);
  $('apply-style-default').textContent=!styled?'Choose a song style first':editable?`Replace draft with ${styleName}`:sheet?.published?`Create ${styleName} revision`:`Create ${styleName} draft`;$('apply-style-default').disabled=!styled;
  $('new-cue-draft').textContent=sheet?.published?'Copy published revision':'New manual draft';
  $('new-cue-draft').hidden=editable;$('publish-cue-sheet').hidden=!editable;$('song-cue-editor').hidden=!editable;$('song-cue-list').replaceChildren();
  $('timeline-status').textContent=!sheet?`Style: ${styleName}. Create a style-based or manual draft.`:sheet.published?`Style: ${styleName}. Published revision ${sheet.revision} remains active. Create a ${styleName} revision to generate new cues, or copy the published revision for manual edits.`:`Style: ${styleName}. Draft revision ${sheet.revision} is editable but not active. Replace it with the style default if required, then preview and publish it.`;
  if(!sheet)return;
  sheet.cues.forEach((cue,index)=>{
    const card=node('article',undefined,'cue'),info=node('div');const preset=catalog.presets.find(item=>item.preset_id===cue.preset_id);
    info.append(node('h3',preset?.name||cue.preset_id),node('p',`${cue.at_seconds}s | ${cue.transition_seconds}s transition`,'hint'));
    const row=node('div',undefined,'row');row.append(button('Preview',()=>act('preview_song_cue',{cue_sheet_id:sheet.cue_sheet_id,cue_index:index})));
    if(editable)row.append(button('Edit',()=>{editingSongCueIndex=index;$('song-cue-time').value=cue.at_seconds;$('song-cue-preset').value=cue.preset_id;$('song-cue-transition').value=cue.transition_seconds;$('save-song-cue').textContent='Save cue';$('cancel-song-cue').hidden=false;}),button('Remove',()=>{if(sheet.cues.length===1){notify('A cue sheet must keep at least one cue.',true);return;}const document=songDocument(),draft=document.cue_sheets.find(item=>item.cue_sheet_id===sheet.cue_sheet_id);draft.cues.splice(index,1);saveSongDocument(document,'Cue removed.');}));
    card.append(node('span',String(index+1).padStart(2,'0'),'cue-number'),info,row);$('song-cue-list').append(card);
  });
}
function newCueDraft(){
  const song=songById(selectedSongId);if(!song)return;const document=songDocument(),sheets=sheetsForSong(song.song_id);if(sheets.some(sheet=>!sheet.published)){notify('This song already has an editable draft.',true);return;}
  const revision=Math.max(0,...sheets.map(sheet=>sheet.revision))+1,active=sheets.find(sheet=>sheet.cue_sheet_id===song.active_cue_sheet_id);
  const draftSheet={cue_sheet_id:`cue-${song.song_id.slice(5)}-v${revision}`,song_id:song.song_id,revision,published:false,cues:active?copy(active.cues):[]};
  document.cue_sheets.push(draftSheet);
  // A draft needs its first zero-second cue before it can pass the schema.
  if(!active)draftSheet.cues=[{at_seconds:0,preset_id:catalog.presets[0].preset_id,transition_seconds:0.5}];
  saveSongDocument(document,active?'Published cues copied into a new editable revision.':'Manual cue-sheet draft created.',clearSongCueEdit);
}
function applyStyleDefault(){
  const song=songById(selectedSongId);if(!song||!song.style||song.style==='unspecified'){notify('Edit the song and choose a song style first.',true);return;}
  const sheet=timelineSheet(song),replace=Boolean(sheet&&!sheet.published);
  if(replace&&!confirm(`Replace every cue in the current draft with the ${songStyleName(song)} default?`))return;
  command('apply_song_style',{song_id:song.song_id,replace},true).then(()=>{notify(`${songStyleName(song)} baseline created as an editable draft.`);clearSongCueEdit();}).catch(()=>{});
}
function publishCueSheet(){
  const song=songById(selectedSongId),sheet=song&&timelineSheet(song);if(!sheet||sheet.published)return;
  if(!sheet.cues.length||sheet.cues[0].at_seconds!==0){notify('The first cue must start at 0 seconds.',true);return;}
  if(!confirm(`Publish revision ${sheet.revision} for ${song.title}? Published revisions cannot be changed.`))return;
  const document=songDocument(),draft=document.cue_sheets.find(item=>item.cue_sheet_id===sheet.cue_sheet_id),savedSong=document.songs.find(item=>item.song_id===song.song_id);draft.published=true;savedSong.active_cue_sheet_id=draft.cue_sheet_id;saveSongDocument(document,'Cue sheet published.');
}
function renderSetlists(){
  const library=catalog.song_library,select=$('setlist-select'),previous=selectedSetlistId||select.value;select.replaceChildren();for(const setlist of library.setlists)option(select,setlist.setlist_id,setlist.name);
  selectedSetlistId=library.setlists.some(item=>item.setlist_id===previous)?previous:(library.setlists[0]?.setlist_id||null);select.value=selectedSetlistId||'';
  const songSelect=$('setlist-song');songSelect.replaceChildren();for(const song of library.songs)option(songSelect,song.song_id,`${song.title} - ${song.artist}`);
  const setlist=library.setlists.find(item=>item.setlist_id===selectedSetlistId);$('setlist-songs').replaceChildren();$('delete-setlist').disabled=$('save-setlist').disabled=!setlist;$('add-setlist-song').disabled=!setlist||!library.songs.length;
  if(document.activeElement!==$('setlist-name'))$('setlist-name').value=setlist?.name||'';
  if(!setlist)return;
  setlist.song_ids.forEach((songId,index)=>{const song=songById(songId),card=node('article',undefined,'cue'),info=node('div');info.append(node('h3',song?.title||songId),node('p',song?.artist||'Missing song','hint'));const row=node('div',undefined,'row');
    row.append(button('Up',()=>moveSetlistSong(index,-1)),button('Down',()=>moveSetlistSong(index,1)),button('Remove',()=>removeSetlistSong(index)));row.children[0].disabled=index===0;row.children[1].disabled=index===setlist.song_ids.length-1;card.append(node('span',String(index+1).padStart(2,'0'),'cue-number'),info,row);$('setlist-songs').append(card);});
}
function updateSetlist(mutator,message){const document=songDocument(),setlist=document.setlists.find(item=>item.setlist_id===selectedSetlistId);if(!setlist)return;mutator(setlist);saveSongDocument(document,message);}
function moveSetlistSong(index,direction){updateSetlist(setlist=>{const target=index+direction;if(target<0||target>=setlist.song_ids.length)return;[setlist.song_ids[index],setlist.song_ids[target]]=[setlist.song_ids[target],setlist.song_ids[index]];},'Setlist order saved.');}
function removeSetlistSong(index){const setlist=catalog.song_library.setlists.find(item=>item.setlist_id===selectedSetlistId);if(setlist?.song_ids.length===1){notify('A setlist must keep one song; delete the setlist instead.',true);return;}updateSetlist(item=>item.song_ids.splice(index,1),'Song removed from setlist.');}
$('new-song').addEventListener('click',()=>openSongEditor());
$('cancel-song').addEventListener('click',()=>{$('song-editor').hidden=true;editingSongId=null;});
$('song-title').addEventListener('input',()=>{if(!editingSongId)$('song-id').value=slug('song',$('song-title').value);});
$('song-editor').addEventListener('submit',event=>{
  event.preventDefault();
  for(const input of $('song-editor').querySelectorAll('input'))if(!input.reportValidity())return;
  const document=songDocument(),songId=$('song-id').value.trim(),existing=document.songs.find(song=>song.song_id===editingSongId);
  if(!existing&&document.songs.some(song=>song.song_id===songId)){notify('That song ID already exists.',true);return;}
  const song={song_id:songId,title:$('song-title').value.trim(),artist:$('song-artist').value.trim(),duration_seconds:Number($('song-duration').value),notes:$('song-notes').value.trim(),source:existing?.source||'manual',active_cue_sheet_id:existing?.active_cue_sheet_id||null,style:$('song-style').value};
  if(existing)document.songs[document.songs.indexOf(existing)]=song;else document.songs.push(song);
  const oldStyle=existing?.style||'unspecified',styleChanged=Boolean(existing&&oldStyle!==song.style),message=styleChanged?`Song saved as ${songStyleName(song)}. Use Create ${songStyleName(song)} revision to generate a new style timeline.`:'Song saved.';
  saveSongDocument(document,message,()=>{$('song-editor').hidden=true;editingSongId=null;selectedSongId=song.song_id;renderSongs();});
});
function clearSongCueEdit(){editingSongCueIndex=null;$('song-cue-time').value='';$('song-cue-transition').value=0.5;$('save-song-cue').textContent='+ Add cue';$('cancel-song-cue').hidden=true;}
$('cancel-song-cue').addEventListener('click',clearSongCueEdit);
$('apply-style-default').addEventListener('click',applyStyleDefault);
$('new-cue-draft').addEventListener('click',newCueDraft);
$('publish-cue-sheet').addEventListener('click',publishCueSheet);
$('song-cue-editor').addEventListener('submit',event=>{
  event.preventDefault();
  for(const input of $('song-cue-editor').querySelectorAll('input'))if(!input.reportValidity())return;
  const song=songById(selectedSongId),sheet=song&&timelineSheet(song);if(!sheet||sheet.published){notify('Create an editable cue-sheet revision first.',true);return;}
  const cue={at_seconds:Number($('song-cue-time').value),preset_id:$('song-cue-preset').value,transition_seconds:Number($('song-cue-transition').value)},document=songDocument(),saved=document.cue_sheets.find(item=>item.cue_sheet_id===sheet.cue_sheet_id);
  if(editingSongCueIndex===null)saved.cues.push(cue);else saved.cues[editingSongCueIndex]=cue;
  saved.cues.sort((left,right)=>left.at_seconds-right.at_seconds);
  saveSongDocument(document,'Song cue saved.',clearSongCueEdit);
});
$('setlist-select').addEventListener('change',event=>{selectedSetlistId=event.target.value||null;renderSetlists();});
$('new-setlist').addEventListener('click',()=>{
  if(!catalog.song_library.songs.length){notify('Add a song before creating a setlist.',true);return;}
  const name=prompt('Setlist name','New setlist')?.trim();if(!name)return;
  const document=songDocument(),setlistId=slug('setlist',name);if(document.setlists.some(item=>item.setlist_id===setlistId)){notify('A setlist with that ID already exists.',true);return;}
  const firstSongId=selectedSongId||$('setlist-song').value||catalog.song_library.songs[0].song_id;
  document.setlists.push({setlist_id:setlistId,name,song_ids:[firstSongId],notes:''});selectedSetlistId=setlistId;saveSongDocument(document,'Setlist created.');
});
$('add-setlist-song').addEventListener('click',()=>updateSetlist(setlist=>setlist.song_ids.push($('setlist-song').value),'Song added to setlist.'));
$('save-setlist').addEventListener('click',()=>{
  const name=$('setlist-name').value.trim();if(!name){notify('Give the setlist a name.',true);return;}updateSetlist(setlist=>{setlist.name=name;},'Setlist saved.');
});
$('delete-setlist').addEventListener('click',()=>{
  const setlist=catalog.song_library.setlists.find(item=>item.setlist_id===selectedSetlistId);if(!setlist||!confirm(`Delete ${setlist.name}?`))return;
  const document=songDocument();document.setlists=document.setlists.filter(item=>item.setlist_id!==setlist.setlist_id);selectedSetlistId=null;saveSongDocument(document,'Setlist deleted.');
});
$('performance-mode').addEventListener('change',event=>{
  const mode=event.target.value,setlistId=mode==='setlist'?($('performance-setlist').value||null):null;
  act('performance_mode',{mode,setlist_id:setlistId});
});
$('performance-setlist').addEventListener('change',event=>act('load_setlist',{setlist_id:event.target.value}));
$('previous-song').addEventListener('click',()=>act('previous_song'));
$('next-song').addEventListener('click',()=>act('next_song'));
$('toggle-song').addEventListener('click',()=>act(state?.performance?.running?'stop_song':'start_song'));
$('quick-preset').addEventListener('change',e=>act('preset',{value:e.target.value}));
$('master').addEventListener('input',e=>{$('master-value').textContent=`${Math.round(e.target.value*100)}%`;});
$('master').addEventListener('change',e=>act('brightness',{value:Number(e.target.value)}));
$('contrast').addEventListener('input',e=>{$('contrast-value').textContent=`${Number(e.target.value).toFixed(2)}x`;});
$('contrast').addEventListener('change',e=>act('contrast',{value:Number(e.target.value)}));
const monitorBrightnessControl=$('monitor-brightness');
monitorBrightnessControl.value=monitorBrightness;$('monitor-brightness-value').textContent=`${monitorBrightness.toFixed(2)}x`;
monitorBrightnessControl.addEventListener('input',e=>{monitorBrightness=Number(e.target.value);$('monitor-brightness-value').textContent=`${monitorBrightness.toFixed(2)}x`;});
monitorBrightnessControl.addEventListener('change',()=>{try{localStorage.setItem(MONITOR_BRIGHTNESS_KEY,String(monitorBrightness));}catch(_){}});
$('audio-auto-level').addEventListener('change',e=>act('audio_auto_level',{enabled:e.target.checked}));
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

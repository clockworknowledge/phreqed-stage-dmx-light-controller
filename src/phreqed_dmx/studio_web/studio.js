const token = document.querySelector('meta[name="phreqed-studio-token"]').content;
let state = null;
let selectedAsset = null;

const el = id => document.getElementById(id);

function notice(message, error = false) {
  const box = el('notice');
  box.textContent = message;
  box.classList.toggle('error', error);
  box.hidden = false;
  window.clearTimeout(notice.timer);
  notice.timer = window.setTimeout(() => { box.hidden = true; }, 5000);
}

async function command(payload) {
  const response = await fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Phreqed-Studio-Token': token},
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Studio command failed');
  state = body.state;
  render();
  return body;
}

function assetItem(asset) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'item-button' + (selectedAsset === asset.asset_id ? ' selected' : '');
  button.dataset.search = `${asset.title} ${asset.original_name} ${asset.family}`.toLowerCase();
  const title = document.createElement('strong');
  title.textContent = asset.title;
  const subtitle = document.createElement('small');
  subtitle.textContent = `${asset.original_name} · ${(asset.size_bytes / 1048576).toFixed(1)} MB`;
  const family = document.createElement('span');
  family.className = 'family';
  family.textContent = asset.family.replaceAll('-', ' ');
  button.append(title, family, subtitle);
  button.addEventListener('click', () => { selectedAsset = asset.asset_id; renderAssets(); });
  return button;
}

function renderAssets() {
  const list = el('asset-list');
  list.replaceChildren(...state.assets.map(assetItem));
  el('asset-empty').hidden = state.assets.length > 0;
  const query = el('asset-search').value.trim().toLowerCase();
  [...list.children].forEach(item => { item.hidden = Boolean(query) && !item.dataset.search.includes(query); });
  const asset = state.assets.find(item => item.asset_id === selectedAsset);
  if (!asset) return;
  const detail = el('asset-detail');
  detail.className = '';
  detail.innerHTML = '';
  const heading = document.createElement('div');
  heading.className = 'detail-empty';
  const kicker = document.createElement('p'); kicker.className = 'eyebrow'; kicker.textContent = asset.family.toUpperCase().replaceAll('-', ' ');
  const title = document.createElement('h3'); title.textContent = asset.title;
  heading.append(kicker, title);
  const dl = document.createElement('dl'); dl.className = 'detail-grid';
  [['Asset ID', asset.asset_id], ['Original', asset.original_name], ['Media type', asset.media_type], ['Bytes', asset.size_bytes.toLocaleString()], ['SHA-256', asset.sha256], ['Imported', asset.created_utc]].forEach(([label, value]) => {
    const dt = document.createElement('dt'); dt.textContent = label;
    const dd = document.createElement('dd'); dd.textContent = value;
    dl.append(dt, dd);
  });
  detail.append(heading, dl);
}

function renderStorylets() {
  const list = el('storylet-list');
  list.replaceChildren(...state.storylets.map(item => {
    const button = document.createElement('button'); button.type = 'button'; button.className = 'item-button';
    const title = document.createElement('strong'); title.textContent = item.title;
    const family = document.createElement('span'); family.className = 'family'; family.textContent = item.loop ? 'loop' : 'one shot';
    const subtitle = document.createElement('small'); subtitle.textContent = `${item.duration_seconds.toFixed(1)}s · ${item.markers.length} markers`;
    button.append(title, family, subtitle); return button;
  }));
  el('storylet-empty').hidden = state.storylets.length > 0;
  const select = el('storylet-asset');
  const current = select.value;
  select.replaceChildren(...state.assets.map(asset => {
    const option = document.createElement('option'); option.value = asset.asset_id; option.textContent = `${asset.title} · ${asset.family}`; return option;
  }));
  if (state.assets.some(asset => asset.asset_id === current)) select.value = current;
}

function render() {
  el('workspace-name').textContent = state.workspace_id;
  el('asset-count').textContent = state.assets.length;
  el('storylet-count').textContent = state.storylets.length;
  el('relationship-count').textContent = state.graph.relationships;
  el('node-count').textContent = state.graph.nodes;
  el('graph-link-count').textContent = state.graph.relationships;
  el('graph-path').textContent = state.graph.export_path;
  const relate = state.relate;
  el('relate-status').textContent = relate.status === 'ready'
    ? `Ready · ${relate.nodes} nodes · ${relate.relationships} links · ${relate.store}`
    : relate.error || `${relate.status} · ${relate.store || 'not configured'}`;
  const family = el('import-family');
  if (!family.children.length) family.replaceChildren(...state.asset_families.map(value => {
    const option = document.createElement('option'); option.value = value; option.textContent = value.replaceAll('-', ' '); return option;
  }));
  if (!selectedAsset && state.assets.length) selectedAsset = state.assets[0].asset_id;
  renderAssets();
  renderStorylets();
}

function parseMarkers(text) {
  return text.split(/\r?\n/).map(line => line.trim()).filter(Boolean).map(line => {
    const parts = line.split('=');
    if (parts.length !== 2 || !parts[0] || !Number.isFinite(Number(parts[1]))) throw new Error(`Invalid marker: ${line}`);
    return {name: parts[0], at_seconds: Number(parts[1])};
  });
}

document.querySelectorAll('.nav-button').forEach(button => button.addEventListener('click', () => {
  document.querySelectorAll('.nav-button').forEach(item => item.classList.toggle('active', item === button));
  ['assets', 'storylets', 'graph'].forEach(view => { el(`${view}-view`).hidden = view !== button.dataset.view; });
  const titles = {assets: ['MEDIA LIBRARY', 'Assets'], storylets: ['REUSABLE VISUAL UNITS', 'Storylets'], graph: ['RELATIONSHIP INDEX', 'Graph']};
  [el('view-kicker').textContent, el('view-title').textContent] = titles[button.dataset.view];
}));

el('asset-search').addEventListener('input', renderAssets);
el('import-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const result = await command({action: 'import_asset', path: el('import-path').value, title: el('import-title').value, family: el('import-family').value});
    selectedAsset = result.asset.asset_id; render(); notice(`Imported ${result.asset.title}`); event.target.reset();
  } catch (error) { notice(error.message, true); }
});
el('storylet-form').addEventListener('submit', async event => {
  event.preventDefault();
  try {
    const result = await command({action: 'create_storylet', storylet_id: el('storylet-id').value, asset_id: el('storylet-asset').value, title: el('storylet-title').value, duration_seconds: Number(el('storylet-duration').value), loop: el('storylet-loop').checked, markers: parseMarkers(el('storylet-markers').value)});
    notice(`Created ${result.storylet.title}`); event.target.reset();
  } catch (error) { notice(error.message, true); }
});
el('export-graph').addEventListener('click', async () => {
  try { const result = await command({action: 'export_graph'}); notice(`Graph projection written to ${result.path}`); }
  catch (error) { notice(error.message, true); }
});
el('sync-relate').addEventListener('click', async () => {
  try {
    const result = await command({action: 'sync_relate'});
    notice(`Relate synchronized: ${result.relate.nodes} nodes · ${result.relate.relationships} links`);
  } catch (error) { notice(error.message, true); }
});

fetch('/api/state').then(response => response.json()).then(value => { state = value; render(); }).catch(error => notice(error.message, true));

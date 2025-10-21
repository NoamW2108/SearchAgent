const form = document.getElementById('searchForm');
const input = document.getElementById('q');
const output = document.getElementById('output');
const go = document.getElementById('go');
const aboutLink = document.getElementById('aboutLink');

aboutLink.onclick = (e) => { e.preventDefault(); alert('This local tool searches DuckDuckGo results and returns a verified root domain that contains query tokens. It avoids social/wiki sites and unrelated matches for gibberish inputs.'); };

function setBusy(b){
  go.disabled = b;
  go.setAttribute('aria-busy', b ? 'true' : 'false');
}

async function doSearch(q){
  output.innerHTML = '';
  const box = document.createElement('div');
  box.className = 'result';
  box.textContent = 'Searching...';
  output.appendChild(box);
  setBusy(true);
  try{
    const resp = await fetch('/api/search', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({name:q})
    });
    if(!resp.ok){ throw new Error('Network error'); }
    const data = await resp.json();
    output.innerHTML = '';
    if(data.url){
      const res = document.createElement('div');
      res.className = 'result';
      const a = document.createElement('a');
      a.href = data.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.textContent = data.url;
      a.setAttribute('aria-label', 'Open site in new tab');
      res.appendChild(a);

      const actions = document.createElement('div');
      actions.className = 'actions';

      const copyBtn = document.createElement('button');
      copyBtn.type = 'button';
      copyBtn.textContent = 'Copy';
      copyBtn.onclick = async () => {
        try{ await navigator.clipboard.writeText(data.url); copyBtn.textContent='Copied'; setTimeout(()=>copyBtn.textContent='Copy',1300);}catch(e){alert('Copy failed');}
      };

      const openBtn = document.createElement('button');
      openBtn.type = 'button';
      openBtn.textContent = 'Open';
      openBtn.onclick = ()=> window.open(data.url, '_blank', 'noopener');

      actions.appendChild(copyBtn);
      actions.appendChild(openBtn);
      res.appendChild(actions);

      const meta = document.createElement('div');
      meta.className = 'small';
      meta.textContent = 'Verified live';
      res.appendChild(meta);

      output.appendChild(res);
      copyBtn.focus();
    } else {
      const no = document.createElement('div');
      no.className = 'result';
      no.textContent = 'No site found — try a different query.';
      output.appendChild(no);
    }
  }catch(err){
    output.innerHTML = '';
    const e = document.createElement('div');
    e.className = 'result';
    e.textContent = 'Error searching. Check your internet connection.';
    output.appendChild(e);
  }finally{
    setBusy(false);
  }
}

form.addEventListener('submit', (ev)=>{
  ev.preventDefault();
  const q = input.value.trim();
  if(!q) return;
  doSearch(q);
});

input.addEventListener('keydown', (ev)=>{ if(ev.key === 'Enter'){ ev.preventDefault(); form.dispatchEvent(new Event('submit')); }});

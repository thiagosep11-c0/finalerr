#!/usr/bin/env python3
"""
Adiciona rotas /api/cidade/* ao app.py
e o tab Cidades ao index.html
"""
import re, os, sys, ast

APP = '/root/grupos_ia/webapp/app.py'
HTML = '/root/grupos_ia/webapp/index.html'

# ─── ROTAS NOVAS ──────────────────────────────────────────────────────────────
ROTAS = r'''
# ═══════════════════════════════════════════════════════════════════════════════
# BUSCA POR CIDADE
# ═══════════════════════════════════════════════════════════════════════════════
_CIDADE_SCRIPT  = '/root/grupos_ia/busca_por_cidade.py'
_CIDADE_CONFIG  = '/root/grupos_ia/busca_cidade_config.json'
_CIDADE_STATUS  = '/root/grupos_ia/busca_cidade_status.json'
_CIDADE_LOG     = '/root/grupos_ia/busca_cidade.log'
_CIDADE_PAUSE   = '/root/grupos_ia/PAUSAR.txt'

_TERMOS_CIDADE_DEFAULT = [
    'vendas', 'venda', 'desapego', 'desapega', 'olx', 'trocas',
    'classificados', 'feira do rolo', 'brick', 'jardim', 'moradores',
    'vila', 'santo', 'santa', 'são', 'parque', 'bairro', 'doação',
    'brique', 'centro', 'condomínio', 'negócios', 'cidade', 'região',
    'serviços', 'permuta', 'bazar', 'gratuito', 'comércio', 'comunidade',
]

@app.route('/api/cidade/termos')
@require_auth
def cidade_termos():
    return jsonify({'termos': _TERMOS_CIDADE_DEFAULT})

@app.route('/api/cidade/start', methods=['POST'])
@require_auth
def cidade_start():
    d = request.json or {}
    cidades = [c.strip() for c in d.get('cidades', []) if str(c).strip()]
    termos  = d.get('termos', _TERMOS_CIDADE_DEFAULT)
    anos    = d.get('anos', ['2026'])
    sufixos = d.get('sufixos', ['chat', '?mode'])
    if not cidades:
        return jsonify({'ok': False, 'erro': 'Nenhuma cidade informada'}), 400
    if not isinstance(anos, list) or not anos:
        anos = ['2026']
    cfg = {'cidades': cidades, 'termos': termos, 'anos': [str(a) for a in anos], 'sufixos': sufixos}
    with open(_CIDADE_CONFIG, 'w', encoding='utf-8') as _cf:
        import json as _json2
        _json2.dump(cfg, _cf, ensure_ascii=False, indent=2)
    # Para processo anterior se existir
    _subproc.run(['pkill', '-f', 'busca_por_cidade.py'], capture_output=True)
    time.sleep(1)
    try: os.remove(_CIDADE_PAUSE)
    except: pass
    with open(_CIDADE_LOG, 'a', encoding='utf-8') as _lf:
        proc = _subproc.Popen(
            ['python3', '-u', _CIDADE_SCRIPT],
            stdout=_lf, stderr=_subproc.STDOUT,
            start_new_session=True,
            env={**os.environ, 'DISPLAY': ':99'}
        )
    total = len(cidades) * len(termos) * len(anos) * len(sufixos)
    return jsonify({'ok': True, 'total_queries': total, 'pid': proc.pid,
                    'cidades': cidades, 'anos': anos})

@app.route('/api/cidade/stop', methods=['POST'])
@require_auth
def cidade_stop():
    _subproc.run(['pkill', '-f', 'busca_por_cidade.py'], capture_output=True)
    try: os.remove(_CIDADE_PAUSE)
    except: pass
    if os.path.exists(_CIDADE_STATUS):
        import json as _json3
        try:
            with open(_CIDADE_STATUS) as _sf: st = _json3.load(_sf)
            st['rodando'] = False
            with open(_CIDADE_STATUS, 'w') as _sf: _json3.dump(st, _sf)
        except: pass
    return jsonify({'ok': True})

@app.route('/api/cidade/pause', methods=['POST'])
@require_auth
def cidade_pause():
    with open(_CIDADE_PAUSE, 'w') as _pf: _pf.write(str(time.time()))
    return jsonify({'ok': True})

@app.route('/api/cidade/resume', methods=['POST'])
@require_auth
def cidade_resume():
    try: os.remove(_CIDADE_PAUSE)
    except: pass
    return jsonify({'ok': True})

@app.route('/api/cidade/status')
@require_auth
def cidade_status():
    import json as _json4
    rodando = False
    try:
        r = _subproc.run(['pgrep', '-f', 'busca_por_cidade.py'], capture_output=True)
        rodando = r.returncode == 0
    except: pass
    pausado = os.path.exists(_CIDADE_PAUSE)
    st = {}
    if os.path.exists(_CIDADE_STATUS):
        try:
            with open(_CIDADE_STATUS, encoding='utf-8') as _sf: st = _json4.load(_sf)
        except: pass
    cfg = {}
    if os.path.exists(_CIDADE_CONFIG):
        try:
            with open(_CIDADE_CONFIG, encoding='utf-8') as _cf: cfg = _json4.load(_cf)
        except: pass
    return jsonify({'rodando': rodando, 'pausado': pausado, 'status': st, 'config': cfg})

@app.route('/api/cidade/logs')
@require_auth
def cidade_logs():
    n = int(request.args.get('n', 60))
    try:
        with open(_CIDADE_LOG, 'r', encoding='utf-8', errors='replace') as _lf:
            linhas = _lf.readlines()
        return jsonify({'linhas': [l.rstrip() for l in linhas[-n:]]})
    except:
        return jsonify({'linhas': []})

@app.route('/api/cidade/importar', methods=['POST'])
@require_auth
def cidade_importar():
    """Importa grupos de GRUPOS_CIDADE/grupos_validos.txt para o sistema principal"""
    import json as _json5
    arq = '/root/grupos_ia/GRUPOS_CIDADE/grupos_validos.txt'
    if not os.path.exists(arq):
        return jsonify({'ok': False, 'erro': 'Arquivo nao encontrado', 'importados': 0})
    db2 = get_db()
    importados = 0
    erros = 0
    try:
        with open(arq, 'r', encoding='utf-8') as _af:
            for linha in _af:
                linha = linha.strip()
                import re as _re3
                _lm = _re3.search(r'https://chat\.whatsapp\.com/([A-Za-z0-9]+)', linha)
                if not _lm: continue
                link = f'https://chat.whatsapp.com/{_lm.group(1)}'
                partes = linha.split(' | ')
                nicho = ''
                if len(partes) >= 2:
                    nm = _re3.search(r'\[([^\]]+)\]', partes[1])
                    if nm: nicho = nm.group(1).lower()
                try:
                    db2.collection('grupos_nao_verificados').document(_lm.group(1)).set({
                        'link': link, 'nicho': nicho, 'fonte': 'busca_cidade',
                        'status': 'nao_verificado', 'adicionado': datetime.utcnow().isoformat()
                    }, merge=True)
                    importados += 1
                except Exception as _ie:
                    erros += 1
    except Exception as _e2:
        return jsonify({'ok': False, 'erro': str(_e2), 'importados': importados})
    return jsonify({'ok': True, 'importados': importados, 'erros': erros})

# ═══════════════════════════════════════════════════════════════════════════════
# FIM BUSCA POR CIDADE
# ═══════════════════════════════════════════════════════════════════════════════
'''

# ─── PATCH app.py ─────────────────────────────────────────────────────────────
print('=== Patching app.py ===')
with open(APP, 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Marca de inserção — antes do if __name__
ANCHOR = "if __name__ == '__main__':"
idx = content.rfind(ANCHOR)
if idx == -1:
    print('ERRO: ancora nao encontrada em app.py')
    sys.exit(1)

if '_CIDADE_SCRIPT' in content:
    print('Rotas de cidade já existem — skip')
else:
    content = content[:idx] + ROTAS + '\n' + content[idx:]
    with open(APP, 'w', encoding='utf-8') as f:
        f.write(content)
    print('app.py patched OK')

# Valida sintaxe
try:
    ast.parse(content)
    print('Sintaxe OK')
except SyntaxError as e:
    print('SYNTAX ERROR:', e)
    sys.exit(1)


# ─── PATCH index.html ─────────────────────────────────────────────────────────
print('\n=== Patching index.html ===')
with open(HTML, 'r', encoding='utf-8', errors='replace') as f:
    html = f.read()

if 'painel-cidades' in html:
    print('Tab cidades já existe — skip')
else:
    # 1. Adicionar botão na toolbar (depois do botão Pesquisas)
    BTN_PESQUISAS = '<button class="btn-toolbar" style="background:#7c3aed" onclick="mostrarPainel(\'painel-pesquisas\')">'
    BTN_CIDADES = '''<button class="btn-toolbar" style="background:#0891b2" onclick="mostrarPainel('painel-cidades')">
          🏙️ Cidades
        </button>'''
    if BTN_PESQUISAS in html:
        # Encontra o fim desse botão e insere depois
        idx_btn = html.find(BTN_PESQUISAS)
        # Procura o próximo </button> depois desse índice
        idx_close = html.find('</button>', idx_btn) + len('</button>')
        html = html[:idx_close] + '\n        ' + BTN_CIDADES + html[idx_close:]
        print('Botão adicionado na toolbar')
    else:
        print('AVISO: botão Pesquisas nao encontrado para inserir depois')

    # 2. Adicionar o painel (antes do </body> ou antes da ultima </div>)
    PAINEL_HTML = '''
<!-- ═══════════════════ PAINEL CIDADES ═══════════════════ -->
<div id="painel-cidades" class="painel" style="display:none">
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
    <h2 style="margin:0;font-size:1.4rem">🏙️ Busca por Cidade / Bairro / Estado</h2>
    <button onclick="voltarHome()" style="background:#374151;border:none;color:#fff;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:0.85rem">🏠 Início</button>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px">

    <!-- Coluna esquerda: cidades -->
    <div style="background:#1f2937;border-radius:12px;padding:18px">
      <label style="font-size:0.85rem;color:#9ca3af;display:block;margin-bottom:8px">
        📍 Cidades / Bairros / Estados <span style="color:#6b7280">(uma por linha)</span>
      </label>
      <textarea id="ct-cidades" rows="10"
        placeholder="São Paulo&#10;Rio de Janeiro&#10;Belo Horizonte&#10;Copacabana&#10;Centro&#10;Zona Sul"
        style="width:100%;background:#111827;color:#e5e7eb;border:1px solid #374151;border-radius:8px;padding:10px;font-size:0.9rem;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>
      <div style="margin-top:8px;font-size:0.78rem;color:#6b7280" id="ct-cont-cidades">0 cidades</div>
    </div>

    <!-- Coluna direita: configs -->
    <div style="display:flex;flex-direction:column;gap:14px">

      <!-- Anos -->
      <div style="background:#1f2937;border-radius:12px;padding:16px">
        <div style="font-size:0.85rem;color:#9ca3af;margin-bottom:10px">📅 Filtrar por Ano</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap" id="ct-anos">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="2026" checked onchange="ctAtualizarResumo()"> <span>2026</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="2025" onchange="ctAtualizarResumo()"> <span>2025</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="2024" onchange="ctAtualizarResumo()"> <span>2024</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="2023" onchange="ctAtualizarResumo()"> <span>2023</span>
          </label>
        </div>
      </div>

      <!-- Sufixos -->
      <div style="background:#1f2937;border-radius:12px;padding:16px">
        <div style="font-size:0.85rem;color:#9ca3af;margin-bottom:10px">🔍 Tipo de busca</div>
        <div style="display:flex;gap:10px;flex-wrap:wrap" id="ct-sufixos">
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="chat" checked onchange="ctAtualizarResumo()"> <span>"chat"</span>
          </label>
          <label style="display:flex;align-items:center;gap:6px;cursor:pointer">
            <input type="checkbox" value="?mode" checked onchange="ctAtualizarResumo()"> <span>"?mode"</span>
          </label>
        </div>
      </div>

      <!-- Resumo -->
      <div style="background:#111827;border:1px solid #374151;border-radius:10px;padding:14px;font-size:0.82rem;color:#9ca3af" id="ct-resumo">
        Selecione cidades e configure os filtros acima
      </div>

    </div><!-- fim coluna direita -->
  </div><!-- fim grid -->

  <!-- Termos -->
  <div style="background:#1f2937;border-radius:12px;padding:18px;margin-bottom:18px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <div style="font-size:0.85rem;color:#9ca3af">🏷️ Termos de busca</div>
      <div style="display:flex;gap:8px">
        <button onclick="ctSelecionarTodos(true)" style="background:#374151;border:none;color:#d1d5db;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:0.78rem">Todos</button>
        <button onclick="ctSelecionarTodos(false)" style="background:#374151;border:none;color:#d1d5db;padding:4px 10px;border-radius:6px;cursor:pointer;font-size:0.78rem">Nenhum</button>
      </div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px" id="ct-termos-grid"></div>
  </div>

  <!-- Controles -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:18px;flex-wrap:wrap">
    <button id="ct-btn-iniciar" onclick="ctIniciar()" style="background:#0891b2;border:none;color:#fff;padding:10px 22px;border-radius:10px;cursor:pointer;font-size:1rem;font-weight:600">
      ▶ Iniciar buscas
    </button>
    <button id="ct-btn-pause" onclick="ctPausar()" style="background:#d97706;border:none;color:#fff;padding:10px 18px;border-radius:10px;cursor:pointer;font-size:0.9rem;display:none">
      ⏸ Pausar
    </button>
    <button id="ct-btn-resume" onclick="ctRetomar()" style="background:#059669;border:none;color:#fff;padding:10px 18px;border-radius:10px;cursor:pointer;font-size:0.9rem;display:none">
      ▶ Retomar
    </button>
    <button id="ct-btn-stop" onclick="ctParar()" style="background:#dc2626;border:none;color:#fff;padding:10px 18px;border-radius:10px;cursor:pointer;font-size:0.9rem;display:none">
      ⏹ Parar
    </button>
    <button onclick="ctImportar()" style="background:#7c3aed;border:none;color:#fff;padding:10px 18px;border-radius:10px;cursor:pointer;font-size:0.9rem">
      📥 Importar grupos encontrados
    </button>
  </div>

  <!-- Status em tempo real -->
  <div id="ct-status-box" style="display:none;background:#1f2937;border-radius:12px;padding:18px;margin-bottom:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <div style="font-weight:600" id="ct-status-titulo">⏳ Buscando...</div>
      <div style="font-size:0.8rem;color:#9ca3af" id="ct-status-pct">0%</div>
    </div>
    <div style="background:#111827;border-radius:6px;height:10px;overflow:hidden;margin-bottom:12px">
      <div id="ct-bar" style="height:100%;background:linear-gradient(90deg,#0891b2,#06b6d4);transition:width 0.5s;width:0%"></div>
    </div>
    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px;font-size:0.82rem;margin-bottom:12px">
      <div style="background:#111827;border-radius:8px;padding:10px;text-align:center">
        <div style="color:#9ca3af;margin-bottom:4px">Cidade</div>
        <div style="color:#06b6d4;font-weight:600" id="ct-curr-cidade">—</div>
      </div>
      <div style="background:#111827;border-radius:8px;padding:10px;text-align:center">
        <div style="color:#9ca3af;margin-bottom:4px">Termo</div>
        <div style="color:#60a5fa;font-weight:600" id="ct-curr-termo">—</div>
      </div>
      <div style="background:#111827;border-radius:8px;padding:10px;text-align:center">
        <div style="color:#9ca3af;margin-bottom:4px">Ano</div>
        <div style="color:#a78bfa;font-weight:600" id="ct-curr-ano">—</div>
      </div>
    </div>
    <div style="display:flex;gap:12px;font-size:0.82rem">
      <span>Query: <b id="ct-curr-query">—</b></span>
      <span>Links: <b id="ct-total-links" style="color:#10b981">0</b></span>
    </div>
  </div>

  <!-- Logs -->
  <div style="background:#1f2937;border-radius:12px;padding:18px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div style="font-size:0.85rem;color:#9ca3af">📋 Log da busca</div>
      <button onclick="ctRefreshLogs()" style="background:#374151;border:none;color:#d1d5db;padding:4px 12px;border-radius:6px;cursor:pointer;font-size:0.78rem">🔄 Atualizar</button>
    </div>
    <pre id="ct-log" style="background:#111827;border-radius:8px;padding:12px;font-size:0.75rem;color:#d1d5db;overflow-y:auto;max-height:280px;white-space:pre-wrap;margin:0"></pre>
  </div>
</div>
<!-- ═══════════════════ FIM PAINEL CIDADES ═══════════════════ -->
'''

    # Insere antes de </body>
    idx_body = html.rfind('</body>')
    if idx_body == -1:
        idx_body = html.rfind('</div>')
    html = html[:idx_body] + PAINEL_HTML + '\n' + html[idx_body:]
    print('Painel HTML inserido')

    # 3. Adicionar JS antes de </script> final ou antes de </body>
    JS = r'''
// ──────────────────── CIDADES ────────────────────
const _CT_TERMOS = [
  'vendas','venda','desapego','desapega','olx','trocas',
  'classificados','feira do rolo','brick','jardim','moradores',
  'vila','santo','santa','são','parque','bairro','doação',
  'brique','centro','condomínio','negócios','cidade','região',
  'serviços','permuta','bazar','gratuito','comércio','comunidade'
];

let _ctInterval = null;

function ctInit() {
  const grid = document.getElementById('ct-termos-grid');
  if (!grid || grid.children.length) return;
  _CT_TERMOS.forEach(t => {
    const lbl = document.createElement('label');
    lbl.style.cssText = 'display:flex;align-items:center;gap:5px;cursor:pointer;background:#111827;padding:5px 10px;border-radius:6px;font-size:0.82rem';
    const cb = document.createElement('input');
    cb.type = 'checkbox'; cb.value = t; cb.checked = true;
    cb.onchange = ctAtualizarResumo;
    lbl.append(cb, document.createTextNode(t));
    grid.appendChild(lbl);
  });
  const ta = document.getElementById('ct-cidades');
  if (ta) ta.addEventListener('input', ctAtualizarResumo);
  ctAtualizarResumo();
  ctRefreshStatus();
}

function ctGetCidades() {
  const ta = document.getElementById('ct-cidades');
  if (!ta) return [];
  return ta.value.split('\n').map(s=>s.trim()).filter(Boolean);
}
function ctGetAnos() {
  return [...document.querySelectorAll('#ct-anos input:checked')].map(c=>c.value);
}
function ctGetSufixos() {
  return [...document.querySelectorAll('#ct-sufixos input:checked')].map(c=>c.value);
}
function ctGetTermos() {
  return [...document.querySelectorAll('#ct-termos-grid input:checked')].map(c=>c.value);
}

function ctAtualizarResumo() {
  const cidades = ctGetCidades();
  const anos    = ctGetAnos();
  const sufixos = ctGetSufixos();
  const termos  = ctGetTermos();
  const total   = cidades.length * termos.length * anos.length * sufixos.length;
  const c = document.getElementById('ct-cont-cidades');
  if (c) c.textContent = cidades.length + ' cidade(s)';
  const r = document.getElementById('ct-resumo');
  if (r) {
    if (total === 0) {
      r.innerHTML = '<span style="color:#ef4444">Configure ao menos 1 cidade, 1 termo, 1 ano e 1 sufixo</span>';
    } else {
      r.innerHTML = `<b style="color:#06b6d4">${total.toLocaleString('pt-BR')} queries</b> a executar<br>
        <span style="font-size:0.76rem">${cidades.length} cidades × ${termos.length} termos × ${anos.length} ano(s) × ${sufixos.length} sufixo(s)</span>`;
    }
  }
}

function ctSelecionarTodos(val) {
  document.querySelectorAll('#ct-termos-grid input').forEach(c => c.checked = val);
  ctAtualizarResumo();
}

async function ctIniciar() {
  const cidades = ctGetCidades();
  const anos    = ctGetAnos();
  const sufixos = ctGetSufixos();
  const termos  = ctGetTermos();
  if (!cidades.length) { alert('Informe ao menos uma cidade!'); return; }
  if (!termos.length)  { alert('Selecione ao menos um termo!'); return; }
  if (!anos.length)    { alert('Selecione ao menos um ano!');   return; }
  if (!sufixos.length) { alert('Selecione ao menos um sufixo!'); return; }
  const btn = document.getElementById('ct-btn-iniciar');
  btn.disabled = true; btn.textContent = '⏳ Iniciando...';
  try {
    const r = await apiFetch('/api/cidade/start', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({cidades, termos, anos, sufixos})
    });
    const d = await r.json();
    if (d.ok) {
      ctMostrarStatus(true);
      ctStartPolling();
    } else {
      alert('Erro: ' + (d.erro || 'desconhecido'));
    }
  } catch(e) { alert('Erro: ' + e); }
  finally { btn.disabled = false; btn.textContent = '▶ Iniciar buscas'; }
}

async function ctPausar() {
  await apiFetch('/api/cidade/pause', {method:'POST'});
  document.getElementById('ct-btn-pause').style.display='none';
  document.getElementById('ct-btn-resume').style.display='';
}
async function ctRetomar() {
  await apiFetch('/api/cidade/resume', {method:'POST'});
  document.getElementById('ct-btn-pause').style.display='';
  document.getElementById('ct-btn-resume').style.display='none';
}
async function ctParar() {
  if (!confirm('Parar a busca por cidades?')) return;
  await apiFetch('/api/cidade/stop', {method:'POST'});
  ctMostrarStatus(false);
  clearInterval(_ctInterval);
}

function ctMostrarStatus(mostrar) {
  const box = document.getElementById('ct-status-box');
  if (box) box.style.display = mostrar ? '' : 'none';
  document.getElementById('ct-btn-stop').style.display  = mostrar ? '' : 'none';
  document.getElementById('ct-btn-pause').style.display = mostrar ? '' : 'none';
  document.getElementById('ct-btn-resume').style.display = 'none';
}

function ctStartPolling() {
  clearInterval(_ctInterval);
  _ctInterval = setInterval(ctRefreshStatus, 4000);
}

async function ctRefreshStatus() {
  try {
    const r = await apiFetch('/api/cidade/status');
    const d = await r.json();
    const st = d.status || {};
    const rodando = d.rodando;
    ctMostrarStatus(rodando || (st.pct > 0 && st.pct < 100));
    if (d.pausado) {
      document.getElementById('ct-btn-pause').style.display='none';
      document.getElementById('ct-btn-resume').style.display='';
    }
    const pct = st.pct || 0;
    document.getElementById('ct-bar').style.width = pct + '%';
    document.getElementById('ct-status-pct').textContent = pct + '% (' + (st.atual||0) + '/' + (st.total||0) + ')';
    document.getElementById('ct-curr-cidade').textContent = st.cidade || '—';
    document.getElementById('ct-curr-termo').textContent  = st.termo  || '—';
    document.getElementById('ct-curr-ano').textContent    = st.ano    || '—';
    document.getElementById('ct-total-links').textContent = st.links  || 0;
    if (st.cidade && st.termo && st.sufixo) {
      document.getElementById('ct-curr-query').textContent =
        `${st.termo} "${st.cidade}" "${st.sufixo}"`;
    }
    if (st.pct === 100 || !rodando) {
      document.getElementById('ct-status-titulo').textContent = pct === 100 ? '✅ Concluído!' : '⏹ Parado';
      clearInterval(_ctInterval);
    }
    await ctRefreshLogs();
  } catch(e) {}
}

async function ctRefreshLogs() {
  try {
    const r = await apiFetch('/api/cidade/logs?n=50');
    const d = await r.json();
    const el = document.getElementById('ct-log');
    if (el && d.linhas) {
      el.textContent = d.linhas.join('\n');
      el.scrollTop = el.scrollHeight;
    }
  } catch(e) {}
}

async function ctImportar() {
  if (!confirm('Importar grupos da busca por cidade para o sistema de verificação?')) return;
  try {
    const r = await apiFetch('/api/cidade/importar', {method:'POST'});
    const d = await r.json();
    if (d.ok) alert(`✅ ${d.importados} grupos importados!`);
    else alert('Erro: ' + (d.erro || 'desconhecido'));
  } catch(e) { alert('Erro: ' + e); }
}
// ──────────────────── FIM CIDADES ────────────────────
'''

    # Insere JS antes de </script> da área principal ou antes de </body>
    # Localiza o último bloco </script> antes de </body>
    last_script = html.rfind('</script>')
    idx_body2 = html.rfind('</body>')
    if last_script != -1 and last_script < idx_body2:
        html = html[:last_script] + JS + '\n' + html[last_script:]
        print('JS inserido antes de </script>')
    else:
        html = html[:idx_body2] + f'<script>{JS}</script>\n' + html[idx_body2:]
        print('JS inserido como novo <script> antes de </body>')

    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(html)
    print('index.html patched OK')

# Reinicia Flask
import subprocess
print('\n=== Reiniciando Flask ===')
subprocess.run('fuser -k 5000/tcp 2>/dev/null; pkill -f "webapp/app.py" 2>/dev/null; pkill -f "python3 app.py" 2>/dev/null; true', shell=True)
import time; time.sleep(2)
proc = subprocess.Popen(
    ['python3', '-u', '/root/grupos_ia/webapp/app.py'],
    cwd='/root/grupos_ia/webapp',
    stdout=open('/root/grupos_ia/webapp/app.log', 'a'),
    stderr=subprocess.STDOUT,
    start_new_session=True
)
time.sleep(3)
r = subprocess.run(['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}', 'http://127.0.0.1:5000/'], capture_output=True, text=True)
print('Flask PID:', proc.pid, '| HTTP:', r.stdout)
print('=== TUDO PRONTO ===')

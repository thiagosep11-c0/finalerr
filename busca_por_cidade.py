#!/usr/bin/env python3
"""
Busca por Cidade - Grupos WhatsApp IA
Combina termos principais com cidades/bairros/estados + filtro por ano
"""
import asyncio, re, os, json, subprocess
from datetime import datetime
from urllib.parse import quote, unquote
from playwright.async_api import async_playwright

BASE_DIR   = '/root/grupos_ia'
CONFIG_FILE = os.path.join(BASE_DIR, 'busca_cidade_config.json')
LOG_FILE   = os.path.join(BASE_DIR, 'busca_cidade.log')
PAUSE_FILE = os.path.join(BASE_DIR, 'PAUSAR.txt')
STATUS_FILE = os.path.join(BASE_DIR, 'busca_cidade_status.json')
SAVE_DIR   = os.path.join(BASE_DIR, 'GRUPOS_CIDADE')

SCROLL_PAUSA = 0.4
TELEGRAM_TOKEN   = '8180469518:AAHkM-QhpMFfIxgpzxGMlqGe42oCfVy1A80'
TELEGRAM_CHAT_ID = '1035802788'

FILTROS_ANO = {
    '2026': 'eyJycF9jcmVhdGlvbl90aW1lOjAiOiJ7XCJuYW1lXCI6XCJjcmVhdGlvbl90aW1lXCIsXCJhcmdzXCI6XCJ7XFxcInN0YXJ0X3llYXJcXFwiOlxcXCIyMDI2XFxcIixcXFwic3RhcnRfbW9udGhcXFwiOlxcXCIyMDI2LTFcXFwiLFxcXCJlbmRfeWVhclxcXCI6XFxcIjIwMjZcXFwiLFxcXCJlbmRfbW9udGhcXFwiOlxcXCIyMDI2LTEyXFxcIixcXFwic3RhcnRfZGF5XFxcIjpcXFwiMjAyNi0xLTFcXFwiLFxcXCJlbmRfZGF5XFxcIjpcXFwiMjAyNi0xMi0zMVxcXCJ9XCJ9In0%3D',
    '2025': 'eyJycF9jcmVhdGlvbl90aW1lOjAiOiJ7XCJuYW1lXCI6XCJjcmVhdGlvbl90aW1lXCIsXCJhcmdzXCI6XCJ7XFxcInN0YXJ0X3llYXJcXFwiOlxcXCIyMDI1XFxcIixcXFwic3RhcnRfbW9udGhcXFwiOlxcXCIyMDI1LTFcXFwiLFxcXCJlbmRfeWVhclxcXCI6XFxcIjIwMjVcXFwiLFxcXCJlbmRfbW9udGhcXFwiOlxcXCIyMDI1LTEyXFxcIixcXFwic3RhcnRfZGF5XFxcIjpcXFwiMjAyNS0xLTFcXFwiLFxcXCJlbmRfZGF5XFxcIjpcXFwiMjAyNS0xMi0zMVxcXCJ9XCJ9In0%3D',
    '2024': 'eyJycF9jcmVhdGlvbl90aW1lOjAiOiJ7XCJuYW1lXCI6XCJjcmVhdGlvbl90aW1lXCIsXCJhcmdzXCI6XCJ7XFxcInN0YXJ0X3llYXJcXFwiOlxcXCIyMDI0XFxcIixcXFwic3RhcnRfbW9udGhcXFwiOlxcXCIyMDI0LTFcXFwiLFxcXCJlbmRfeWVhclxcXCI6XFxcIjIwMjRcXFwiLFxcXCJlbmRfbW9udGhcXFwiOlxcXCIyMDI0LTEyXFxcIixcXFwic3RhcnRfZGF5XFxcIjpcXFwiMjAyNC0xLTFcXFwiLFxcXCJlbmRfZGF5XFxcIjpcXFwiMjAyNC0xMi0zMVxcXCJ9XCJ9In0%3D',
    '2023': 'eyJycF9jcmVhdGlvbl90aW1lOjAiOiJ7XCJuYW1lXCI6XCJjcmVhdGlvbl90aW1lXCIsXCJhcmdzXCI6XCJ7XFxcInN0YXJ0X3llYXJcXFwiOlxcXCIyMDIzXFxcIixcXFwic3RhcnRfbW9udGhcXFwiOlxcXCIyMDIzLTFcXFwiLFxcXCJlbmRfeWVhclxcXCI6XFxcIjIwMjNcXFwiLFxcXCJlbmRfbW9udGhcXFwiOlxcXCIyMDIzLTEyXFxcIixcXFwic3RhcnRfZGF5XFxcIjpcXFwiMjAyMy0xLTFcXFwiLFxcXCJlbmRfZGF5XFxcIjpcXFwiMjAyMy0xMi0zMVxcXCJ9XCJ9In0%3D',
}

TODOS_TERMOS = [
    'vendas', 'venda', 'desapego', 'desapega', 'olx', 'trocas',
    'classificados', 'feira do rolo', 'brick', 'jardim', 'moradores',
    'vila', 'santo', 'santa', 'são', 'parque', 'bairro', 'doação',
    'brique', 'centro', 'condomínio', 'negócios', 'cidade', 'região',
    'serviços', 'permuta', 'bazar', 'gratuito', 'comércio', 'comunidade',
]


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linha = f'[{ts}] {msg}'
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(linha + '\n')
    print(linha, flush=True)


def salvar_status(status: dict):
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status, f, ensure_ascii=False)


def telegram(msg):
    import urllib.request
    url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
    data = json.dumps({'chat_id': TELEGRAM_CHAT_ID, 'text': msg, 'parse_mode': 'HTML'}).encode()
    try:
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log(f'Telegram erro: {e}')


async def verificar_pausa():
    if os.path.exists(PAUSE_FILE):
        log('*** PAUSADO ***')
        while os.path.exists(PAUSE_FILE):
            await asyncio.sleep(5)
        log('*** Retomando... ***')


def extrair_links(html: str) -> set:
    links = set()
    html = html.replace('\\/', '/')
    for encoded in re.findall(
        r'l\.facebook\.com/l\.php\?u=(https?%3A%2F%2Fchat\.whatsapp\.com%2F[A-Za-z0-9]+)', html):
        decoded = unquote(encoded)
        m = re.match(r'https://chat\.whatsapp\.com/([A-Za-z0-9]+)', decoded)
        if m:
            links.add(f'https://chat.whatsapp.com/{m.group(1)}')
    for codigo in re.findall(r'chat\.whatsapp\.com/([A-Za-z0-9]{10,})', html):
        links.add(f'https://chat.whatsapp.com/{codigo}')
    for codigo in re.findall(r'chat\.whatsapp\.com%2F([A-Za-z0-9]{10,})', html, re.IGNORECASE):
        links.add(f'https://chat.whatsapp.com/{codigo}')
    for codigo in re.findall(r'chat\.whatsapp\.com\\u00252F([A-Za-z0-9]{10,})', html):
        links.add(f'https://chat.whatsapp.com/{codigo}')
    for codigo in re.findall(r'chat\.whatsapp\.com\\u002F([A-Za-z0-9]{10,})', html):
        links.add(f'https://chat.whatsapp.com/{codigo}')
    return links


def carregar_existentes() -> set:
    links = set()
    os.makedirs(SAVE_DIR, exist_ok=True)
    save_file = os.path.join(SAVE_DIR, 'grupos_validos.txt')
    if not os.path.exists(save_file):
        return links
    with open(save_file, encoding='utf-8') as f:
        for linha in f:
            m = re.search(r'https://chat\.whatsapp\.com/[A-Za-z0-9]+', linha)
            if m:
                links.add(m.group())
    return links


def salvar_novos(items: list):
    save_file = os.path.join(SAVE_DIR, 'grupos_validos.txt')
    with open(save_file, 'a', encoding='utf-8') as f:
        for item in items:
            f.write(item + '\n')


async def clicar_ver_mais(page):
    try:
        btns = await page.locator('text="Ver mais"').all()
        for btn in btns[:8]:
            try:
                await btn.scroll_into_view_if_needed()
                await btn.dispatch_event('click')
                await page.wait_for_timeout(100)
            except Exception:
                pass
    except Exception:
        pass


async def buscar_facebook(page, query: str, filtro_ano: str, existentes: set) -> set:
    url = f'https://www.facebook.com/search/posts?q={quote(query)}&filters={filtro_ano}'
    encontrados = set()

    async def on_response(response):
        try:
            ct = response.headers.get('content-type', '')
            if 'json' in ct or 'javascript' in ct or 'text' in ct:
                corpo = await response.text()
                novos = extrair_links(corpo) - existentes
                if novos:
                    log(f'    [rede] +{len(novos)} via GraphQL')
                encontrados.update(novos)
        except Exception:
            pass

    page.on('response', on_response)
    try:
        log(f'    Buscando: {query}')
        await page.goto(url, timeout=30000, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)

        # Fase 1: desce até o fundo
        sem_crescimento = 0
        altura_ant = 0
        passos = 0
        while sem_crescimento < 3 and passos < 50:
            passos += 1
            await page.evaluate('''
                window.scrollBy(0, 900);
                let el = document.querySelector("[role=feed]") || document.scrollingElement;
                if (el) el.scrollBy(0, 900);
            ''')
            await page.keyboard.press('PageDown')
            await page.wait_for_timeout(int(SCROLL_PAUSA * 1000))
            await clicar_ver_mais(page)
            altura_nova = await page.evaluate('document.body.scrollHeight')
            html = await page.content()
            novos = extrair_links(html) - existentes
            if novos:
                log(f'    +{len(novos)} novos | total={len(encontrados | novos)}')
                for lk in novos:
                    log(f'      {lk}')
            encontrados |= novos
            if altura_nova == altura_ant:
                sem_crescimento += 1
            else:
                sem_crescimento = 0
            altura_ant = altura_nova

        # Fase 2: sobe coletando
        altura_total = await page.evaluate('document.body.scrollHeight')
        posicao = altura_total
        while posicao > 0:
            posicao = max(0, posicao - 700)
            await page.evaluate(f'window.scrollTo(0, {posicao});')
            await page.wait_for_timeout(int(SCROLL_PAUSA * 1000))
            await clicar_ver_mais(page)
            html = await page.content()
            novos = extrair_links(html) - existentes
            if novos:
                log(f'    +{len(novos)} novos | total={len(encontrados | novos)}')
                for lk in novos:
                    log(f'      {lk}')
            encontrados |= novos

        log(f'    {len(encontrados)} links encontrados na query')

    except Exception as e:
        log(f'  Erro na query "{query}": {e}')
    finally:
        try:
            page.remove_listener('response', on_response)
        except Exception:
            pass

    return encontrados


async def rodar():
    if not os.path.exists(CONFIG_FILE):
        log('ERRO: arquivo de config nao encontrado')
        return

    with open(CONFIG_FILE, encoding='utf-8') as f:
        cfg = json.load(f)

    cidades  = [c.strip() for c in cfg.get('cidades', []) if c.strip()]
    termos   = cfg.get('termos', TODOS_TERMOS)
    anos     = cfg.get('anos', ['2026'])
    sufixos  = cfg.get('sufixos', ['chat', '?mode'])

    if not cidades:
        log('ERRO: nenhuma cidade configurada')
        return

    total_queries = len(cidades) * len(termos) * len(anos) * len(sufixos)
    log(f'=== Busca por Cidade iniciada ===')
    log(f'Cidades: {len(cidades)} | Termos: {len(termos)} | Anos: {anos} | Sufixos: {sufixos}')
    log(f'Total de queries: {total_queries}')
    telegram(f'🏙️ <b>Busca por Cidade iniciada</b>\n{len(cidades)} cidades × {len(termos)} termos × {len(anos)} anos = {total_queries} queries')

    existentes = carregar_existentes()
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
    total_links = 0
    query_atual = 0

    salvar_status({'rodando': True, 'total': total_queries, 'atual': 0,
                   'cidade': '', 'termo': '', 'ano': '', 'links': 0})

    async with async_playwright() as pw:
        browser = await pw.chromium.connect_over_cdp('http://127.0.0.1:9222')
        ctx = browser.contexts[0]

        page = None
        for p in ctx.pages:
            if 'facebook.com' in p.url:
                page = p
                break
        if page is None:
            page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.bring_to_front()

        if 'login' in page.url or 'facebook.com' not in page.url:
            log('ERRO: nao esta logado no Facebook')
            await browser.close()
            return

        for ano in anos:
            filtro = FILTROS_ANO.get(str(ano), FILTROS_ANO['2026'])
            for cidade in cidades:
                for termo in termos:
                    for sufixo in sufixos:
                        await verificar_pausa()

                        query_atual += 1
                        q = f'{termo} "{cidade}" "{sufixo}"'
                        pct = int((query_atual / total_queries) * 100)

                        salvar_status({'rodando': True, 'total': total_queries,
                                       'atual': query_atual, 'pct': pct,
                                       'cidade': cidade, 'termo': termo,
                                       'ano': str(ano), 'sufixo': sufixo, 'links': total_links})

                        log(f'[{query_atual}/{total_queries}] {q} (ano {ano})')

                        novos = await buscar_facebook(page, q, filtro, existentes)
                        existentes |= novos
                        total_links += len(novos)

                        if novos:
                            linhas = [f'{data_hora} | [{termo.upper()}][{cidade}][{ano}] | NAO VERIFICADO | {lk}'
                                      for lk in novos]
                            salvar_novos(linhas)

                        await asyncio.sleep(1)

        await browser.close()

    salvar_status({'rodando': False, 'total': total_queries, 'atual': total_queries,
                   'pct': 100, 'links': total_links})

    log(f'=== Busca por Cidade concluida — {total_links} links encontrados ===')
    telegram(f'✅ <b>Busca por Cidade concluida</b>\n{total_links} links encontrados')


if __name__ == '__main__':
    asyncio.run(rodar())

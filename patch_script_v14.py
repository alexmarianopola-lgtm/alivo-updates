from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v14.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.28 - Busca simples de catálogo para pedidos como "Tem DOT 4?".
# Reproduz a lógica de uma pesquisa simples do Sankhya: expressão direta na Base Soma,
# sem exigir aplicação/chassi quando o item é uma especificação comercial.
anchor='''        part_words={\n'''
if anchor not in text:
    raise SystemExit('part_words anchor not found')

catalog_code=r'''        # Busca simples de catálogo (ex.: DOT 4 / DOT4 / DOT-4).
        # Usa prioritariamente mensagens do cliente para não confundir preços/respostas antigas do vendedor.
        simple_results=[]
        simple_query_label=""
        simple_source="\n".join(customer_messages[-10:]) if customer_messages else text
        simple_candidates=[]

        # Detecta expressões letra+número que funcionam como nome/especificação de produto.
        for mm in re.finditer(r"(?i)\b([a-z]{2,12})\s*[-./]?\s*(\d{1,4})\b",simple_source):
            a=mm.group(1).strip(); b=mm.group(2).strip()
            if a.lower() in {"ano","mod","modelo","cod","codigo","soma","r","rs","qtd","qtde"}:
                continue
            label=(a+" "+b).upper()
            compact=re.sub(r"[^A-Z0-9]","",label)
            if len(compact)>=4 and label not in simple_candidates:
                simple_candidates.append(label)

        if not priority_soma_codes:
            for label in simple_candidates[:8]:
                compact=re.sub(r"[^A-Z0-9]","",label.upper())
                # Se a frase já fala explicitamente de veículo/aplicação, deixa a lógica técnica normal decidir.
                if re.search(r"(?i)\b(?:ano|modelo|mod|chassi|placa|motor)\b",simple_source):
                    continue
                try:
                    con=sqlite3.connect(DB_PATH); cur=con.cursor()
                    expr_desc="REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(descricao,'')),' ',''),'-',''),'.',''),'/','')"
                    expr_comp="REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(compldesc,'')),' ',''),'-',''),'.',''),'/','')"
                    expr_ref="REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(refforn,'')),' ',''),'-',''),'.',''),'/','')"
                    expr_marca="REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(marca,'')),' ',''),'-',''),'.',''),'/','')"
                    sql=("SELECT id,codprod,refforn,marca,descricao,compldesc,88 AS score FROM produtos WHERE "
                         +expr_desc+" LIKE ? OR "+expr_comp+" LIKE ? OR "+expr_ref+" LIKE ? OR "+expr_marca+
                         " LIKE ? ORDER BY CAST(COALESCE(codprod,'0') AS INTEGER), codprod LIMIT 40")
                    like="%"+compact+"%"
                    rows=cur.execute(sql,(like,like,like,like)).fetchall()
                    con.close()
                    if rows:
                        seen_simple=set()
                        for r in rows:
                            if r[0] not in seen_simple:
                                seen_simple.add(r[0]); simple_results.append(r)
                        simple_query_label=label
                        break
                except Exception:
                    simple_results=[]
'''
text=text.replace(anchor,catalog_code+anchor,1)

# Não reabre busca vaga de uma palavra se o catálogo já respondeu.
text=text.replace(
    'if not exact and not fuzzy and parts and not priority_soma_codes:',
    'if not exact and not fuzzy and not simple_results and parts and not priority_soma_codes:',
    1
)

# Depois que a busca fuzzy normal rodar, uma resposta simples de catálogo tem prioridade e elimina ruído.
priority_anchor='''        if priority_soma_codes and exact:\n            fuzzy=[]\n            fuzzy_seen=set()\n'''
if priority_anchor in text:
    text=text.replace(priority_anchor,
'''        if simple_results or (priority_soma_codes and exact):\n            fuzzy=[]\n            fuzzy_seen=set()\n''',1)
else:
    raise SystemExit('priority fuzzy anchor not found')

# Busca de catálogo não precisa pedir ano/chassi.
html_anchor='''        # Painel visual de cotação: produtos primeiro, contexto depois.\n'''
if html_anchor not in text:
    raise SystemExit('visual panel anchor not found')
text=text.replace(html_anchor,
'''        if simple_results:\n            missing=[]\n\n'''+html_anchor,1)

# Resumo superior.
old_summary='''            f'<span style="color:#047857;"><b>{len(exact)}</b> correspondência(s) direta(s)</span>'\n            f' &nbsp; <span style="color:#B45309;"><b>{len(fuzzy)}</b> possibilidade(s)</span>'\n'''
if old_summary not in text:
    raise SystemExit('visual summary anchor not found')
text=text.replace(old_summary,
'''            f'<span style="color:#047857;"><b>{len(exact)}</b> correspondência(s) direta(s)</span>'\n            f' &nbsp; <span style="color:#1D4ED8;"><b>{len(simple_results)}</b> resultado(s) de catálogo</span>'\n            f' &nbsp; <span style="color:#B45309;"><b>{len(fuzzy)}</b> possibilidade(s)</span>'\n''',1)

# Cards azuis de catálogo antes das possibilidades amarelas.
fuzzy_anchor='''        if fuzzy:\n            cards.append('<div class="section">🟡 POSSIBILIDADES — CONFIRMAR APLICAÇÃO</div>')\n'''
if fuzzy_anchor not in text:
    raise SystemExit('fuzzy visual anchor not found')
simple_visual=r'''        if simple_results:
            cards.append('<div class="section">🔵 RESULTADOS DA BASE SOMA — BUSCA '+_esc(simple_query_label or 'SIMPLES')+'</div>')
            for r in simple_results[:30]:
                soma=_esc(r[1]); ref=_esc(r[2] or '-'); marca=_esc(r[3] or '-')
                desc=_esc(str(r[4] or '')[:220]); comp=_esc(str(r[5] or '')[:180])
                cards.append(
                    '<table width="100%" cellspacing="0" cellpadding="7" '
                    'style="margin-bottom:6px;background:#EFF6FF;border:1px solid #93C5FD;">'
                    '<tr><td>'
                    f'<span style="font-size:15px;color:#1D4ED8;"><b>Soma {soma}</b></span>'
                    f' &nbsp; <span class="ref">REF. {ref}</span><br>'
                    f'<span class="muted"><b>Marca:</b> {marca}</span><br>'
                    f'<span class="desc"><b>{desc}</b></span>'
                    + (f'<br><span class="muted">{comp}</span>' if comp and comp!='-' else '') +
                    '</td></tr></table>'
                )
            if len(simple_results)>30:
                cards.append(f'<div class="muted">+ {len(simple_results)-30} resultado(s) adicionais.</div>')

'''
text=text.replace(fuzzy_anchor,simple_visual+fuzzy_anchor,1)

# Não mostra mensagem de base vazia se houve resultado simples.
text=text.replace('if not exact and not fuzzy:', 'if not exact and not fuzzy and not simple_results:',1)

old_status='''        self.status.setText(f"✅ {len(exact)} direta(s) • {len(fuzzy)} possibilidade(s) — produtos organizados para cotação.")'''
if old_status in text:
    text=text.replace(old_status,
'''        self.status.setText(f"✅ {len(exact)} direta(s) • {len(simple_results)} catálogo • {len(fuzzy)} possibilidade(s) — produtos organizados para cotação.")''',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched simple catalog search',version)

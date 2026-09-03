from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v8.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.22 - Assistente Técnico com apresentação visual para cotação.
# Não altera captura do WhatsApp nem lógica de busca; troca somente a renderização final.
old='''        self.result.setPlainText("\\n".join(lines))
        self.status.setText(f"✅ Pedido analisado • {len(exact)} correspondência(s) direta(s) • {len(fuzzy)} possibilidade(s).")'''
if old not in text:
    raise SystemExit('technical plain renderer not found')

new=r'''        # Painel visual de cotação: produtos primeiro, contexto depois.
        import html as _html
        def _esc(value):
            return _html.escape(str(value or ""))

        cards=[]
        cards.append("""
        <style>
          body { font-family: 'Segoe UI', Arial, sans-serif; color:#0F172A; font-size:12px; }
          .section { margin-top:10px; margin-bottom:5px; font-size:13px; font-weight:700; color:#0B2940; }
          .muted { color:#64748B; font-size:10px; }
          .ref { color:#0F4C5C; font-weight:700; }
          .desc { color:#1E293B; font-size:11px; }
        </style>
        """)

        # Resumo no topo.
        cards.append(
            '<table width="100%" cellspacing="0" cellpadding="7" '
            'style="background:#F1F5F9;border:1px solid #CBD5E1;">'
            '<tr><td><b style="font-size:14px;color:#0B2940;">COTAÇÃO — RESULTADOS</b><br>'
            f'<span style="color:#047857;"><b>{len(exact)}</b> correspondência(s) direta(s)</span>'
            f' &nbsp; <span style="color:#B45309;"><b>{len(fuzzy)}</b> possibilidade(s)</span>'
            '</td></tr></table><br>'
        )

        if codes:
            refs=[]
            for c in codes[:14]:
                key=re.sub(r"[^A-Z0-9]","",str(c).upper())
                raw=str(c)
                shown=raw if raw.upper()==key else f"{raw} → {key}"
                refs.append('<b>'+_esc(shown)+'</b>')
            cards.append('<div class="section">🔎 REFERÊNCIAS DETECTADAS</div>')
            cards.append('<div style="background:#EFF6FF;border:1px solid #BFDBFE;padding:6px;">'+' &nbsp; • &nbsp; '.join(refs)+'</div>')

        if exact:
            cards.append('<div class="section">🟢 CORRESPONDÊNCIAS DIRETAS</div>')
            for r in exact[:30]:
                soma=_esc(r[1])
                ref=_esc(r[2] or '-')
                marca=_esc(r[3] or '-')
                desc=_esc(str(r[4] or '')[:220])
                cards.append(
                    '<table width="100%" cellspacing="0" cellpadding="7" '
                    'style="margin-bottom:6px;background:#ECFDF5;border:1px solid #A7F3D0;">'
                    '<tr><td>'
                    f'<span style="font-size:15px;color:#065F46;"><b>Soma {soma}</b></span>'
                    f' &nbsp; <span class="ref">REF. {ref}</span><br>'
                    f'<span class="muted"><b>Marca:</b> {marca}</span><br>'
                    f'<span class="desc"><b>{desc}</b></span>'
                    '</td></tr></table>'
                )
            if len(exact)>30:
                cards.append(f'<div class="muted">+ {len(exact)-30} correspondência(s) direta(s) adicionais.</div>')

        if fuzzy:
            cards.append('<div class="section">🟡 POSSIBILIDADES — CONFIRMAR APLICAÇÃO</div>')
            for r,pair in fuzzy[:12]:
                soma=_esc(r[1])
                ref=_esc(r[2] or '-')
                marca=_esc(r[3] or '-')
                desc=_esc(str(r[4] or '')[:220])
                termo=_esc(' + '.join(str(x) for x in pair))
                cards.append(
                    '<table width="100%" cellspacing="0" cellpadding="7" '
                    'style="margin-bottom:6px;background:#FFFBEB;border:1px solid #FDE68A;">'
                    '<tr><td>'
                    f'<span style="font-size:14px;color:#92400E;"><b>Soma {soma}</b></span>'
                    f' &nbsp; <span class="ref">REF. {ref}</span><br>'
                    f'<span class="muted"><b>Marca:</b> {marca} &nbsp; | &nbsp; busca: {termo}</span><br>'
                    f'<span class="desc">{desc}</span>'
                    '</td></tr></table>'
                )
            if len(fuzzy)>12:
                cards.append(f'<div class="muted">+ {len(fuzzy)-12} possibilidade(s) adicionais.</div>')

        if not exact and not fuzzy:
            cards.append('<div class="section">BASE SOMA</div>')
            cards.append('<div style="background:#F8FAFC;border:1px solid #CBD5E1;padding:7px;">Nenhum produto útil encontrado com os dados atuais.</div>')

        if missing:
            cards.append('<div class="section">⚠️ PARA CONFIRMAR</div>')
            cards.append('<div style="background:#FFF7ED;border:1px solid #FED7AA;padding:7px;">' +
                         '<br>'.join('• '+_esc(x) for x in missing) + '</div>')

        # Pedido capturado fica no fim, como contexto, sem competir com a cotação.
        if messages:
            cards.append('<div class="section">💬 PEDIDO LIDO</div>')
            msg_html=[]
            for m in messages[-10:]:
                msg_html.append('• '+_esc(str(m)[:500]))
            cards.append('<div style="background:#F8FAFC;border:1px solid #E2E8F0;padding:7px;color:#475569;font-size:10px;">'
                         + '<br>'.join(msg_html) + '</div>')

        self.result.setHtml(''.join(cards))
        self.status.setText(f"✅ {len(exact)} direta(s) • {len(fuzzy)} possibilidade(s) — produtos organizados para cotação.")'''

text=text.replace(old,new,1)
ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched visual technical quotation panel',version)

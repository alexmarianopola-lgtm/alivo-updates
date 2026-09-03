from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v9.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.23 - Cotação contextual: lê cliente + vendedor sob clique e dá prioridade
# absoluta a código Soma informado pelo vendedor (ex.: cod6387 / cod soma 7910).
# Sem observer, timer ou monitoramento contínuo do WhatsApp.
pattern=r'(?s)    def _technical_analyze_current\(self\):.*?\n    def _technical_receive_current\(self,result\):'
match=re.search(pattern,text)
if not match:
    raise SystemExit('technical analyze method not found')

replacement='''    def _technical_analyze_current(self):
        try:
            self.technical_panel.set_loading()
        except Exception:
            pass
        js=r"""
        (() => {
          try{
            const main=document.querySelector('#main') || document.querySelector('[data-testid="conversation-panel-wrapper"]');
            if(!main) return {ok:false,error:'Abra uma conversa no WhatsApp antes de analisar.'};

            let name='';
            const h=main.querySelector('header [data-testid="conversation-info-header-chat-title"]') ||
                    main.querySelector('header span[title]') || main.querySelector('header [title]');
            if(h) name=(h.getAttribute('title')||h.textContent||'').trim();

            const mainRect=main.getBoundingClientRect();
            const midX=mainRect.left+(mainRect.width*0.50);
            const context=[];
            const seen=new Set();
            const clean=(t) => String(t||'').replace(/\\s+/g,' ').trim();

            const sideOf=(el) => {
              if(!el) return 'customer';
              let r=el.getBoundingClientRect();
              let holder=el;
              for(let i=0; i<5 && (!r || r.width<2); i++){
                holder=holder.parentElement;
                if(!holder) break;
                r=holder.getBoundingClientRect();
              }
              if(!r || r.width<2) return 'customer';
              const cx=(r.left+r.right)/2;
              return cx >= midX ? 'seller' : 'customer';
            };

            const push=(side,t) => {
              t=clean(t);
              if(!t || t.length<2) return;
              const key=side+'|'+t;
              if(seen.has(key)) return;
              seen.add(key);
              context.push({side:side,text:t.slice(0,1400)});
            };

            // Principal: blocos semânticos na ordem em que aparecem na conversa.
            const plain=Array.from(main.querySelectorAll('[data-pre-plain-text]'));
            for(const block of plain){
              const parts=[];
              const nodes=Array.from(block.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
              if(nodes.length){
                for(const n of nodes){
                  const t=clean(n.innerText||n.textContent||'');
                  if(t && !parts.includes(t)) parts.push(t);
                }
              }else{
                const t=clean(block.innerText||block.textContent||'');
                if(t) parts.push(t);
              }
              if(parts.length) push(sideOf(block),parts.join(' '));
            }

            // Compatibilidade com layouts antigos caso data-pre-plain-text não esteja presente.
            if(!context.length){
              for(const bubble of Array.from(main.querySelectorAll('div.message-in, div.message-out')).slice(-40)){
                const side=bubble.classList.contains('message-out') ? 'seller' : 'customer';
                const parts=[];
                for(const n of Array.from(bubble.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'))){
                  const t=clean(n.innerText||n.textContent||'');
                  if(t && !parts.includes(t)) parts.push(t);
                }
                if(parts.length) push(side,parts.join(' '));
              }
            }

            if(!context.length){
              return {ok:false,error:'Não consegui localizar mensagens de texto nesta conversa.'};
            }

            const recent=context.slice(-20);
            return {
              ok:true,
              name:name||'Cliente',
              context:recent,
              messages:recent.map(x => (x.side==='seller'?'Você: ':'Cliente: ')+x.text),
              customer_messages:recent.filter(x=>x.side==='customer').map(x=>x.text),
              seller_messages:recent.filter(x=>x.side==='seller').map(x=>x.text),
              capture_mode:'both-sides-recent'
            };
          }catch(e){
            return {ok:false,error:String(e&&e.message||e)};
          }
        })()
        """
        try:
            self.web.page().runJavaScript(js,self._technical_receive_current)
        except Exception as e:
            self.technical_panel.render_error(str(e))

    def _technical_receive_current(self,result):'''
text=text[:match.start()]+replacement+text[match.end():]

# Render/análise: usa texto dos dois lados, mas identifica código Soma digitado pelo vendedor.
old='''        name=str(data.get("name") or "Cliente")
        messages=[str(x).strip() for x in (data.get("messages") or []) if str(x).strip()]
        text="\\n".join(messages[-10:]).strip()
        if not text:
            self.render_error("Não encontrei mensagem de texto recebida nesta conversa.")
            return
'''
if old not in text:
    # Compatibilidade caso a base ainda esteja no slice antigo.
    old='''        name=str(data.get("name") or "Cliente")
        messages=[str(x).strip() for x in (data.get("messages") or []) if str(x).strip()]
        text="\\n".join(messages[-5:]).strip()
        if not text:
            self.render_error("Não encontrei mensagem de texto recebida nesta conversa.")
            return
'''
if old not in text:
    raise SystemExit('technical render header not found')

new='''        name=str(data.get("name") or "Cliente")
        messages=[str(x).strip() for x in (data.get("messages") or []) if str(x).strip()]
        customer_messages=[str(x).strip() for x in (data.get("customer_messages") or []) if str(x).strip()]
        seller_messages=[str(x).strip() for x in (data.get("seller_messages") or []) if str(x).strip()]
        raw_context=[]
        for item in (data.get("context") or []):
            if isinstance(item,dict) and str(item.get("text") or "").strip():
                raw_context.append(str(item.get("text") or "").strip())
        if not raw_context:
            raw_context=[x.split(": ",1)[-1] for x in messages]
        text="\\n".join(raw_context[-16:]).strip()
        seller_text="\\n".join(seller_messages[-12:]).strip()
        if not text:
            self.render_error("Não encontrei mensagens de texto nesta conversa.")
            return

        # Código Soma informado por VOCÊ tem prioridade máxima para cotação.
        priority_soma_codes=[]
        for mm in re.finditer(r"(?i)\\b(?:cod(?:igo)?(?:\\s+soma)?|soma)\\s*[:#.-]?\\s*(\\d{2,8})\\b",seller_text):
            c=mm.group(1)
            if c not in priority_soma_codes:
                priority_soma_codes.append(c)
        # Forma muito comum no balcão: cod6387
        for mm in re.finditer(r"(?i)\\bcod(\\d{2,8})\\b",seller_text):
            c=mm.group(1)
            if c not in priority_soma_codes:
                priority_soma_codes.append(c)
'''
text=text.replace(old,new,1)

# Injeta busca direta pelo CODPROD antes da busca geral por referências.
needle='''        exact=[]
        if codes:
'''
if needle not in text:
    raise SystemExit('exact block anchor not found')
priority_block='''        exact=[]
        if priority_soma_codes:
            try:
                con=sqlite3.connect(DB_PATH); cur=con.cursor(); seen_priority=set()
                for scode in priority_soma_codes[:6]:
                    nq=norm(scode)
                    rows=cur.execute("""
                        SELECT id,codprod,refforn,marca,descricao,compldesc,110 AS score
                        FROM produtos
                        WHERE codprod=? OR n_codprod=?
                        ORDER BY CASE WHEN codprod=? THEN 0 ELSE 1 END
                        LIMIT 6
                    """,(scode,nq,scode)).fetchall()
                    for r in rows:
                        if r[0] not in seen_priority:
                            seen_priority.add(r[0]); exact.append(r)
                con.close()
            except Exception:
                pass

        # Se você já informou o código Soma, não misturamos outras referências na prioridade.
        if codes and not priority_soma_codes:
'''
text=text.replace(needle,priority_block,1)

# Quando o código Soma digitado por você foi encontrado, elimina sugestões vagas.
anchor='''        # Fallback controlado: uma palavra de peça, ainda sempre como possibilidade.'''
if anchor not in text:
    raise SystemExit('fuzzy fallback anchor not found')
text=text.replace(anchor,'''        if priority_soma_codes and exact:
            fuzzy=[]
            fuzzy_seen=set()

        # Fallback controlado: uma palavra de peça, ainda sempre como possibilidade.''',1)

# O fallback por uma palavra não deve reabrir ruído se já há código Soma confirmado.
text=text.replace('''        if not exact and not fuzzy and parts:''','''        if not exact and not fuzzy and parts and not priority_soma_codes:''',1)

# Painel visual: mostra o código informado por você no topo.
visual_anchor='''        if codes:
            refs=[]
'''
if visual_anchor not in text:
    raise SystemExit('visual refs anchor not found')
text=text.replace(visual_anchor,'''        if priority_soma_codes:
            cards.append('<div class="section">🎯 CÓDIGO INFORMADO POR VOCÊ</div>')
            cards.append('<div style="background:#DCFCE7;border:2px solid #22C55E;padding:8px;font-size:15px;color:#14532D;">'
                         + ' &nbsp; '.join('<b>Soma '+_esc(c)+'</b>' for c in priority_soma_codes[:6]) + '</div>')

        if codes:
            refs=[]
''',1)

# Ajusta textos do painel para contexto dos dois lados.
text=text.replace('Lendo as últimas mensagens recebidas da conversa e consultando a Base Soma...',
                  'Lendo o contexto recente do cliente e suas respostas, depois consultando a Base Soma...')
text=text.replace('Lendo as mensagens recentes do atendimento aberto e consultando a Base Soma...',
                  'Lendo o contexto recente do cliente e suas respostas, depois consultando a Base Soma...')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched quotation context and seller Soma priority',version)

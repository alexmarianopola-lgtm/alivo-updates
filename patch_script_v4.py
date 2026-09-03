from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v4.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.17: Assistente Técnico lê APENAS as mensagens recebidas que estão
# realmente visíveis no viewport da conversa aberta. Nenhum timer/observer WA.
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
            const h=main.querySelector('header span[title]') || main.querySelector('header [title]');
            if(h) name=(h.getAttribute('title')||h.textContent||'').trim();

            const mainRect=main.getBoundingClientRect();
            const header=main.querySelector('header');
            const footer=main.querySelector('footer');
            const headerRect=header ? header.getBoundingClientRect() : null;
            const footerRect=footer ? footer.getBoundingClientRect() : null;
            const visibleTop=Math.max(0, mainRect.top, headerRect ? headerRect.bottom : mainRect.top);
            const visibleBottom=Math.min(window.innerHeight, mainRect.bottom, footerRect ? footerRect.top : mainRect.bottom);

            const isVisible=(el) => {
              if(!el) return false;
              const r=el.getBoundingClientRect();
              if(!r || r.width<2 || r.height<2) return false;
              const st=window.getComputedStyle(el);
              if(st.display==='none' || st.visibility==='hidden' || parseFloat(st.opacity||'1')===0) return false;
              const overlap=Math.min(r.bottom,visibleBottom)-Math.max(r.top,visibleTop);
              return overlap>Math.min(8,Math.max(2,r.height*0.20));
            };

            const messages=[];
            const pushText=(t) => {
              t=String(t||'').replace(/\\s+/g,' ').trim();
              if(!t || t.length<2) return;
              if(messages.length && messages[messages.length-1]===t) return;
              messages.push(t.slice(0,1200));
            };

            // Somente bolhas RECEBIDAS que intersectam a parte visível da conversa.
            const inbound=Array.from(main.querySelectorAll('div.message-in')).filter(isVisible);
            for(const bubble of inbound){
              const parts=[];
              const nodes=Array.from(bubble.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
              for(const n of nodes){
                const t=(n.innerText||n.textContent||'').replace(/\\s+/g,' ').trim();
                if(t && !parts.includes(t)) parts.push(t);
              }
              if(parts.length) pushText(parts.join(' '));
            }

            // Fallback somente visível, caso a classe message-in mude no WhatsApp.
            if(!messages.length){
              const candidates=Array.from(main.querySelectorAll('[data-pre-plain-text]')).filter(isVisible);
              for(const c of candidates){
                const parent=c.closest('.message-in');
                if(parent && !isVisible(parent)) continue;
                if(!parent) continue; // não mistura mensagens enviadas por nós
                const n=c.querySelector('span.selectable-text') || c;
                pushText(n.innerText||n.textContent||'');
              }
            }

            if(!messages.length){
              return {ok:false,error:'Não encontrei mensagem recebida visível. Role a conversa até o pedido e clique novamente.'};
            }
            return {ok:true,name:name||'Cliente',messages:messages.slice(-12),visible_only:true};
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

# O painel passa a analisar até 10 mensagens visíveis, em vez de somente 5.
old='text="\\n".join(messages[-5:]).strip()'
new='text="\\n".join(messages[-10:]).strip()'
if old not in text:
    raise SystemExit('technical payload message slice not found')
text=text.replace(old,new,1)

old='for m in messages[-5:]:'
new='for m in messages[-10:]:'
if old not in text:
    raise SystemExit('technical payload render slice not found')
text=text.replace(old,new,1)

text=text.replace('lines=["PEDIDO CAPTURADO",f"Cliente: {name},""]' if False else 'lines=["PEDIDO CAPTURADO",f"Cliente: {name}",""]',
                  'lines=["PEDIDO CAPTURADO — SOMENTE MENSAGENS VISÍVEIS",f"Cliente: {name}",""]',1)
text=text.replace('Clique em Ler conversa para analisar somente o atendimento aberto.',
                  'Mostre na tela o trecho do pedido e clique em Ler conversa.',1)
text=text.replace('Lendo somente a conversa aberta e consultando a Base Soma...',
                  'Lendo somente as mensagens visíveis na tela e consultando a Base Soma...',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched visible-only technical assistant',version)

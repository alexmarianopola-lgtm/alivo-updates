from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v6.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.19 - Corrige filtro de mensagens visíveis do Assistente Técnico.
# A versão anterior calculava limites usando header/footer do DOM do WhatsApp e,
# em alguns layouts, terminava com uma faixa visível inválida. Agora usamos
# diretamente o viewport real do WebView2. Continua sendo leitura SOMENTE SOB CLIQUE.
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

            // Visibilidade simples e robusta: a bolha precisa intersectar o viewport
            // real do WebView. Não depende da estrutura interna de header/footer.
            const vw=Math.max(document.documentElement.clientWidth||0, window.innerWidth||0);
            const vh=Math.max(document.documentElement.clientHeight||0, window.innerHeight||0);
            const isVisible=(el) => {
              if(!el) return false;
              const r=el.getBoundingClientRect();
              if(!r || r.width<2 || r.height<2) return false;
              return r.bottom>55 && r.top<(vh-55) && r.right>0 && r.left<vw;
            };

            const messages=[];
            const pushText=(t) => {
              t=String(t||'').replace(/\\s+/g,' ').trim();
              if(!t || t.length<2) return;
              if(messages.length && messages[messages.length-1]===t) return;
              messages.push(t.slice(0,1200));
            };

            // Somente mensagens RECEBIDAS que estão na parte atualmente visível.
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

            // Fallback para mudanças de seletor, ainda exigindo elemento visível e recebido.
            if(!messages.length){
              const candidates=Array.from(main.querySelectorAll('[data-pre-plain-text]'));
              for(const c of candidates){
                const parent=c.closest('.message-in');
                if(!parent || !isVisible(parent)) continue;
                const n=c.querySelector('span.selectable-text') || c;
                pushText(n.innerText||n.textContent||'');
              }
            }

            if(!messages.length){
              return {ok:false,error:'Não encontrei mensagem recebida visível. Deixe o pedido aparecendo na tela e clique novamente.'};
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

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched visible viewport technical assistant',version)

from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v6.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.21 - Captura estável independente da classe message-in.
# O WhatsApp muda classes internas entre conversas/layouts. Agora usamos os blocos
# de mensagem com data-pre-plain-text e classificamos cliente x vendedor pela
# posição horizontal: mensagens recebidas ficam à esquerda, enviadas à direita.
# Continua SEM observer/timer: uma leitura somente quando o usuário clica.
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
            const midX=mainRect.left+(mainRect.width*0.50);
            const messages=[];
            const seen=new Set();

            const clean=(t) => String(t||'').replace(/\\s+/g,' ').trim();
            const pushText=(t) => {
              t=clean(t);
              if(!t || t.length<2 || seen.has(t)) return;
              seen.add(t);
              messages.push(t.slice(0,1200));
            };
            const isLeftSide=(el) => {
              if(!el) return false;
              let r=el.getBoundingClientRect();
              if((!r || r.width<1) && el.parentElement) r=el.parentElement.getBoundingClientRect();
              if(!r || r.width<1) return false;
              const cx=(r.left+r.right)/2;
              return cx < midX;
            };

            // Principal: estrutura semântica da mensagem. Não depende de message-in.
            const plain=Array.from(main.querySelectorAll('[data-pre-plain-text]'));
            for(const block of plain){
              if(!isLeftSide(block)) continue;
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
              if(parts.length) pushText(parts.join(' '));
            }

            // Compatibilidade com layouts que ainda usam message-in.
            if(!messages.length){
              const inbound=Array.from(main.querySelectorAll('div.message-in'));
              for(const bubble of inbound.slice(-30)){
                const parts=[];
                const nodes=Array.from(bubble.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
                for(const n of nodes){
                  const t=clean(n.innerText||n.textContent||'');
                  if(t && !parts.includes(t)) parts.push(t);
                }
                if(parts.length) pushText(parts.join(' '));
              }
            }

            // Último fallback: textos selecionáveis do lado esquerdo da conversa.
            if(!messages.length){
              const nodes=Array.from(main.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
              for(const n of nodes){
                if(n.closest('header') || n.closest('footer')) continue;
                if(!isLeftSide(n)) continue;
                pushText(n.innerText||n.textContent||'');
              }
            }

            if(!messages.length){
              return {
                ok:false,
                error:'Não consegui localizar texto recebido nesta conversa. Diagnóstico: blocos='+plain.length+'.',
                debug:{plain:plain.length,selectable:main.querySelectorAll('span.selectable-text').length}
              };
            }
            return {
              ok:true,
              name:name||'Cliente',
              messages:messages.slice(-12),
              capture_mode:'left-side',
              debug:{plain:plain.length,total:messages.length}
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

# Atualiza os textos do painel para não prometer filtro geométrico de viewport.
text=text.replace('Lendo somente as mensagens visíveis na tela e consultando a Base Soma...',
                  'Lendo as mensagens recentes do atendimento aberto e consultando a Base Soma...')
text=text.replace('PEDIDO CAPTURADO — SOMENTE MENSAGENS VISÍVEIS',
                  'PEDIDO CAPTURADO — ATENDIMENTO ABERTO')
text=text.replace('Mostre na tela o trecho do pedido e clique em Ler conversa.',
                  'Abra a conversa do cliente e clique em Ler conversa.')

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched left-side technical capture',version)

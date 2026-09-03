from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v7.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# v0.22.20 - Volta ao mecanismo de captura que funcionou na v0.22.16.
# Sem getBoundingClientRect/viewport. O WhatsApp/WebView2 mantém apenas um conjunto
# limitado de bolhas carregadas no DOM; pegamos as últimas recebidas sob clique.
# Mantemos as melhorias posteriores: até 10 mensagens no painel e referências flexíveis.
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

            const messages=[];
            const pushText=(t) => {
              t=String(t||'').replace(/\\s+/g,' ').trim();
              if(!t || t.length<2) return;
              if(messages.length && messages[messages.length-1]===t) return;
              messages.push(t.slice(0,1200));
            };

            // MESMO PRINCÍPIO DA PRIMEIRA VERSÃO QUE FUNCIONOU:
            // lê somente mensagens RECEBIDAS carregadas na conversa e pega as últimas.
            const inbound=Array.from(main.querySelectorAll('div.message-in'));
            for(const bubble of inbound.slice(-20)){
              const parts=[];
              const nodes=Array.from(bubble.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
              for(const n of nodes){
                const t=(n.innerText||n.textContent||'').replace(/\\s+/g,' ').trim();
                if(t && !parts.includes(t)) parts.push(t);
              }
              if(parts.length) pushText(parts.join(' '));
            }

            // Fallback da primeira versão para mudanças de seletor do WhatsApp.
            if(!messages.length){
              const candidates=Array.from(main.querySelectorAll('[data-pre-plain-text]')).slice(-30);
              for(const c of candidates){
                const parent=c.closest('.message-in');
                if(inbound.length && !parent) continue;
                if(!parent) continue;
                const n=c.querySelector('span.selectable-text') || c;
                pushText(n.innerText||n.textContent||'');
              }
            }

            if(!messages.length){
              return {ok:false,error:'Não encontrei mensagem de texto recebida nesta conversa. Abra o pedido e tente novamente.'};
            }
            return {ok:true,name:name||'Cliente',messages:messages.slice(-12),capture_mode:'last_loaded_inbound'};
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

# Corrige os textos da UI: não prometemos mais filtro geométrico de viewport.
text=text.replace('Lendo somente as mensagens visíveis na tela e consultando a Base Soma...',
                  'Lendo as últimas mensagens recebidas da conversa e consultando a Base Soma...',1)
text=text.replace('PEDIDO CAPTURADO — SOMENTE MENSAGENS VISÍVEIS',
                  'PEDIDO CAPTURADO — ÚLTIMAS MENSAGENS RECEBIDAS',1)
text=text.replace('Mostre na tela o trecho do pedido e clique em Ler conversa.',
                  'Abra a conversa no trecho do pedido e clique em Ler conversa.',1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched stable technical capture',version)

from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v3.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# Preserve capture log across page navigations/reinjections.
text=text.replace('save([]); log("capture_start",{title:document.title||""});','if(!read().length){ save([]); log("capture_start",{title:document.title||""}); }')

# Start a short-lived rearm loop while diagnostic mode is active.
old='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)'''
new='''    def _catalog_capture_start(self):\n        browser=self._get_catalog_window(False)\n        browser._capture_started=True\n        browser._capture_rounds=0'''
if old in text:
    text=text.replace(old,new,1)

needle='''        browser.start_network_capture(started)'''
replacement='''        browser.start_network_capture(started)\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))'''
if needle in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(needle,replacement,1)

marker='''    def _catalog_capture_read(self,browser):'''
method='''    def _catalog_capture_keepalive(self,browser):\n        try:\n            if not getattr(browser,"_capture_started",False):\n                return\n            browser._capture_rounds=int(getattr(browser,"_capture_rounds",0))+1\n            if browser._capture_rounds>140:\n                browser._capture_started=False\n                return\n            browser.start_network_capture()\n        except Exception:\n            pass\n        QTimer.singleShot(300,lambda b=browser:self._catalog_capture_keepalive(b))\n\n'''
if marker in text and '_catalog_capture_keepalive' not in text:
    text=text.replace(marker,method+marker,1)

oldline='''            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
newline='''            if any("gateway/graphql" in str(x) for x in lines):\n                lines.insert(4,"PISTA: endpoint GraphQL detectado: https://bff.catalogofraga.com.br/gateway/graphql")\n                self.plate_panel.capture.setPlainText("\\n".join(lines))\n            if useful: self.plate_panel.status.setText(f"✅ Diagnóstico capturou {useful} chamada(s).")'''
if oldline in text:
    text=text.replace(oldline,newline,1)

# Accept file downloads created by ChatGPT/Copiloto inside QWebEngine.
if '_aliyvo_install_download_hooks' not in text:
    hook = r'''
# --- ALIYVO: downloads do Copiloto/ChatGPT ---
def _aliyvo_handle_web_download(download):
    try:
        import os as _os
        from pathlib import Path as _Path
        folder = _Path.home() / "Downloads"
        folder.mkdir(parents=True, exist_ok=True)
        try:
            name = str(download.downloadFileName() or "arquivo")
        except Exception:
            name = "arquivo"
        name = _os.path.basename(name).strip() or "arquivo"
        base, ext = _os.path.splitext(name)
        candidate = folder / name
        n = 2
        while candidate.exists():
            candidate = folder / f"{base} ({n}){ext}"
            n += 1
        download.setDownloadDirectory(str(folder))
        download.setDownloadFileName(candidate.name)
        download.accept()
    except Exception:
        try:
            download.accept()
        except Exception:
            pass

def _aliyvo_install_download_hooks():
    try:
        _app = QApplication.instance()
        if _app is None:
            return
        for _w in _app.allWidgets():
            try:
                _page = _w.page()
                if _page is None:
                    continue
                _profile = _page.profile()
                if _profile is None or bool(_profile.property("ALIYVO_DOWNLOAD_HOOK")):
                    continue
                _profile.downloadRequested.connect(_aliyvo_handle_web_download)
                _profile.setProperty("ALIYVO_DOWNLOAD_HOOK", True)
            except Exception:
                pass
    finally:
        try:
            QTimer.singleShot(2000, _aliyvo_install_download_hooks)
        except Exception:
            pass
# --- fim downloads Copiloto ---

'''
    main_block = re.search(r'(?m)^if\s+__name__\s*==\s*[\"\']__main__[\"\']\s*:', text)
    if main_block:
        text = text[:main_block.start()] + hook + text[main_block.start():]
    else:
        m = re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\(', text)
        if not m:
            raise SystemExit('QApplication creation not found for download hook')
        text = text[:m.start()] + hook + text[m.start():]

    m2 = re.search(r'(?m)^(?P<indent>\s*)(?P<var>[A-Za-z_]\w*)\s*=\s*QApplication\s*\([^\n]*\)\s*$', text)
    if not m2:
        raise SystemExit('QApplication assignment not found after download hook')
    insert_pos = m2.end()
    indent = m2.group('indent')
    text = text[:insert_pos] + '\n' + indent + 'QTimer.singleShot(700, _aliyvo_install_download_hooks)' + text[insert_pos:]

# From 0.22.15 onward, reveal the downloaded file in Windows Explorer when it finishes.
if '_aliyvo_reveal_when_done' not in text:
    old_download = '''        download.setDownloadDirectory(str(folder))\n        download.setDownloadFileName(candidate.name)\n        download.accept()'''
    new_download = '''        download.setDownloadDirectory(str(folder))\n        download.setDownloadFileName(candidate.name)\n\n        def _aliyvo_reveal_when_done(*_args):\n            try:\n                _state = download.state()\n                _state_name = str(getattr(_state, "name", _state))\n                if "DownloadCompleted" not in _state_name:\n                    return\n                try:\n                    download.stateChanged.disconnect(_aliyvo_reveal_when_done)\n                except Exception:\n                    pass\n                import subprocess as _subprocess\n                try:\n                    _subprocess.Popen(["explorer.exe", "/select,", str(candidate)])\n                except Exception:\n                    try:\n                        _os.startfile(str(folder))\n                    except Exception:\n                        pass\n            except Exception:\n                pass\n\n        try:\n            download.stateChanged.connect(_aliyvo_reveal_when_done)\n        except Exception:\n            pass\n        download.accept()'''
    if old_download not in text:
        raise SystemExit('download handler target not found for reveal upgrade')
    text=text.replace(old_download,new_download,1)

# -----------------------------------------------------------------------------
# v0.22.16 - Assistente Técnico leve: somente sob clique, sem observador/timer WA.
# -----------------------------------------------------------------------------
if 'class TechnicalAssistPanel(QWidget):' not in text:
    technical_class = r'''
class TechnicalAssistPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded=False
        self.on_analyze=None
        self.setObjectName("technicalAssistPanel")
        self.setStyleSheet("""
            QWidget#technicalAssistPanel{background:#F8FAFC;color:#0F172A;}
            QWidget#technicalAssistPanel QLabel{color:#0F172A;background:transparent;}
            QWidget#technicalAssistPanel QPushButton{
                background:#0A2236;color:#F4FAF8;border:1px solid #173B52;
                border-radius:6px;padding:8px;font-weight:700;
            }
            QWidget#technicalAssistPanel QPushButton:hover{border-color:#20E983;background:#0D303B;}
            QWidget#technicalAssistPanel QTextEdit{
                background:#FFFFFF;color:#0F172A;border:1px solid #CBD5E1;
                border-radius:6px;font-size:11px;padding:5px;
            }
        """)
        lay=QVBoxLayout(self)
        lay.setContentsMargins(8,8,8,8)
        lay.setSpacing(7)

        head=QHBoxLayout()
        title=QLabel("⚡ Assistente Técnico")
        title.setStyleSheet("font-size:15px;font-weight:800;color:#073B4C;")
        head.addWidget(title)
        head.addStretch(1)
        self.expand_btn=QPushButton("⛶")
        self.expand_btn.setFixedWidth(34)
        self.close_btn=QPushButton("◀")
        self.close_btn.setFixedWidth(34)
        head.addWidget(self.expand_btn)
        head.addWidget(self.close_btn)
        lay.addLayout(head)

        self.status=QLabel("Clique em Ler conversa para analisar somente o atendimento aberto.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#475569;font-size:10px;")
        lay.addWidget(self.status)

        self.analyze_btn=QPushButton("⚡ Ler conversa atual novamente")
        self.analyze_btn.clicked.connect(self._request_analysis)
        lay.addWidget(self.analyze_btn)

        self.result=QTextEdit()
        self.result.setReadOnly(True)
        self.result.setPlaceholderText("O pedido, termos técnicos e possibilidades da Base Soma aparecerão aqui.")
        lay.addWidget(self.result,1)

        warn=QLabel("Resultados por descrição são possibilidades. Confirme aplicação/código/chassi antes da venda.")
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#9A6700;font-size:9px;font-weight:700;")
        lay.addWidget(warn)

    def _request_analysis(self):
        if self.on_analyze:
            self.on_analyze()

    def set_loading(self):
        self.status.setText("Lendo somente a conversa aberta e consultando a Base Soma...")
        self.result.setPlainText("Analisando pedido atual...")

    def render_error(self, message):
        self.status.setText("Não consegui ler o pedido atual.")
        self.result.setPlainText(str(message or "Abra uma conversa no WhatsApp e tente novamente."))

    def render_payload(self, data):
        if not isinstance(data,dict) or not data.get("ok"):
            self.render_error((data or {}).get("error") if isinstance(data,dict) else None)
            return
        name=str(data.get("name") or "Cliente")
        messages=[str(x).strip() for x in (data.get("messages") or []) if str(x).strip()]
        text="\n".join(messages[-5:]).strip()
        if not text:
            self.render_error("Não encontrei mensagem de texto recebida nesta conversa.")
            return

        normalized=normalize_phrase(text)
        raw_tokens=re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9./-]*", normalized)
        stop={
            "bom","boa","dia","tarde","noite","por","favor","pra","para","com","sem","que","tem","uma","uns","umas",
            "esse","essa","isso","meu","minha","dele","dela","cliente","preciso","queria","quero","consegue","consegue",
            "do","da","dos","das","de","e","ou","no","na","nos","nas","modelo","mod"
        }
        tokens=[]
        for t in raw_tokens:
            t=t.strip("./-").lower()
            if not t or t in stop: continue
            if re.fullmatch(r"(?:19|20)\d{2}",t): continue
            if len(t)<3 and t not in ("mb",): continue
            if t not in tokens: tokens.append(t)

        lines=["PEDIDO CAPTURADO",f"Cliente: {name}",""]
        for m in messages[-5:]:
            lines.append("• "+m[:500])

        technical=find_technical_knowledge(text,DB_PATH)
        alias=find_alias_match(text,DB_PATH)
        if technical or alias:
            lines += ["","LEITURA TÉCNICA"]
            if technical:
                frase,termo,aplicacao,consulta,obs=technical
                lines.append(f"• {termo}")
                if aplicacao: lines.append(f"• Aplicação conhecida: {aplicacao}")
                if consulta: lines.append(f"• Pesquisa sugerida: {consulta}")
            if alias:
                termo_cliente,termo_tecnico,medida_ctx,cod_pref,obs=alias
                lines.append(f"• '{termo_cliente}' pode significar '{termo_tecnico}'")

        if tokens:
            lines += ["","TERMOS ÚTEIS"," • ".join(tokens[:10])]

        # Códigos explícitos: evita tratar ano/modelo curto como referência.
        codes=[]
        for c in extract_codes_strict(text):
            nc=norm(c)
            if len(nc)>=5 and any(ch.isdigit() for ch in nc) and c not in codes:
                codes.append(c)
        for c in re.findall(r"(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9./-]{4,})(?![A-Za-z0-9])",text):
            nc=norm(c)
            if len(nc)>=5 and any(ch.isdigit() for ch in nc) and not re.fullmatch(r"(?:19|20)\d{2}",c) and c not in codes:
                codes.append(c)

        exact=[]
        if codes:
            try:
                con=sqlite3.connect(DB_PATH); cur=con.cursor()
                seen=set()
                for code in codes[:10]:
                    nq=norm(code)
                    rows=cur.execute("""
                        SELECT id,codprod,refforn,marca,descricao,compldesc,
                        CASE WHEN codprod=? THEN 100 WHEN refforn=? THEN 98
                             WHEN n_codprod=? THEN 95 WHEN n_refforn=? THEN 93
                             WHEN n_compldesc LIKE ? THEN 80 ELSE 0 END score
                        FROM produtos
                        WHERE codprod=? OR refforn=? OR n_codprod=? OR n_refforn=? OR n_compldesc LIKE ?
                        ORDER BY score DESC LIMIT 6
                    """,(code,code,nq,nq,f"%{nq}%",code,code,nq,nq,f"%{nq}%")).fetchall()
                    for r in rows:
                        if r[0] not in seen:
                            seen.add(r[0]); exact.append(r)
                con.close()
            except Exception:
                exact=[]

        part_words={
            "servo","cilindro","embreagem","cano","tubo","compressor","retentor","cruzeta","filtro","pastilha","disco",
            "cubo","rolamento","sensor","valvula","bomba","reparo","mola","cuica","terminal","barra","amortecedor",
            "bolsa","balao","junta","anel","pistao","bucha","radiador","suporte","eixo","mangueira","diafragma",
            "catraca","freio","embreagem","atuador","volante","coroa","pinhao","sincronizado","garfo"
        }
        parts=[t for t in tokens if t in part_words]
        query_pairs=[]
        for pword in parts[:5]:
            for other in tokens[:10]:
                if other==pword: continue
                pair=(pword,other)
                if pair not in query_pairs:
                    query_pairs.append(pair)
                if len(query_pairs)>=14: break
            if len(query_pairs)>=14: break

        fuzzy=[]; fuzzy_seen=set()
        for pair in query_pairs:
            try:
                rows=search_products_by_words(DB_PATH,list(pair),limit=12)
            except Exception:
                rows=[]
            for r in rows:
                if r[0] not in fuzzy_seen and not any(x[0]==r[0] for x in exact):
                    fuzzy_seen.add(r[0]); fuzzy.append((r,pair))
                if len(fuzzy)>=10: break
            if len(fuzzy)>=10: break

        # Fallback controlado: uma palavra de peça, ainda sempre como possibilidade.
        if not exact and not fuzzy and parts:
            try:
                for r in search_products_by_words(DB_PATH,[parts[0]],limit=8):
                    if r[0] not in fuzzy_seen:
                        fuzzy_seen.add(r[0]); fuzzy.append((r,(parts[0],)))
            except Exception:
                pass

        lines += ["","BASE SOMA"]
        if exact:
            lines.append("🟢 CORRESPONDÊNCIA DIRETA DE CÓDIGO/REFERÊNCIA")
            for r in exact[:8]:
                lines.append(f"• Soma {r[1]} | {r[2] or '-'} | {r[3] or '-'}")
                lines.append("  "+str(r[4] or "")[:180])
        if fuzzy:
            lines.append("🟡 POSSIBILIDADES — confirmar aplicação")
            for r,pair in fuzzy[:8]:
                lines.append(f"• Soma {r[1]} | {r[2] or '-'} | {r[3] or '-'}")
                lines.append("  "+str(r[4] or "")[:180])
        if not exact and not fuzzy:
            lines.append("• Nenhuma possibilidade útil encontrada na base local com estes termos.")

        missing=[]
        if not re.search(r"\b(?:19|20)\d{2}\b",text): missing.append("ano/modelo")
        if not re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b",text.upper()): missing.append("chassi para confirmar a aplicação")
        lines += ["","PARA CONFIRMAR"]
        if missing:
            lines.extend("• "+x for x in missing)
        else:
            lines.append("• Conferir código/aplicação antes de fechar a venda.")

        self.result.setPlainText("\n".join(lines))
        self.status.setText(f"✅ Pedido analisado • {len(exact)} correspondência(s) direta(s) • {len(fuzzy)} possibilidade(s).")

'''
    anchor='class MainWindow(QMainWindow):'
    if anchor not in text:
        raise SystemExit('MainWindow anchor not found for technical panel')
    text=text.replace(anchor,technical_class+'\n'+anchor,1)

    # Botão principal na lateral, acima das demais ferramentas.
    old='''        self.lens_toggle=QPushButton("🔎  Busca por imagem")'''
    new='''        self.quick_technical=QPushButton("⚡  Analisar pedido atual")\n        self.lens_toggle=QPushButton("🔎  Busca por imagem")'''
    if old not in text: raise SystemExit('quick button anchor not found')
    text=text.replace(old,new,1)

    old='''        q.addSpacing(5)\n        q.addWidget(self.lens_toggle)'''
    new='''        q.addSpacing(5)\n        q.addWidget(self.quick_technical)\n        q.addWidget(self.lens_toggle)'''
    if old not in text: raise SystemExit('quick layout anchor not found')
    text=text.replace(old,new,1)

    # Painel leve do assistente técnico.
    old='''        self.copilot=ALIYVOPanel()\n\n        self.lens_panel=LensPanel(self.web_host)'''
    new='''        self.copilot=ALIYVOPanel()\n\n        self.technical_panel=TechnicalAssistPanel(self.web_host)\n        self.technical_panel.hide()\n        self.technical_panel.raise_()\n        self.technical_panel.on_analyze=self._technical_analyze_current\n\n        self.lens_panel=LensPanel(self.web_host)'''
    if old not in text: raise SystemExit('panel creation anchor not found')
    text=text.replace(old,new,1)

    old='''        # ========== SINAIS ==========\n        self.lens_toggle.clicked.connect(lambda: self._open_quick_tool("lens"))'''
    new='''        # ========== SINAIS ==========\n        self.quick_technical.clicked.connect(self._technical_open_and_analyze)\n        self.technical_panel.close_btn.clicked.connect(lambda: self._close_tool_panel("technical"))\n        self.technical_panel.expand_btn.clicked.connect(self.toggle_technical_expand)\n        self.lens_toggle.clicked.connect(lambda: self._open_quick_tool("lens"))'''
    if old not in text: raise SystemExit('signals anchor not found')
    text=text.replace(old,new,1)

    # Integração com o host de ferramentas da direita.
    old='''            "lens": self.lens_panel,'''
    new='''            "technical": self.technical_panel,\n            "lens": self.lens_panel,'''
    if old not in text: raise SystemExit('tool panel map anchor not found')
    text=text.replace(old,new,1)

    # Larguras do painel técnico.
    text=text.replace('''                "lens": 620,''','''                "technical": 680,\n                "lens": 620,''',1)
    text=text.replace('''            "lens": 430,''','''            "technical": 520,\n            "lens": 430,''',1)

    old='''        self.lens_toggle.setText("🔎  Busca por imagem")'''
    new='''        self.quick_technical.setText("⚡  Analisar pedido atual")\n        self.lens_toggle.setText("🔎  Busca por imagem")'''
    if old not in text: raise SystemExit('reset labels anchor not found')
    text=text.replace(old,new,1)

    old='''        for name in ("lens","chat","prazo","audio","campaign","diagnostic","update","plate"):'''
    new='''        for name in ("technical","lens","chat","prazo","audio","campaign","diagnostic","update","plate"):'''
    if old not in text: raise SystemExit('quick close loop anchor not found')
    text=text.replace(old,new,1)

    old='''        if tool in ("diagnostic","update","plate"):'''
    new='''        if tool in ("technical","diagnostic","update","plate"):'''
    if old not in text: raise SystemExit('close special tools anchor not found')
    text=text.replace(old,new,1)

    # Métodos MainWindow: um clique, uma leitura DOM, nenhuma observação contínua.
    main_methods = r'''
    def _technical_open_and_analyze(self):
        self._open_quick_tool("technical")
        QTimer.singleShot(0,self._technical_analyze_current)

    def _technical_analyze_current(self):
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
            const pushText=(t)=>{
              t=String(t||'').replace(/\s+/g,' ').trim();
              if(!t || t.length<2) return;
              if(messages.length && messages[messages.length-1]===t) return;
              messages.push(t.slice(0,1200));
            };
            let inbound=Array.from(main.querySelectorAll('div.message-in'));
            for(const bubble of inbound.slice(-20)){
              let parts=[];
              const nodes=Array.from(bubble.querySelectorAll('span.selectable-text, [data-testid="selectable-text"]'));
              for(const n of nodes){
                const t=(n.innerText||n.textContent||'').trim();
                if(t && !parts.includes(t)) parts.push(t);
              }
              if(parts.length) pushText(parts.join(' '));
            }
            if(!messages.length){
              const candidates=Array.from(main.querySelectorAll('[data-pre-plain-text]')).slice(-20);
              for(const c of candidates){
                const parent=c.closest('.message-in');
                if(inbound.length && !parent) continue;
                const n=c.querySelector('span.selectable-text') || c;
                pushText(n.innerText||n.textContent||'');
              }
            }
            return {ok:true,name:name,messages:messages.slice(-8)};
          }catch(e){ return {ok:false,error:String(e)}; }
        })()
        """
        try:
            self.web.page().runJavaScript(js,self._technical_receive_current)
        except Exception as e:
            self.technical_panel.render_error(str(e))

    def _technical_receive_current(self,result):
        try:
            self.technical_panel.render_payload(result)
        except Exception as e:
            try:self.technical_panel.render_error('Falha ao analisar: '+str(e))
            except Exception:pass

    def toggle_technical_expand(self):
        if not self.technical_panel.isVisible():
            self._open_quick_tool("technical")
            return
        self.technical_panel.expanded=not getattr(self.technical_panel,"expanded",False)
        self.technical_panel.expand_btn.setText("↩" if self.technical_panel.expanded else "⛶")
        self._position_quick_tool("technical")

'''
    anchor='''    def _release_whatsapp_focus(self):'''
    if anchor not in text: raise SystemExit('MainWindow methods anchor not found')
    text=text.replace(anchor,main_methods+anchor,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched',version)

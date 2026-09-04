from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v25.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

if 'class _AliyvoSomaforceUploadPage' not in text:
    marker='class SomaforceCatalogPanel(QWidget):\n'
    if marker not in text:
        raise SystemExit('SomaforceCatalogPanel marker not found')

    helper=r'''
try:
    from PyQt6.QtWebEngineCore import QWebEnginePage as _AliyvoQWebEnginePage
except Exception:
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage as _AliyvoQWebEnginePage
    except Exception:
        _AliyvoQWebEnginePage = None

class _AliyvoSomaforceUploadPage(_AliyvoQWebEnginePage if _AliyvoQWebEnginePage is not None else object):
    def __init__(self,parent=None):
        if _AliyvoQWebEnginePage is not None:
            super().__init__(parent)
        self._aliyvo_pending_upload=""

    def set_pending_upload(self,path):
        self._aliyvo_pending_upload=str(path or "")

    def chooseFiles(self,mode,oldFiles,acceptedMimeTypes):
        try:
            path=str(self._aliyvo_pending_upload or "")
            if path and Path(path).exists():
                self._aliyvo_pending_upload=""
                return [path]
        except Exception:
            pass
        try:
            return super().chooseFiles(mode,oldFiles,acceptedMimeTypes)
        except Exception:
            return []

class _AliyvoSomaforceDropFilter(QObject):
    def __init__(self,panel):
        super().__init__(panel)
        self.panel=panel

    def _inside_browser(self,obj):
        try:
            cur=obj
            for _ in range(16):
                if cur is None: break
                if cur is self.panel.browser: return True
                try: cur=cur.parent()
                except Exception: break
        except Exception:
            pass
        return False

    def _interesting(self,md):
        try:
            if md.hasImage() or md.hasUrls(): return True
            for f in md.formats():
                s=str(f).lower()
                if 'image' in s or 'filecontents' in s or 'filegroupdescriptor' in s:
                    return True
            if md.hasHtml():
                h=str(md.html() or '')
                if '<img' in h.lower() or 'data:image/' in h.lower(): return True
        except Exception:
            pass
        return False

    def eventFilter(self,obj,event):
        try:
            if not self._inside_browser(obj): return False
            et=event.type()
            if et in (QEvent.Type.DragEnter,QEvent.Type.DragMove):
                try:
                    if self._interesting(event.mimeData()):
                        event.acceptProposedAction(); return True
                except Exception: pass
            if et==QEvent.Type.Drop:
                try:
                    if self.panel._aliyvo_handle_photo_drop(event.mimeData()):
                        event.acceptProposedAction(); return True
                except Exception as e:
                    try: self.panel._aliyvo_set_drop_status('Falha ao receber imagem: '+str(e)[:120],True)
                    except Exception: pass
        except Exception:
            pass
        return False

'''
    text=text.replace(marker,helper+marker,1)

old='''        self.browser=QWebEngineView(self)\n        self.browser.setFocusPolicy(Qt.FocusPolicy.StrongFocus)'''
if old not in text:
    raise SystemExit('Somaforce browser creation anchor not found')
new='''        self.browser=QWebEngineView(self)\n        try:\n            if _AliyvoQWebEnginePage is not None:\n                self._aliyvo_upload_page=_AliyvoSomaforceUploadPage(self.browser)\n                self.browser.setPage(self._aliyvo_upload_page)\n            else:\n                self._aliyvo_upload_page=None\n        except Exception:\n            self._aliyvo_upload_page=None\n        self.browser.setAcceptDrops(True)\n        self.browser.setFocusPolicy(Qt.FocusPolicy.StrongFocus)'''
text=text.replace(old,new,1)

old='''        self.browser.setUrl(QUrl(self.URL))\n        lay.addWidget(self.browser,1)\n\n        self.refresh_btn.clicked.connect(self.browser.reload)'''
if old not in text:
    raise SystemExit('Somaforce browser layout anchor not found')
new='''        self.browser.setUrl(QUrl(self.URL))\n        lay.addWidget(self.browser,1)\n\n        self._aliyvo_drop_status=QLabel("📷 Arraste a foto do WhatsApp para dentro do buscador. O ALIYVO envia para leitura automaticamente.")\n        self._aliyvo_drop_status.setWordWrap(True)\n        self._aliyvo_drop_status.setStyleSheet("color:#0F766E;font-size:10px;font-weight:700;padding:4px;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:5px;")\n        lay.insertWidget(max(0,lay.count()-1),self._aliyvo_drop_status)\n        self._aliyvo_drop_filter=_AliyvoSomaforceDropFilter(self)\n        try:\n            QApplication.instance().installEventFilter(self._aliyvo_drop_filter)\n        except Exception:\n            try: self.browser.installEventFilter(self._aliyvo_drop_filter)\n            except Exception: pass\n\n        self.refresh_btn.clicked.connect(self.browser.reload)'''
text=text.replace(old,new,1)

anchor='''    def _open_external(self):\n        try:\n            QDesktopServices.openUrl(QUrl(self.URL))\n        except Exception:\n            pass\n'''
if anchor not in text:
    raise SystemExit('Somaforce open external anchor not found')

methods=r"""    def _aliyvo_set_drop_status(self,message,error=False):
        try:
            self._aliyvo_drop_status.setText(str(message or ""))
            if error:
                self._aliyvo_drop_status.setStyleSheet("color:#991B1B;font-size:10px;font-weight:700;padding:4px;background:#FEF2F2;border:1px solid #FCA5A5;border-radius:5px;")
            else:
                self._aliyvo_drop_status.setStyleSheet("color:#0F766E;font-size:10px;font-weight:700;padding:4px;background:#ECFDF5;border:1px solid #A7F3D0;border-radius:5px;")
        except Exception:
            pass

    def _aliyvo_temp_image_path(self,ext="png"):
        import tempfile,time
        folder=Path(tempfile.gettempdir())/"ALIYVO"/"pedido_foto"
        folder.mkdir(parents=True,exist_ok=True)
        ext=re.sub(r"[^a-zA-Z0-9]","",str(ext or "png").lower()) or "png"
        return folder/("pedido_"+str(int(time.time()*1000))+"."+ext)

    def _aliyvo_save_bytes(self,data):
        try:
            raw=bytes(data)
            if not raw: return ""
            ext="bin"
            if raw.startswith(b"\x89PNG\r\n\x1a\n"): ext="png"
            elif raw[:3]==b"\xff\xd8\xff": ext="jpg"
            elif raw[:4]==b"RIFF" and b"WEBP" in raw[:16]: ext="webp"
            elif raw[:6] in (b"GIF87a",b"GIF89a"): ext="gif"
            if ext=="bin" and len(raw)<4096: return ""
            path=self._aliyvo_temp_image_path(ext if ext!="bin" else "png")
            path.write_bytes(raw)
            return str(path)
        except Exception:
            return ""

    def _aliyvo_path_from_mime(self,md):
        try:
            if md.hasUrls():
                for u in md.urls():
                    try:
                        if u.isLocalFile():
                            path=str(u.toLocalFile() or "")
                            if path and Path(path).exists() and Path(path).suffix.lower() in (".jpg",".jpeg",".png",".webp",".gif",".bmp"):
                                return path
                    except Exception: pass
        except Exception: pass

        try:
            if md.hasImage():
                img=md.imageData()
                if img is not None:
                    path=self._aliyvo_temp_image_path("png")
                    if hasattr(img,"save") and img.save(str(path),"PNG"):
                        return str(path)
                    try:
                        pix=QPixmap.fromImage(img)
                        if pix.save(str(path),"PNG"): return str(path)
                    except Exception: pass
        except Exception: pass

        try:
            formats=[str(x) for x in md.formats()]
            preferred=[f for f in formats if "filecontents" in f.lower()]
            preferred += [f for f in formats if "image/" in f.lower() or "x-qt-image" in f.lower()]
            seen=set()
            for fmt in preferred:
                if fmt in seen: continue
                seen.add(fmt)
                try:
                    path=self._aliyvo_save_bytes(md.data(fmt))
                    if path: return path
                except Exception: pass
        except Exception: pass

        try:
            import base64
            sources=[]
            if md.hasHtml(): sources.append(str(md.html() or ""))
            if md.hasText(): sources.append(str(md.text() or ""))
            for src in sources:
                m=re.search(r'data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)',src,re.I)
                if m:
                    raw=base64.b64decode(re.sub(r"\s+","",m.group(2)))
                    ext=m.group(1).lower().replace("jpeg","jpg")
                    path=self._aliyvo_temp_image_path(ext)
                    path.write_bytes(raw)
                    return str(path)
        except Exception: pass
        return ""

    def _aliyvo_handle_photo_drop(self,md):
        try:
            path=self._aliyvo_path_from_mime(md)
            if not path:
                fmts=[]
                try: fmts=[str(x) for x in md.formats()]
                except Exception: pass
                self._aliyvo_set_drop_status("⚠ O WhatsApp arrastou a foto, mas não entregou os bytes. Formatos: "+", ".join(fmts[:6]),True)
                return False
            self._aliyvo_set_drop_status("✅ Foto recebida. Enviando para Ler pedido por foto...")
            self._aliyvo_upload_file_to_site(path)
            return True
        except Exception as e:
            self._aliyvo_set_drop_status("⚠ Não consegui processar a foto: "+str(e)[:140],True)
            return False

    def _aliyvo_upload_file_to_site(self,path):
        try:
            page=getattr(self,"_aliyvo_upload_page",None)
            if page is None or not hasattr(page,"set_pending_upload"):
                self._aliyvo_set_drop_status("⚠ Navegador interno sem suporte ao upload automático.",True); return
            page.set_pending_upload(path)
            js=r'''(() => {
              const inputs=[...document.querySelectorAll('input[type="file"]')];
              if(!inputs.length) return {ok:false,reason:'file_input_not_found'};
              const f=inputs[0];
              try{f.scrollIntoView({block:'center'});}catch(e){}
              f.click();
              return {ok:true};
            })()'''
            def after(res):
                ok=False
                try: ok=isinstance(res,dict) and bool(res.get("ok"))
                except Exception: pass
                if not ok:
                    self._aliyvo_set_drop_status("⚠ Não encontrei o campo de arquivo do site. Recarregue e tente novamente.",True); return
                QTimer.singleShot(1200,self._aliyvo_submit_photo_request)
            self.browser.page().runJavaScript(js,after)
        except Exception as e:
            self._aliyvo_set_drop_status("⚠ Falha ao entregar a foto ao site: "+str(e)[:140],True)

    def _aliyvo_submit_photo_request(self):
        try:
            js=r'''(() => {
              const all=[...document.querySelectorAll('button,input[type="submit"],a')];
              const norm=s=>(s||'').replace(/\s+/g,' ').trim().toLowerCase();
              let b=all.find(x=>norm(x.innerText||x.textContent||x.value).includes('enviar e ler pedido'));
              if(!b) b=all.find(x=>norm(x.innerText||x.textContent||x.value).includes('ler pedido'));
              if(!b) return {ok:false};
              b.click(); return {ok:true};
            })()'''
            def done(res):
                try:
                    if isinstance(res,dict) and res.get("ok"):
                        self._aliyvo_set_drop_status("✅ Foto enviada. Aguardando a leitura do pedido...")
                    else:
                        self._aliyvo_set_drop_status("✅ Foto colocada no site. Clique em ENVIAR E LER PEDIDO.")
                except Exception: pass
            self.browser.page().runJavaScript(js,done)
        except Exception:
            self._aliyvo_set_drop_status("✅ Foto colocada no site. Clique em ENVIAR E LER PEDIDO.")

"""
text=text.replace(anchor,methods+anchor,1)

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched Somaforce WhatsApp photo drag/drop',version)

from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v26.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

start=text.find('    def _aliyvo_save_bytes(self,data):')
end=text.find('    def _aliyvo_handle_photo_drop(self,md):',start)
if start<0 or end<0:
    raise SystemExit('photo mime methods anchor not found')

new_methods=r'''    def _aliyvo_save_bytes(self,data,name_hint=""):
        try:
            raw=bytes(data)
            if not raw or len(raw)<32:
                return ""
            ext=""
            if raw.startswith(b"\x89PNG\r\n\x1a\n"):
                ext="png"
            elif raw[:3]==b"\xff\xd8\xff":
                ext="jpg"
            elif raw[:4]==b"RIFF" and b"WEBP" in raw[:16]:
                ext="webp"
            elif raw[:6] in (b"GIF87a",b"GIF89a"):
                ext="gif"
            elif raw[:2]==b"BM":
                ext="bmp"

            # Alguns FileContents do Chromium chegam sem um header que reconhecemos
            # de primeira. Deixe o Qt tentar decodificar os bytes como imagem.
            if not ext:
                try:
                    pix=QPixmap()
                    if pix.loadFromData(raw) and not pix.isNull():
                        path=self._aliyvo_temp_image_path("png")
                        if pix.save(str(path),"PNG"):
                            return str(path)
                except Exception:
                    pass

            if not ext:
                try:
                    suf=Path(str(name_hint or "")).suffix.lower().lstrip('.')
                    if suf in ("jpg","jpeg","png","webp","gif","bmp"):
                        ext="jpg" if suf=="jpeg" else suf
                except Exception:
                    pass

            if not ext:
                return ""
            path=self._aliyvo_temp_image_path(ext)
            path.write_bytes(raw)
            return str(path)
        except Exception:
            return ""

    def _aliyvo_virtual_file_name(self,md):
        # Tenta extrair um nome do FILEGROUPDESCRIPTORW apenas como dica de extensao.
        try:
            fmts=[str(x) for x in md.formats()]
            fd=next((f for f in fmts if 'filegroupdescriptorw' in f.lower()),"")
            if not fd:
                fd='application/x-qt-windows-mime;value="FileGroupDescriptorW"'
            raw=bytes(md.data(fd))
            if len(raw)>=8:
                # O nome UTF-16 fica no final de cada FILEDESCRIPTORW. Buscar sequencias legiveis.
                txt=raw.decode('utf-16le',errors='ignore').replace('\x00',' ')
                m=re.findall(r'([A-Za-z0-9 _().-]+\.(?:jpe?g|png|webp|gif|bmp))',txt,re.I)
                if m:
                    return m[-1].strip()
        except Exception:
            pass
        return ""

    def _aliyvo_moz_url(self,md):
        try:
            raw=bytes(md.data('text/x-moz-url'))
            if not raw:
                return ""
            for enc in ('utf-16le','utf-8','latin1'):
                try:
                    s=raw.decode(enc,errors='ignore').replace('\x00','').strip()
                    first=(s.splitlines()[0] if s.splitlines() else s).strip()
                    if first.startswith(('http://','https://','blob:','data:')):
                        return first
                except Exception:
                    pass
        except Exception:
            pass
        return ""

    def _aliyvo_download_drop_url(self,url):
        try:
            if not str(url).startswith(('http://','https://')):
                return ""
            import urllib.request
            req=urllib.request.Request(str(url),headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req,timeout=5) as r:
                raw=r.read(20*1024*1024)
            return self._aliyvo_save_bytes(raw,str(url))
        except Exception:
            return ""

    def _aliyvo_path_from_mime(self,md):
        self._aliyvo_last_drop_debug=[]
        # 1) Arquivo normal arrastado do Explorer ou URL local.
        try:
            if md.hasUrls():
                for u in md.urls():
                    try:
                        if u.isLocalFile():
                            path=str(u.toLocalFile() or "")
                            if path and Path(path).exists() and Path(path).suffix.lower() in (".jpg",".jpeg",".png",".webp",".gif",".bmp"):
                                return path
                        else:
                            remote=str(u.toString() or "")
                            if remote.startswith(('http://','https://')):
                                got=self._aliyvo_download_drop_url(remote)
                                if got:
                                    return got
                    except Exception:
                        pass
        except Exception:
            pass

        # 2) Imagem real entregue pelo Qt.
        try:
            if md.hasImage():
                img=md.imageData()
                if img is not None:
                    path=self._aliyvo_temp_image_path("png")
                    if hasattr(img,"save") and img.save(str(path),"PNG"):
                        return str(path)
                    try:
                        pix=QPixmap.fromImage(img)
                        if pix.save(str(path),"PNG"):
                            return str(path)
                    except Exception:
                        pass
        except Exception:
            pass

        # 3) Arquivo virtual do Windows/Chromium: FileContents pode exigir index=N.
        try:
            formats=[str(x) for x in md.formats()]
            name_hint=self._aliyvo_virtual_file_name(md)
            candidates=[]
            for f in formats:
                low=f.lower()
                if 'filecontents' in low:
                    candidates.append(f)
            base_forms=[
                'application/x-qt-windows-mime;value="FileContents"',
                "application/x-qt-windows-mime;value=FileContents",
            ]
            candidates.extend(base_forms)
            for i in range(8):
                candidates.append('application/x-qt-windows-mime;value="FileContents";index='+str(i))
                candidates.append('application/x-qt-windows-mime;value=FileContents;index='+str(i))
            # Outros formatos que as vezes carregam a imagem diretamente.
            candidates += [f for f in formats if 'image/' in f.lower() or 'x-qt-image' in f.lower()]

            seen=set()
            for fmt in candidates:
                if fmt in seen:
                    continue
                seen.add(fmt)
                try:
                    raw=md.data(fmt)
                    n=len(bytes(raw))
                    if 'filecontents' in fmt.lower() or n:
                        short=fmt.replace('application/x-qt-windows-mime;value=','').replace('application/x-qt-windows-mime;value="','').replace('"','')
                        self._aliyvo_last_drop_debug.append(short+'='+str(n))
                    if n:
                        path=self._aliyvo_save_bytes(raw,name_hint)
                        if path:
                            return path
                except Exception as e:
                    if 'filecontents' in fmt.lower():
                        self._aliyvo_last_drop_debug.append('erro='+str(e)[:50])
        except Exception as e:
            self._aliyvo_last_drop_debug.append('virtual='+str(e)[:60])

        # 4) text/x-moz-url: Chromium costuma mandar junto com FileContents.
        try:
            moz=self._aliyvo_moz_url(md)
            if moz:
                self._aliyvo_last_drop_debug.append('moz='+moz[:90])
                got=self._aliyvo_download_drop_url(moz)
                if got:
                    return got
        except Exception:
            pass

        # 5) data:image embutido em HTML/texto.
        try:
            import base64
            sources=[]
            if md.hasHtml():
                sources.append(str(md.html() or ""))
            if md.hasText():
                sources.append(str(md.text() or ""))
            for src in sources:
                m=re.search(r'data:image/([a-zA-Z0-9.+-]+);base64,([A-Za-z0-9+/=\r\n]+)',src,re.I)
                if m:
                    raw=base64.b64decode(re.sub(r"\s+","",m.group(2)))
                    ext=m.group(1).lower().replace("jpeg","jpg")
                    path=self._aliyvo_temp_image_path(ext)
                    path.write_bytes(raw)
                    return str(path)
        except Exception:
            pass
        return ""

'''
text=text[:start]+new_methods+text[end:]

hstart=text.find('    def _aliyvo_handle_photo_drop(self,md):')
hend=text.find('    def _aliyvo_upload_file_to_site(self,path):',hstart)
if hstart<0 or hend<0:
    raise SystemExit('handle photo drop anchor not found')

new_handle=r'''    def _aliyvo_handle_photo_drop(self,md):
        try:
            path=self._aliyvo_path_from_mime(md)
            if not path:
                debug=[]
                try:
                    debug=list(getattr(self,'_aliyvo_last_drop_debug',[]) or [])
                except Exception:
                    pass
                if debug:
                    msg="⚠ Arquivo virtual detectado, mas a imagem ainda nao abriu. Dados: "+" | ".join(debug[:10])
                else:
                    fmts=[]
                    try:
                        fmts=[str(x) for x in md.formats()]
                    except Exception:
                        pass
                    msg="⚠ O WhatsApp arrastou a foto, mas nao entregou bytes utilizaveis. Formatos: "+", ".join(fmts[:6])
                self._aliyvo_set_drop_status(msg,True)
                return False
            self._aliyvo_set_drop_status("✅ Foto recebida. Enviando para Ler pedido por foto...")
            self._aliyvo_upload_file_to_site(path)
            return True
        except Exception as e:
            self._aliyvo_set_drop_status("⚠ Nao consegui processar a foto: "+str(e)[:140],True)
            return False

'''
text=text[:hstart]+new_handle+text[hend:]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched indexed Windows FileContents drag/drop',version)

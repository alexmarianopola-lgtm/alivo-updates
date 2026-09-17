from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

def one(old,new,label):
    global text
    n=text.count(old)
    if n!=1:
        raise SystemExit(f'{label}: esperado 1, encontrado {n}')
    text=text.replace(old,new,1)

one('ALIYVO_VERSION = "0.22.88"','ALIYVO_VERSION = "0.22.89"','version')

one('''    def _diagnostic_start(self):\n        self._diagnostic_busy=False\n''','''    def _diagnostic_start(self):\n        # Cache em memoria: o historico JSONL e carregado uma vez por sessao.\n        # Novos eventos sao acrescentados ao cache em _diagnostic_log.\n        self._diagnostic_cache_rows=None\n        self._diagnostic_busy=False\n''','diagnostic cache init')

one('''            with self._diagnostic_file().open("a",encoding="utf-8") as f:\n                f.write(json.dumps(row,ensure_ascii=False)+"\\n")\n''','''            with self._diagnostic_file().open("a",encoding="utf-8") as f:\n                f.write(json.dumps(row,ensure_ascii=False)+"\\n")\n            cache=getattr(self,"_diagnostic_cache_rows",None)\n            if isinstance(cache,list):\n                cache.append(dict(row))\n''','diagnostic cache append')

start=text.index('    def _diagnostic_read(self):\n')
end=text.index('    def _diagnostic_summary_text(self,rows):\n',start)
text=text[:start]+'''    def _diagnostic_read(self):\n        # O arquivo cresce durante todo o uso. Rele-lo inteiro em cada refresh/backup\n        # travava a thread da interface conforme o historico aumentava.\n        cached=getattr(self,"_diagnostic_cache_rows",None)\n        if isinstance(cached,list):\n            return list(cached)\n        rows=[]\n        try:\n            f=self._diagnostic_file()\n            if f.exists():\n                for line in f.read_text(encoding="utf-8",errors="ignore").splitlines():\n                    try:\n                        x=json.loads(line)\n                        if not isinstance(x,dict):continue\n                        if x.get("event")=="response":\n                            try:\n                                secs=int(x.get("total_wait_seconds") or x.get("response_seconds") or 0)\n                                if secs>48*3600:continue\n                            except Exception:pass\n                        rows.append(x)\n                    except Exception:pass\n        except Exception:pass\n        self._diagnostic_cache_rows=rows\n        return list(rows)\n\n'''+text[end:]

one('''        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(3000)\n''','''        # 5 s preserva o acompanhamento quase em tempo real e reduz em 40%\n        # as consultas ao DOM do WhatsApp executadas durante todo o expediente.\n        self._diagnostic_timer=QTimer(self); self._diagnostic_timer.setInterval(5000)\n''','diagnostic scan interval')

one('''        self._diagnostic_backup_timer=QTimer(self); self._diagnostic_backup_timer.setInterval(120000)\n''','''        self._diagnostic_backup_timer=QTimer(self); self._diagnostic_backup_timer.setInterval(600000)\n''','backup interval')

one('''                "ai_observer_learning":self._ai_learning_summary_payload(True),\n''','''                "ai_observer_learning":self._ai_learning_summary_payload(False),\n''','backup learning')

one('''        def refresh():\n            groups=set(self._diagnostic_groups_load()); pending=len(self._diagnostic_waiting_snapshot())\n            info.setText(f"Contatos individuais • {len(groups)} grupo(s) ignorado(s) • {pending} aguardando resposta agora")\n            txt.setPlainText(self._diagnostic_whatsapp_overview_text()+"\\n\\n"+self._diagnostic_enhanced_text(filtered_rows()))\n        refresh(); live=QTimer(dlg); live.setInterval(3000); live.timeout.connect(refresh); live.start()\n''','''        def refresh():\n            try:\n                groups=set(self._diagnostic_groups_load()); pending=len(self._diagnostic_waiting_snapshot())\n                info.setText(f"Contatos individuais • {len(groups)} grupo(s) ignorado(s) • {pending} aguardando resposta agora")\n                txt.setPlainText(self._diagnostic_whatsapp_overview_text()+"\\n\\n"+self._diagnostic_enhanced_text(filtered_rows()))\n            except RuntimeError:\n                # Pode existir um timeout ja enfileirado no instante em que a janela fecha.\n                return\n        refresh(); live=QTimer(dlg); live.setInterval(5000); live.timeout.connect(refresh); live.start()\n        dlg.finished.connect(lambda _=0,t=live:t.stop())\n''','diagnostic dialog timer')

one('''        export.clicked.connect(do_export);close.clicked.connect(dlg.accept);dlg.exec()\n\n    def _reminder_file(self):\n''','''        export.clicked.connect(do_export);close.clicked.connect(dlg.accept);dlg.exec()\n        try:live.stop()\n        except Exception:pass\n\n    def _reminder_file(self):\n''','diagnostic dialog final stop')

one('''        timer=QTimer(dlg);timer.setInterval(600);timer.timeout.connect(poll);timer.start()\n        load_cache(False);self._ai_profiles_cache_refresh_async(False);dlg.exec()\n''','''        timer=QTimer(dlg);timer.setInterval(600);timer.timeout.connect(poll);timer.start()\n        dlg.finished.connect(lambda _=0,t=timer:t.stop())\n        load_cache(False);self._ai_profiles_cache_refresh_async(False);dlg.exec()\n        try:timer.stop()\n        except Exception:pass\n''','ai profile timer stop')

one('''        try:\n            if client in set(self._diagnostic_groups_load()):return\n        except Exception:pass\n''','''        try:\n            # O conjunto ja fica em memoria; evita reler JSON do disco a cada scan.\n            if client in set(getattr(self,"_diagnostic_groups",set()) or set()):return\n        except Exception:pass\n''','smart reminder groups memory')

one('''def _aliyvo_install_download_hooks():\n    try:\n        _app = QApplication.instance()\n        if _app is None:\n            return\n        for _w in _app.allWidgets():\n            try:\n                _page = _w.page()\n                if _page is None:\n                    continue\n                _profile = _page.profile()\n                if _profile is None or bool(_profile.property("ALIYVO_DOWNLOAD_HOOK")):\n                    continue\n                _profile.downloadRequested.connect(_aliyvo_handle_web_download)\n                _profile.setProperty("ALIYVO_DOWNLOAD_HOOK", True)\n            except Exception:\n                pass\n    finally:\n        try:\n            QTimer.singleShot(2000, _aliyvo_install_download_hooks)\n        except Exception:\n            pass\n''','''_aliyvo_download_hook_attempts=0\n\ndef _aliyvo_install_download_hooks():\n    # Descoberta apenas durante o startup. O Assistente instala seu proprio\n    # downloadRequested ao criar o QWebEngineView; nao precisamos varrer\n    # QApplication.allWidgets() a cada 2 segundos durante todo o expediente.\n    global _aliyvo_download_hook_attempts\n    _aliyvo_download_hook_attempts+=1\n    try:\n        _app = QApplication.instance()\n        if _app is None:\n            return\n        for _w in _app.allWidgets():\n            try:\n                _page = _w.page()\n                if _page is None:\n                    continue\n                _profile = _page.profile()\n                if _profile is None or bool(_profile.property("ALIYVO_DOWNLOAD_HOOK")):\n                    continue\n                _profile.downloadRequested.connect(_aliyvo_handle_web_download)\n                _profile.setProperty("ALIYVO_DOWNLOAD_HOOK", True)\n            except Exception:\n                pass\n    except Exception:\n        pass\n    if _aliyvo_download_hook_attempts<8:\n        QTimer.singleShot(2000, _aliyvo_install_download_hooks)\n''','download hook finite')

one('''    # A tela de placa e criada/mostrada sob demanda; checagem leve apenas da UI Qt.\n    try:\n        if _aliyvo_plate_override_timer is None:\n            _aliyvo_plate_override_timer=QTimer()\n            _aliyvo_plate_override_timer.setInterval(1200)\n            _aliyvo_plate_override_timer.timeout.connect(_aliyvo_override_old_plate_search)\n            _aliyvo_plate_override_timer.start()\n    except Exception:\n        pass\n''','''    # Sem timer permanente: duas passagens de startup resolvem a troca do botao.\n''','plate override timer removal')

one('''    try:\n        if _aliyvo_plate_ui_cleaner_timer is None:\n            _aliyvo_plate_ui_cleaner_timer=QTimer()\n            _aliyvo_plate_ui_cleaner_timer.setInterval(1200)\n            _aliyvo_plate_ui_cleaner_timer.timeout.connect(_aliyvo_clean_plate_ui)\n            _aliyvo_plate_ui_cleaner_timer.start()\n    except Exception:\n        pass\n''','''    # O limpador antigo nao fica mais varrendo todos os widgets a cada 1,2 s.\n''','plate ui cleaner timer removal')

one('''    try:\n        if _aliyvo_plate_v24_timer is None:\n            _aliyvo_plate_v24_timer=QTimer()\n            _aliyvo_plate_v24_timer.setInterval(1400)\n            _aliyvo_plate_v24_timer.timeout.connect(_aliyvo_clean_plate_ui)\n            _aliyvo_plate_v24_timer.start()\n    except Exception:\n        pass\n\nif __name__=="__main__":\n''','''    # Sem timer permanente: a UI principal nao muda estruturalmente durante o uso.\n\nif __name__=="__main__":\n''','plate v24 timer removal')

one('''    QTimer.singleShot(1000, _aliyvo_clean_plate_ui)\n    QTimer.singleShot(900, _aliyvo_override_old_plate_search)\n''','''    QTimer.singleShot(1000, _aliyvo_clean_plate_ui)\n    QTimer.singleShot(900, _aliyvo_override_old_plate_search)\n    QTimer.singleShot(4500, _aliyvo_clean_plate_ui)\n    QTimer.singleShot(5000, _aliyvo_override_old_plate_search)\n''','finite plate delayed passes')

main.write_text(text,encoding='utf-8')
print('patched stability v0.22.89')

from pathlib import Path
import sys

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.05"' not in text:
    raise SystemExit('base esperada 0.23.05 nao encontrada')
text=text.replace('ALIYVO_VERSION = "0.23.05"','ALIYVO_VERSION = "0.23.06"',1)
text=text.replace('aliyvo_version="0.23.05"','aliyvo_version="0.23.06"')

# Insere metodos antes do dialogo principal do Radar.
anchor='    def _radar_show_dialog(self):\n'
idx=text.index(anchor)
bulk=r'''
    def _radar_known_whatsapp_contacts(self):
        names=set()
        try:
            for x in self._diagnostic_read() or []:
                if isinstance(x,dict):
                    n=str(x.get("client") or "").strip()
                    if n:names.add(n)
        except Exception:pass
        try:
            data=getattr(self,"_attendance_data",{}) or {}
            for n in (data.get("items",{}) or {}).keys():
                n=str(n or "").strip()
                if n:names.add(n)
        except Exception:pass
        try:
            n=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if n:names.add(n)
        except Exception:pass
        try:
            for n in (getattr(self,"_diagnostic_last_context_by_contact",{}) or {}).keys():
                n=str(n or "").strip()
                if n:names.add(n)
        except Exception:pass
        try:
            groups=set(self._diagnostic_groups_load() or [])
            names={n for n in names if n not in groups}
        except Exception:pass
        return sorted(names,key=str.lower)

    def _radar_match_name(self,a,b):
        import re,difflib
        na=self._radar_norm(a);nb=self._radar_norm(b)
        # Remove blocos numericos longos (CNPJ/CPF/telefone) para comparar o nome comercial.
        ca=re.sub(r'\b\d{7,}\b',' ',na);cb=re.sub(r'\b\d{7,}\b',' ',nb)
        ca=re.sub(r'\s+',' ',ca).strip();cb=re.sub(r'\s+',' ',cb).strip()
        if not ca or not cb:return 0.0
        if ca==cb:return 1.0
        # Se um lado contem o outro e o trecho e razoavelmente descritivo, confianca alta.
        if len(min((ca,cb),key=len))>=8 and (ca in cb or cb in ca):return 0.97
        return difflib.SequenceMatcher(None,ca,cb).ratio()

    def _radar_links_reverse(self):
        data=self._radar_load();rev={}
        for wa,key in (data.get("links",{}) or {}).items():
            if str(key or ""):rev[str(key)]=str(wa or "")
        return rev

    def _radar_auto_link_all(self,save=True):
        data=self._radar_load();clients=self._radar_all_clients();contacts=self._radar_known_whatsapp_contacts()
        links=data.setdefault("links",{});rev=self._radar_links_reverse()
        used=set(str(x) for x in links.keys())
        matched=[];suggested=[]
        for key,c in clients.items():
            key=str(key)
            if key in rev:continue
            cname=str((c or {}).get("name") or "").strip()
            if not cname:continue
            scored=[]
            for wa in contacts:
                if wa in used:continue
                sc=self._radar_match_name(cname,wa)
                if sc>=0.82:scored.append((sc,wa))
            scored.sort(reverse=True)
            if not scored:continue
            best_sc,best=scored[0]
            second=scored[1][0] if len(scored)>1 else 0.0
            # Auto salva so quando a correspondencia e muito forte e sem empate proximo.
            if best_sc>=0.94 and (best_sc-second)>=0.035:
                links[best]=key;used.add(best);rev[key]=best
                matched.append({"key":key,"client":cname,"whatsapp":best,"score":best_sc})
            else:
                suggested.append({"key":key,"client":cname,"whatsapp":best,"score":best_sc})
        if save and matched:self._radar_save()
        return matched,suggested

    def _radar_bulk_link_dialog(self,parent=None,on_done=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QComboBox,QMessageBox,QCheckBox
        from PyQt6.QtCore import Qt
        dlg=QDialog(parent or self);dlg.setWindowTitle("🔗 Vincular carteira ao WhatsApp");dlg.resize(1080,720)
        lay=QVBoxLayout(dlg)
        title=QLabel("🔗 VINCULAR TODA A CARTEIRA");title.setStyleSheet("font-size:20px;font-weight:900;color:#0B3349;");lay.addWidget(title)
        info=QLabel("O ALIYVO memoriza qual conversa do WhatsApp pertence a cada cadastro. Vínculos exatos ficam salvos automaticamente; os restantes podem ser escolhidos abaixo.")
        info.setWordWrap(True);info.setStyleSheet("color:#60717F;font-weight:600;");lay.addWidget(info)

        stat=QLabel();stat.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:8px;font-weight:800;");lay.addWidget(stat)

        table=QTableWidget(0,4);table.setHorizontalHeaderLabels(["Cliente da carteira","Código","WhatsApp vinculado","Situação"])
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        lay.addWidget(table,1)

        contacts=self._radar_known_whatsapp_contacts()
        selector=QComboBox();selector.setEditable(True);selector.addItem("— escolher contato do WhatsApp —","")
        for n in contacts:selector.addItem(n,n)
        selector.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        rowpick=QHBoxLayout();rowpick.addWidget(QLabel("Vincular linha selecionada a:"));rowpick.addWidget(selector,1)
        save_one=QPushButton("🔗 Salvar vínculo");unlink=QPushButton("Desvincular");rowpick.addWidget(save_one);rowpick.addWidget(unlink);lay.addLayout(rowpick)

        only_unlinked=QCheckBox("Mostrar somente não vinculados");only_unlinked.setChecked(True)
        lay.addWidget(only_unlinked)

        def refresh():
            clients=self._radar_all_clients();rev=self._radar_links_reverse()
            rows=[]
            for key,c in clients.items():
                wa=rev.get(str(key),"")
                if only_unlinked.isChecked() and wa:continue
                rows.append((str(key),str((c or {}).get("name") or ""),str((c or {}).get("code") or ""),wa))
            rows.sort(key=lambda x:(0 if not x[3] else 1,x[1].lower()))
            table.setRowCount(len(rows))
            linked=len(rev);total=len(clients)
            stat.setText(f"{linked} de {total} clientes vinculados • {max(0,total-linked)} ainda sem vínculo • {len(contacts)} contatos conhecidos no WhatsApp")
            for i,(key,name,code,wa) in enumerate(rows):
                vals=[name or key,code,wa or "—",("✅ Memorizado" if wa else "⚠ Não vinculado")]
                for j,v in enumerate(vals):
                    it=QTableWidgetItem(v);it.setData(Qt.ItemDataRole.UserRole,key);table.setItem(i,j,it)

        def selected_key():
            r=table.currentRow();it=table.item(r,0) if r>=0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def save_selected():
            key=selected_key();wa=str(selector.currentData() or selector.currentText() or "").strip()
            if not key:
                QMessageBox.information(dlg,"Vínculos","Selecione um cliente da carteira.");return
            if not wa or wa.startswith("—"):
                QMessageBox.information(dlg,"Vínculos","Escolha o contato correspondente no WhatsApp.");return
            data=self._radar_load();links=data.setdefault("links",{})
            # Cada conversa aponta para um unico cadastro.
            for oldwa,oldkey in list(links.items()):
                if str(oldkey)==key or str(oldwa)==wa:links.pop(oldwa,None)
            links[wa]=key;self._radar_save();refresh()
            selector.setCurrentIndex(0)

        def unlink_selected():
            key=selected_key()
            if not key:return
            data=self._radar_load();links=data.setdefault("links",{})
            for wa,k in list(links.items()):
                if str(k)==key:links.pop(wa,None)
            self._radar_save();refresh()

        def auto_link():
            matched,suggested=self._radar_auto_link_all(True);refresh()
            QMessageBox.information(dlg,"Vínculo automático",f"{len(matched)} clientes foram vinculados automaticamente por nome com alta confiança.\n\nOs demais ficaram para conferência manual.")

        def link_current():
            key=selected_key();wa=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if not key:
                QMessageBox.information(dlg,"Vínculos","Selecione um cliente da carteira.");return
            if not wa:
                QMessageBox.information(dlg,"Vínculos","Abra primeiro a conversa correta no WhatsApp.");return
            data=self._radar_load();links=data.setdefault("links",{})
            for oldwa,oldkey in list(links.items()):
                if str(oldkey)==key or str(oldwa)==wa:links.pop(oldwa,None)
            links[wa]=key;self._radar_save();refresh()

        bar=QHBoxLayout();auto=QPushButton("✨ Auto-vincular nomes iguais");current=QPushButton("💬 Usar conversa atual");close=QPushButton("Concluir")
        bar.addWidget(auto);bar.addWidget(current);bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        save_one.clicked.connect(save_selected);unlink.clicked.connect(unlink_selected);auto.clicked.connect(auto_link);current.clicked.connect(link_current)
        only_unlinked.toggled.connect(lambda _=False:refresh())
        close.clicked.connect(dlg.accept)
        refresh();dlg.exec()
        if callable(on_done):on_done()

'''
text=text[:idx]+bulk+text[idx:]

# Adiciona botão em Radar.
old='''        hist_btn.clicked.connect(lambda:self._radar_import("history",dlg,refresh))
        rec_btn.clicked.connect(lambda:self._radar_import("recurrence",dlg,refresh))
        row=QHBoxLayout();openb=QPushButton("💬 Abrir cliente");linkb=QPushButton("🔗 Vincular conversa atual");reloadb=QPushButton("↻ Atualizar painel");close=QPushButton("Fechar")
        row.addWidget(openb);row.addWidget(linkb);row.addWidget(reloadb);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        openb.clicked.connect(open_selected);linkb.clicked.connect(link_current);reloadb.clicked.connect(refresh);close.clicked.connect(dlg.accept);table.cellDoubleClicked.connect(lambda _r,_c:open_selected())
'''
new='''        hist_btn.clicked.connect(lambda:self._radar_import("history",dlg,refresh))
        rec_btn.clicked.connect(lambda:self._radar_import("recurrence",dlg,refresh))
        row=QHBoxLayout();openb=QPushButton("💬 Abrir cliente");bulklink=QPushButton("🔗 Vincular toda a carteira");linkb=QPushButton("🔗 Vincular conversa atual");reloadb=QPushButton("↻ Atualizar painel");close=QPushButton("Fechar")
        row.addWidget(openb);row.addWidget(bulklink);row.addWidget(linkb);row.addWidget(reloadb);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        openb.clicked.connect(open_selected);bulklink.clicked.connect(lambda:self._radar_bulk_link_dialog(dlg,refresh));linkb.clicked.connect(link_current);reloadb.clicked.connect(refresh);close.clicked.connect(dlg.accept);table.cellDoubleClicked.connect(lambda _r,_c:open_selected())
'''
if text.count(old)!=1:
    raise SystemExit('bloco de botoes Radar nao encontrado')
text=text.replace(old,new,1)

main.write_text(text,encoding='utf-8')
print('PATCH_RADAR_LINKS_V2306=OK')

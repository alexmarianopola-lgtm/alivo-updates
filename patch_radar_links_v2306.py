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


# ===== Melhoria de leitura comercial do Radar =====
# Ranking por cliente: evita que um cliente com centenas de itens domine a prioridade.
start=text.index('    def _radar_priorities(self):\n')
end=text.index('    def _radar_source_status(self,kind):\n',start)
better_priorities=r'''    def _radar_priorities(self):
        data=self._radar_load();clients=self._radar_all_clients();rows={}
        def row_for(key):
            if key not in rows:
                cc=clients.get(key,{})
                rows[key]={"key":key,"code":str(cc.get("code") or ""),"name":str(cc.get("name") or ""),"score":0,"reasons":[],"trend":None,"due":[]}
            return rows[key]

        for key,h in (data.get("history",{}).get("clients",{}) or {}).items():
            if not isinstance(h,dict):continue
            r=row_for(str(key));tr=h.get("trend_pct");r["trend"]=tr
            if tr is not None and tr<=-40:r["score"]+=45;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")
            elif tr is not None and tr<=-25:r["score"]+=30;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")
            elif tr is not None and tr<=-15:r["score"]+=18;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")

        by_client={}
        for it in (data.get("recurrence",{}).get("items",[]) or []):
            if not isinstance(it,dict):continue
            code=str(it.get("client_code") or "");key=code or ("NOME:"+self._radar_norm(it.get("client_name")))
            by_client.setdefault(key,[]).append(it)

        for key,items in by_client.items():
            r=row_for(key)
            relevant=[]
            for it in items:
                d=it.get("days_to_next")
                if bool(it.get("overdue")) or (d is not None and int(d)<=7) or bool(it.get("alert")):
                    relevant.append(it)
            relevant.sort(key=lambda x:(0 if x.get("overdue") else 1,x.get("days_to_next") if x.get("days_to_next") is not None else 99999,-int(x.get("score") or 0)))
            r["due"]=relevant[:5]
            overdue=[x for x in relevant if x.get("overdue")]
            soon=[x for x in relevant if not x.get("overdue") and x.get("days_to_next") is not None and int(x.get("days_to_next"))<=7]
            # Pontuação por situação do cliente, não pela quantidade bruta de linhas.
            if overdue:
                r["score"]+=55+min(20,len(overdue)*4)
                r["reasons"].append(f"{len(overdue)} recompra(s) atrasada(s)")
            elif soon:
                r["score"]+=32+min(12,len(soon)*3)
                r["reasons"].append(f"{len(soon)} recompra(s) nos próximos 7 dias")
            elif relevant:
                r["score"]+=18
                r["reasons"].append(f"{len(relevant)} produto(s) em alerta")
            # Expõe no máximo 3 peças para a linha ficar legível.
            for it in relevant[:3]:
                prod=str(it.get("product") or it.get("product_code") or "produto")
                d=it.get("days_to_next")
                if it.get("overdue"):
                    label=f"{prod} atrasado {abs(int(d or 0))}d" if d is not None else f"{prod} atrasado"
                elif d is not None:
                    label=f"{prod} em {int(d)}d"
                else:
                    label=f"{prod} em alerta"
                r["reasons"].append(label)

        out=[x for x in rows.values() if x.get("score",0)>0]
        out.sort(key=lambda x:(-int(x.get("score") or 0),str(x.get("name") or "").lower()))
        return out

'''
text=text[:start]+better_priorities+text[end:]

# Cartões passam a mostrar quantidade de CLIENTES, não linhas de produto.
old_cards='''            overdue=sum(1 for x in (data.get("recurrence",{}).get("items",[]) or []) if x.get("overdue"))
            upcoming=sum(1 for x in (data.get("recurrence",{}).get("items",[]) or []) if x.get("days_to_next") is not None and 0<int(x.get("days_to_next"))<=7)
            falling=sum(1 for x in (data.get("history",{}).get("clients",{}) or {}).values() if isinstance(x,dict) and x.get("trend_pct") is not None and x.get("trend_pct")<=-15)
            linked=len(data.get("links",{}) or {})
            over.setText(f"🔴 {overdue}\\nRECOMPRAS ATRASADAS");soon.setText(f"🟡 {upcoming}\\nPRÓXIMOS 7 DIAS");drop.setText(f"📉 {falling}\\nCLIENTES EM QUEDA");links.setText(f"🔗 {linked}\\nVÍNCULOS WHATSAPP")
'''
new_cards='''            recitems=(data.get("recurrence",{}).get("items",[]) or [])
            overdue_clients=set()
            upcoming_clients=set()
            for x in recitems:
                if not isinstance(x,dict):continue
                key=str(x.get("client_code") or ("NOME:"+self._radar_norm(x.get("client_name"))))
                d=x.get("days_to_next")
                if x.get("overdue"):overdue_clients.add(key)
                elif d is not None and 0<int(d)<=7:upcoming_clients.add(key)
            falling=sum(1 for x in (data.get("history",{}).get("clients",{}) or {}).values() if isinstance(x,dict) and x.get("trend_pct") is not None and x.get("trend_pct")<=-15)
            linked=len(set(str(v) for v in (data.get("links",{}) or {}).values() if v))
            over.setText(f"🔴 {len(overdue_clients)}\\nCLIENTES PARA CHAMAR");soon.setText(f"🟡 {len(upcoming_clients)}\\nRECOMPRA EM ATÉ 7 DIAS");drop.setText(f"📉 {falling}\\nCLIENTES EM QUEDA");links.setText(f"🔗 {linked}\\nCLIENTES VINCULADOS")
'''
if text.count(old_cards)!=1:raise SystemExit('cards Radar nao encontrados')
text=text.replace(old_cards,new_cards,1)

# Nomes das colunas mais comerciais.
text=text.replace('table.setHorizontalHeaderLabels(["Prioridade","Cliente","Motivo","Tendência","Recompras","Vínculo WhatsApp"])',
                  'table.setHorizontalHeaderLabels(["Prioridade","Cliente","Por que chamar","Tendência","Oportunidades","WhatsApp"])',1)

# Coluna de oportunidades conta só itens relevantes exibíveis (máximo 5).
text=text.replace('due=len(r.get("due") or []);key=str(r.get("key") or "")',
                  'due=len(r.get("due") or []);key=str(r.get("key") or "")',1)

# Painel de detalhes do cliente selecionado.
needle='''        current=QLabel("");current.setWordWrap(True);current.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:8px;font-weight:700;");lay.addWidget(current)
'''
replacement='''        detail=QLabel("Selecione um cliente para ver as melhores oportunidades.");detail.setWordWrap(True);detail.setMinimumHeight(92);detail.setStyleSheet("background:#FFF9E8;color:#4D4300;border-radius:8px;padding:9px;font-weight:700;");lay.addWidget(detail)
        current=QLabel("");current.setWordWrap(True);current.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:8px;font-weight:700;");lay.addWidget(current)
'''
if text.count(needle)!=1:raise SystemExit('painel current Radar nao encontrado')
text=text.replace(needle,replacement,1)

# Atualiza detalhe ao selecionar uma linha.
needle2='''        def selected_key():
            row=table.currentRow()
            it=table.item(row,0) if row>=0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def link_current():
'''
replacement2='''        def selected_key():
            row=table.currentRow()
            it=table.item(row,0) if row>=0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def update_detail():
            key=selected_key()
            if not key:
                detail.setText("Selecione um cliente para ver as melhores oportunidades.");return
            prof=self._radar_profile_by_code(key);h=prof.get("history") or {};rec=prof.get("recurrence") or []
            cli=self._radar_all_clients().get(key) or {}
            lines=[str(cli.get("name") or key)]
            tr=h.get("trend_pct")
            if tr is not None:lines.append(f"Faturamento: {tr:+.1f}% nos últimos 3 meses vs. 3 anteriores")
            hot=[]
            for x in rec:
                d=x.get("days_to_next")
                if x.get("overdue") or (d is not None and int(d)<=7) or x.get("alert"):hot.append(x)
            if hot:
                lines.append("Melhores oportunidades:")
                for x in hot[:5]:
                    prod=str(x.get("product") or x.get("product_code") or "produto")
                    d=x.get("days_to_next")
                    if x.get("overdue"):when=f"ATRASADO {abs(int(d or 0))} dia(s)" if d is not None else "ATRASADO"
                    elif d is not None:when=f"previsto em {int(d)} dia(s)"
                    else:when="em alerta"
                    lines.append(f"• {prod} — {when}")
            else:lines.append("Nenhuma recompra urgente detectada.")
            detail.setText("\\n".join(lines))

        def link_current():
'''
if text.count(needle2)!=1:raise SystemExit('selected_key Radar nao encontrado')
text=text.replace(needle2,replacement2,1)

needle3='''        openb.clicked.connect(open_selected);bulklink.clicked.connect(lambda:self._radar_bulk_link_dialog(dlg,refresh));linkb.clicked.connect(link_current);reloadb.clicked.connect(refresh);close.clicked.connect(dlg.accept);table.cellDoubleClicked.connect(lambda _r,_c:open_selected())
        refresh();dlg.exec()
'''
replacement3='''        openb.clicked.connect(open_selected);bulklink.clicked.connect(lambda:self._radar_bulk_link_dialog(dlg,refresh));linkb.clicked.connect(link_current);reloadb.clicked.connect(refresh);close.clicked.connect(dlg.accept);table.cellDoubleClicked.connect(lambda _r,_c:open_selected())
        table.itemSelectionChanged.connect(update_detail)
        refresh();dlg.exec()
'''
if text.count(needle3)!=1:raise SystemExit('connect Radar nao encontrado')
text=text.replace(needle3,replacement3,1)

main.write_text(text,encoding='utf-8')
print('PATCH_RADAR_LINKS_V2306=OK')

from pathlib import Path
import sys,re

root=Path(sys.argv[1])
main=root/'_app'/'main.py'
text=main.read_text(encoding='utf-8')

if 'ALIYVO_VERSION = "0.23.06"' not in text:
    raise SystemExit('base esperada 0.23.06 nao encontrada')
text=text.replace('ALIYVO_VERSION = "0.23.06"','ALIYVO_VERSION = "0.23.07"',1)
text=text.replace('aliyvo_version="0.23.06"','aliyvo_version="0.23.07"')

def replace_method(name,new_src):
    global text
    pat=rf'(?ms)^    def {re.escape(name)}\(.*?(?=^    def |\Z)'
    m=re.search(pat,text)
    if not m: raise SystemExit(f'metodo {name} nao encontrado')
    text=text[:m.start()]+new_src.rstrip()+"\n\n"+text[m.end():]

replace_method('_radar_all_clients',r'''
    def _radar_all_clients(self):
        # REGRA DE NEGOCIO: a carteira oficial vem SOMENTE do histórico de 12 meses.
        # A recorrência nunca cria clientes novos no CRM.
        data=self._radar_load();out={}
        for code,x in (data.get("history",{}).get("clients",{}) or {}).items():
            if not isinstance(x,dict):continue
            key=str(code)
            out[key]={"code":str(x.get("code") or code),"name":str(x.get("name") or "")}
        return out
''')

replace_method('_radar_profile_by_code',r'''
    def _radar_profile_by_code(self,key):
        data=self._radar_load()
        clients=self._radar_all_clients()
        if str(key) not in clients:return {"history":{},"recurrence":[]}
        hist=(data.get("history",{}).get("clients",{}) or {}).get(str(key)) or {}
        cname=self._radar_norm((clients.get(str(key)) or {}).get("name"))
        rec=[]
        for x in (data.get("recurrence",{}).get("items",[]) or []):
            if not isinstance(x,dict):continue
            same_code=str(x.get("client_code") or "")==str(key)
            same_name=bool(cname and self._radar_norm(x.get("client_name"))==cname)
            if same_code or same_name:rec.append(x)
        rec.sort(key=lambda x:(0 if x.get("overdue") else 1,
                               x.get("days_to_next") if x.get("days_to_next") is not None else 99999,
                               -float(x.get("purchases") or 0),
                               -int(x.get("score") or 0)))
        return {"history":hist if isinstance(hist,dict) else {},"recurrence":rec}
''')

replace_method('_radar_links_reverse',r'''
    def _radar_links_reverse(self):
        # Um cadastro pode ter VARIOS compradores/contatos do WhatsApp.
        data=self._radar_load();rev={}
        for wa,key in (data.get("links",{}) or {}).items():
            key=str(key or "");wa=str(wa or "").strip()
            if not key or not wa:continue
            rev.setdefault(key,[]).append(wa)
        for key in rev:rev[key]=sorted(set(rev[key]),key=str.lower)
        return rev

    def _radar_links_label(self,key):
        contacts=self._radar_links_reverse().get(str(key),[])
        if not contacts:return "Não vinculado"
        if len(contacts)==1:return contacts[0]
        shown=" • ".join(contacts[:3])
        if len(contacts)>3:shown+=f" • +{len(contacts)-3}"
        return f"{len(contacts)} contatos: {shown}"
''')

replace_method('_radar_auto_link_all',r'''
    def _radar_auto_link_all(self,save=True):
        data=self._radar_load();clients=self._radar_all_clients();contacts=self._radar_known_whatsapp_contacts()
        links=data.setdefault("links",{});rev=self._radar_links_reverse()
        used=set(str(x) for x in links.keys())
        matched=[];suggested=[]
        for key,c in clients.items():
            key=str(key)
            # Se já existe ao menos um vínculo, não tenta adivinhar compradores extras.
            if rev.get(key):continue
            cname=str((c or {}).get("name") or "").strip()
            if not cname:continue
            scored=[]
            for wa in contacts:
                if wa in used:continue
                sc=self._radar_match_name(cname,wa)
                if sc>=0.82:scored.append((sc,wa))
            scored.sort(reverse=True)
            if not scored:continue
            best_sc,best=scored[0];second=scored[1][0] if len(scored)>1 else 0.0
            if best_sc>=0.94 and (best_sc-second)>=0.035:
                links[best]=key;used.add(best)
                matched.append({"key":key,"client":cname,"whatsapp":best,"score":best_sc})
            else:
                suggested.append({"key":key,"client":cname,"whatsapp":best,"score":best_sc})
        if save and matched:self._radar_save()
        return matched,suggested
''')

replace_method('_radar_bulk_link_dialog',r'''
    def _radar_bulk_link_dialog(self,parent=None,on_done=None):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QComboBox,QMessageBox,QCheckBox
        from PyQt6.QtCore import Qt
        dlg=QDialog(parent or self);dlg.setWindowTitle("🔗 Vincular carteira ao WhatsApp");dlg.resize(1120,740)
        lay=QVBoxLayout(dlg)
        title=QLabel("🔗 VINCULAR TODA A CARTEIRA");title.setStyleSheet("font-size:20px;font-weight:900;color:#0B3349;");lay.addWidget(title)
        info=QLabel("A carteira abaixo vem SOMENTE do relatório dos últimos 12 meses. Um mesmo cliente pode ter vários compradores/contatos do WhatsApp.")
        info.setWordWrap(True);info.setStyleSheet("color:#60717F;font-weight:600;");lay.addWidget(info)
        stat=QLabel();stat.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:8px;font-weight:800;");lay.addWidget(stat)

        table=QTableWidget(0,4);table.setHorizontalHeaderLabels(["Cliente da minha carteira","Código","WhatsApps vinculados","Situação"])
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
        rowpick=QHBoxLayout();rowpick.addWidget(QLabel("Adicionar comprador/contato:"));rowpick.addWidget(selector,1)
        add=QPushButton("➕ Adicionar vínculo");unlink=QPushButton("Remover todos os vínculos")
        rowpick.addWidget(add);rowpick.addWidget(unlink);lay.addLayout(rowpick)

        only_unlinked=QCheckBox("Mostrar somente clientes sem nenhum vínculo");only_unlinked.setChecked(True);lay.addWidget(only_unlinked)

        def refresh():
            clients=self._radar_all_clients();rev=self._radar_links_reverse();rows=[]
            for key,c in clients.items():
                was=rev.get(str(key),[])
                if only_unlinked.isChecked() and was:continue
                rows.append((str(key),str((c or {}).get("name") or ""),str((c or {}).get("code") or ""),was))
            rows.sort(key=lambda x:(0 if not x[3] else 1,x[1].lower()))
            table.setRowCount(len(rows))
            linked=sum(1 for k in clients if rev.get(str(k)));total=len(clients)
            total_contacts=sum(len(rev.get(str(k),[])) for k in clients)
            stat.setText(f"{linked} de {total} clientes vinculados • {total-linked} sem vínculo • {total_contacts} contatos memorizados • {len(contacts)} contatos conhecidos no WhatsApp")
            for i,(key,name,code,was) in enumerate(rows):
                label="—" if not was else (" • ".join(was[:4])+(f" • +{len(was)-4}" if len(was)>4 else ""))
                state="⚠ Não vinculado" if not was else f"✅ {len(was)} contato(s)"
                vals=[name or key,code,label,state]
                for j,v in enumerate(vals):
                    it=QTableWidgetItem(v);it.setData(Qt.ItemDataRole.UserRole,key);table.setItem(i,j,it)

        def selected_key():
            r=table.currentRow();it=table.item(r,0) if r>=0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def add_selected():
            key=selected_key();wa=str(selector.currentData() or selector.currentText() or "").strip()
            if not key:
                QMessageBox.information(dlg,"Vínculos","Selecione um cliente da carteira.");return
            if not wa or wa.startswith("—"):
                QMessageBox.information(dlg,"Vínculos","Escolha o comprador/contato do WhatsApp.");return
            data=self._radar_load();links=data.setdefault("links",{})
            # Uma conversa só pertence a um cadastro, mas um cadastro pode receber muitas conversas.
            links.pop(wa,None);links[wa]=key
            self._radar_save();refresh();selector.setCurrentIndex(0)

        def unlink_all():
            key=selected_key()
            if not key:return
            data=self._radar_load();links=data.setdefault("links",{})
            for wa,k in list(links.items()):
                if str(k)==key:links.pop(wa,None)
            self._radar_save();refresh()

        def auto_link():
            matched,_=self._radar_auto_link_all(True);refresh()
            QMessageBox.information(dlg,"Vínculo automático",f"{len(matched)} cliente(s) vinculado(s) automaticamente por nome com alta confiança.\n\nCompradores adicionais podem ser adicionados manualmente ao mesmo cliente.")

        def link_current():
            key=selected_key();wa=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if not key:
                QMessageBox.information(dlg,"Vínculos","Selecione um cliente da carteira.");return
            if not wa:
                QMessageBox.information(dlg,"Vínculos","Abra primeiro a conversa correta no WhatsApp.");return
            data=self._radar_load();links=data.setdefault("links",{})
            links.pop(wa,None);links[wa]=key;self._radar_save();refresh()

        bar=QHBoxLayout();auto=QPushButton("✨ Auto-vincular nomes iguais");current=QPushButton("💬 Adicionar conversa atual");close=QPushButton("Concluir")
        bar.addWidget(auto);bar.addWidget(current);bar.addStretch(1);bar.addWidget(close);lay.addLayout(bar)
        add.clicked.connect(add_selected);unlink.clicked.connect(unlink_all);auto.clicked.connect(auto_link);current.clicked.connect(link_current)
        only_unlinked.toggled.connect(lambda _=False:refresh());close.clicked.connect(dlg.accept)
        refresh();dlg.exec()
        if callable(on_done):on_done()
''')

# Substitui o ranking para considerar SOMENTE a carteira oficial.
replace_method('_radar_priorities',r'''
    def _radar_priorities(self):
        data=self._radar_load();clients=self._radar_all_clients();rows={}
        def row_for(key):
            if key not in clients:return None
            if key not in rows:
                cc=clients.get(key,{})
                rows[key]={"key":key,"code":str(cc.get("code") or ""),"name":str(cc.get("name") or ""),"score":0,"reasons":[],"trend":None,"due":[]}
            return rows[key]
        for key,h in (data.get("history",{}).get("clients",{}) or {}).items():
            if not isinstance(h,dict):continue
            key=str(key);r=row_for(key)
            if r is None:continue
            tr=h.get("trend_pct");r["trend"]=tr
            if tr is not None and tr<=-40:r["score"]+=45;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")
            elif tr is not None and tr<=-25:r["score"]+=30;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")
            elif tr is not None and tr<=-15:r["score"]+=18;r["reasons"].append(f"compras caíram {abs(tr):.0f}%")

        by_client={}
        # Associa recorrência por código; se o relatório vier com código diferente,
        # tenta casar pelo nome EXATO com um cliente da carteira.
        name_to_key={}
        for k,c in clients.items():
            n=self._radar_norm((c or {}).get("name"))
            if n:name_to_key.setdefault(n,[]).append(k)
        for it in (data.get("recurrence",{}).get("items",[]) or []):
            if not isinstance(it,dict):continue
            code=str(it.get("client_code") or "")
            key=code if code in clients else ""
            if not key:
                nn=self._radar_norm(it.get("client_name"));ks=name_to_key.get(nn,[])
                if len(ks)==1:key=str(ks[0])
            if not key:continue
            by_client.setdefault(key,[]).append(it)

        for key,items in by_client.items():
            r=row_for(key)
            if r is None:continue
            relevant=[]
            for it in items:
                d=it.get("days_to_next")
                if bool(it.get("overdue")) or (d is not None and int(d)<=7) or bool(it.get("alert")):relevant.append(it)
            relevant.sort(key=lambda x:(0 if x.get("overdue") else 1,x.get("days_to_next") if x.get("days_to_next") is not None else 99999,-float(x.get("purchases") or 0)))
            r["due"]=relevant[:5]
            overdue=[x for x in relevant if x.get("overdue")]
            soon=[x for x in relevant if not x.get("overdue") and x.get("days_to_next") is not None and int(x.get("days_to_next"))<=7]
            if overdue:r["score"]+=55+min(20,len(overdue)*4);r["reasons"].append(f"{len(overdue)} recompra(s) atrasada(s)")
            elif soon:r["score"]+=32+min(12,len(soon)*3);r["reasons"].append(f"{len(soon)} recompra(s) nos próximos 7 dias")
            elif relevant:r["score"]+=18;r["reasons"].append(f"{len(relevant)} produto(s) em alerta")
            for it in relevant[:2]:
                prod=str(it.get("product") or it.get("product_code") or "produto");d=it.get("days_to_next")
                if it.get("overdue"):label=f"{prod} atrasado {abs(int(d or 0))}d" if d is not None else f"{prod} atrasado"
                elif d is not None:label=f"{prod} em {int(d)}d"
                else:label=f"{prod} em alerta"
                r["reasons"].append(label)
        out=[x for x in rows.values() if x.get("score",0)>0]
        out.sort(key=lambda x:(-int(x.get("score") or 0),str(x.get("name") or "").lower()))
        return out
''')

# Novos métodos para painel lateral "O QUE OFERECER AGORA".
anchor='    def _radar_source_status(self,kind):\n'
idx=text.index(anchor)
offer_methods=r'''
    def _radar_offer_items_for_key(self,key,limit=8):
        p=self._radar_profile_by_code(str(key));rec=p.get("recurrence") or []
        hot=[];regular=[]
        for x in rec:
            d=x.get("days_to_next")
            if x.get("overdue") or (d is not None and int(d)<=7) or x.get("alert"):hot.append(x)
            else:regular.append(x)
        hot.sort(key=lambda x:(0 if x.get("overdue") else 1,x.get("days_to_next") if x.get("days_to_next") is not None else 99999,-float(x.get("purchases") or 0)))
        regular.sort(key=lambda x:(-float(x.get("purchases") or 0),x.get("days_to_next") if x.get("days_to_next") is not None else 99999))
        out=hot+regular
        return out[:max(1,int(limit or 8))]

    def _radar_offer_text_for_contact(self,whatsapp_name,limit=3):
        p=self._radar_contact_payload(whatsapp_name)
        if not p:return ""
        c=p.get("client") or {};code=str(c.get("code") or "")
        key=code if code in self._radar_all_clients() else ""
        if not key:return ""
        items=self._radar_offer_items_for_key(key,limit)
        if not items:return f"🎯 O QUE OFERECER AGORA\n{c.get('name') or whatsapp_name}\nSem recorrência suficiente ainda."
        lines=[f"🎯 O QUE OFERECER AGORA",str(c.get("name") or whatsapp_name)]
        for x in items[:limit]:
            prod=str(x.get("product") or x.get("product_code") or "produto");d=x.get("days_to_next")
            if x.get("overdue"):when=f"atrasado {abs(int(d or 0))}d" if d is not None else "atrasado"
            elif d is not None and int(d)<=7:when=f"em {int(d)}d"
            else:when="recorrente"
            lines.append(f"• {prod[:32]} — {when}")
        return "\n".join(lines)

    def _radar_refresh_offer_panel(self,whatsapp_name=""):
        card=getattr(self,"radar_offer_card",None);btn=getattr(self,"radar_offer_button",None)
        if card is None:return
        name=str(whatsapp_name or getattr(self,"_diagnostic_active_name","") or "").strip()
        txt=self._radar_offer_text_for_contact(name,3) if name else ""
        if txt:
            card.setText(txt)
            if btn is not None:btn.setEnabled(True);btn.setText("🎯 Ver oportunidades deste cliente")
        else:
            card.setText("🎯 O QUE OFERECER AGORA\nAbra uma conversa vinculada ao Radar.")
            if btn is not None:btn.setEnabled(False);btn.setText("🎯 Ver oportunidades deste cliente")

    def _radar_current_offer_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QMessageBox
        name=str(getattr(self,"_diagnostic_active_name","") or "").strip()
        p=self._radar_contact_payload(name)
        if not p:
            QMessageBox.information(self,"Radar","Esta conversa ainda não está vinculada a um cliente da sua carteira.");return
        c=p.get("client") or {};code=str(c.get("code") or "");key=code if code in self._radar_all_clients() else ""
        if not key:return
        prof=self._radar_profile_by_code(key);h=prof.get("history") or {};items=self._radar_offer_items_for_key(key,10)
        dlg=QDialog(self);dlg.setWindowTitle("🎯 O que oferecer agora");dlg.resize(900,600)
        lay=QVBoxLayout(dlg)
        head=QLabel(f"🎯 O QUE OFERECER AGORA — {c.get('name') or name}")
        head.setStyleSheet("font-size:18px;font-weight:900;color:#0B3349;");lay.addWidget(head)
        tr=h.get("trend_pct");avg=float(h.get("average") or 0)
        info=QLabel((f"Código {code} • Média 12 meses R$ {avg:,.2f}".replace(",", "X").replace(".",",").replace("X","."))
                    +(f" • Tendência {tr:+.1f}%" if tr is not None else ""))
        info.setStyleSheet("font-weight:700;color:#60717F;");lay.addWidget(info)
        table=QTableWidget(0,6);table.setHorizontalHeaderLabels(["Prioridade","Produto","Última compra","Ciclo médio","Próxima/atraso","Compras"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers);table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        table.setRowCount(len(items))
        for i,x in enumerate(items):
            d=x.get("days_to_next")
            if x.get("overdue"):prio="🔴 OFERECER";when=f"{abs(int(d or 0))} dia(s) atrasado"
            elif d is not None and int(d)<=7:prio="🟡 EM BREVE";when=f"em {int(d)} dia(s)"
            else:prio="🔵 RECORRENTE";when=str(x.get("next_purchase") or "-")
            vals=[prio,str(x.get("product") or x.get("product_code") or "produto"),str(x.get("last_purchase") or "-"),
                  (f"{float(x.get('avg_days')):.0f} dias" if x.get("avg_days") else "-"),when,
                  (f"{float(x.get('purchases')):.0f}" if x.get("purchases") else "-")]
            for j,v in enumerate(vals):table.setItem(i,j,QTableWidgetItem(v))
        lay.addWidget(table,1)
        hint=QLabel("Use esses itens como oportunidade de abordagem; o histórico sugere recorrência, não garante que o cliente precise comprar agora.")
        hint.setWordWrap(True);hint.setStyleSheet("color:#6C7780;font-size:10px;");lay.addWidget(hint)
        row=QHBoxLayout();close=QPushButton("Fechar");row.addStretch(1);row.addWidget(close);lay.addLayout(row);close.clicked.connect(dlg.accept)
        dlg.exec()

'''
text=text[:idx]+offer_methods+text[idx:]

# Painel lateral persistente.
needle='''        q.addWidget(self.quick_update)
        q.addWidget(self.quick_plate)
        q.addStretch(1)
'''
replacement='''        q.addWidget(self.quick_update)
        q.addWidget(self.quick_plate)
        self.radar_offer_card=QLabel("🎯 O QUE OFERECER AGORA\\nAbra uma conversa vinculada ao Radar.")
        self.radar_offer_card.setWordWrap(True)
        self.radar_offer_card.setStyleSheet("background:#FFF7D6;color:#4D4300;border:1px solid #E8CF62;border-radius:7px;padding:8px;font-size:9px;font-weight:700;")
        self.radar_offer_button=QPushButton("🎯 Ver oportunidades deste cliente")
        self.radar_offer_button.setEnabled(False)
        self.radar_offer_button.clicked.connect(self._radar_current_offer_dialog)
        q.addWidget(self.radar_offer_card)
        q.addWidget(self.radar_offer_button)
        q.addStretch(1)
'''
if text.count(needle)!=1:raise SystemExit('quick panel anchor nao encontrado')
text=text.replace(needle,replacement,1)

# Atualiza o card sempre que a conversa ativa muda, reutilizando o scan já existente.
needle='''        self._diagnostic_active_name=name
        try:self._diagnostic_live_call_update(result.get("live_call"),now,name)
'''
replacement='''        self._diagnostic_active_name=name
        try:self._radar_refresh_offer_panel(name)
        except Exception:pass
        try:self._diagnostic_live_call_update(result.get("live_call"),now,name)
'''
if text.count(needle)!=1:raise SystemExit('diagnostic active anchor nao encontrado')
text=text.replace(needle,replacement,1)

# Tabela principal: mostra vários contatos.
text=text.replace('reverse={str(v):k for k,v in (data.get("links",{}) or {}).items()}','reverse=self._radar_links_reverse()',1)
text=text.replace('reverse.get(key,"Não vinculado")','self._radar_links_label(key)',1)

# Cartões do Radar: contam somente clientes da carteira oficial.
needle='''            recitems=(data.get("recurrence",{}).get("items",[]) or [])
            overdue_clients=set()
            upcoming_clients=set()
            for x in recitems:
                if not isinstance(x,dict):continue
                key=str(x.get("client_code") or ("NOME:"+self._radar_norm(x.get("client_name"))))
                d=x.get("days_to_next")
                if x.get("overdue"):overdue_clients.add(key)
                elif d is not None and 0<int(d)<=7:upcoming_clients.add(key)
'''
replacement='''            recitems=(data.get("recurrence",{}).get("items",[]) or [])
            portfolio=self._radar_all_clients();portfolio_names={}
            for pk,pc in portfolio.items():
                nn=self._radar_norm((pc or {}).get("name"))
                if nn:portfolio_names.setdefault(nn,[]).append(pk)
            overdue_clients=set();upcoming_clients=set()
            for x in recitems:
                if not isinstance(x,dict):continue
                code=str(x.get("client_code") or "");key=code if code in portfolio else ""
                if not key:
                    ks=portfolio_names.get(self._radar_norm(x.get("client_name")),[])
                    if len(ks)==1:key=str(ks[0])
                if not key:continue
                d=x.get("days_to_next")
                if x.get("overdue"):overdue_clients.add(key)
                elif d is not None and 0<int(d)<=7:upcoming_clients.add(key)
'''
if text.count(needle)!=1:raise SystemExit('card portfolio block nao encontrado')
text=text.replace(needle,replacement,1)

# O vínculo manual principal não apaga outros compradores; apenas move o contato atual para este cadastro.
needle='''            data=self._radar_load();data.setdefault("links",{})[wa]=key;self._radar_save();refresh()
'''
replacement='''            data=self._radar_load();links=data.setdefault("links",{});links.pop(wa,None);links[wa]=key;self._radar_save();refresh()
'''
text=text.replace(needle,replacement,1)

main.write_text(text,encoding='utf-8')
print('PATCH_RADAR_PORTFOLIO_MULTI_OFFER_V2307=OK')

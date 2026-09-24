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

one('ALIYVO_VERSION = "0.23.03"','ALIYVO_VERSION = "0.23.04"','version')

# Botão principal visível no topo.
one('''        self.reminder_toggle=QPushButton("⏰  Lembretes")
        self.ponto_toggle=QPushButton("🕒  Ponto")
''','''        self.reminder_toggle=QPushButton("⏰  Lembretes")
        self.radar_toggle=QPushButton("🎯  Radar da Carteira")
        self.radar_toggle.setToolTip("Inteligência automática da carteira • histórico 12 meses + recompra")
        self.radar_toggle.clicked.connect(self._radar_show_dialog)
        self.ponto_toggle=QPushButton("🕒  Ponto")
''','radar button create')

one('''        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addWidget(self.ponto_toggle)
''','''        nav_lay.addWidget(self.reminder_toggle)
        nav_lay.addWidget(self.radar_toggle)
        nav_lay.addWidget(self.ponto_toggle)
''','radar button layout')

# Enriquecer Assistência Rápida com dados locais do Radar.
one('''        crm_state=self._crm_state_for_client(name)
        lines += ["", "SITUAÇÃO CRM"]
''','''        crm_state=self._crm_state_for_client(name)
        try:
            radar_text=self._radar_client_summary_text(name)
        except Exception:
            radar_text=""
        if radar_text:
            lines += ["", "RADAR DA CARTEIRA", radar_text]
        lines += ["", "SITUAÇÃO CRM"]
''','radar in quick assist')

# Métodos do Radar entram antes do CRM states.
anchor='    def _crm_state_file(self):\n'
idx=text.index(anchor)
radar=r'''
    # ===== RADAR DA CARTEIRA 0.23.04 =====
    # Fontes locais: (1) histórico de 12 meses e (2) recorrência/recompra.
    # Nenhum dado comercial é enviado automaticamente para a nuvem.
    def _radar_file(self):
        try: USER_DATA_DIR.mkdir(parents=True,exist_ok=True)
        except Exception: pass
        return USER_DATA_DIR/"radar_carteira.json"

    def _radar_sources_dir(self):
        p=USER_DATA_DIR/"radar_fontes"
        try:p.mkdir(parents=True,exist_ok=True)
        except Exception:pass
        return p

    def _radar_default(self):
        return {"version":1,"history":{"meta":{},"clients":{}},"recurrence":{"meta":{},"items":[]},"links":{}}

    def _radar_load(self,force=False):
        if not force:
            x=getattr(self,"_radar_cache",None)
            if isinstance(x,dict):return x
        try:
            f=self._radar_file()
            if f.exists():
                x=json.loads(f.read_text(encoding="utf-8"))
                if isinstance(x,dict):
                    x.setdefault("history",{"meta":{},"clients":{}})
                    x.setdefault("recurrence",{"meta":{},"items":[]})
                    x.setdefault("links",{})
                    self._radar_cache=x;return x
        except Exception:pass
        x=self._radar_default();self._radar_cache=x;return x

    def _radar_save(self):
        try:
            x=self._radar_load()
            self._radar_file().write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding="utf-8")
        except Exception:pass

    def _radar_norm(self,value):
        import re,unicodedata
        s=str(value or "").strip().lower()
        s=''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn')
        return re.sub(r'[^a-z0-9]+',' ',s).strip()

    def _radar_num(self,value):
        if value is None:return None
        if isinstance(value,(int,float)) and not isinstance(value,bool):
            try:return float(value)
            except Exception:return None
        s=str(value).strip()
        if not s:return None
        s=s.replace("R$","").replace(" ","")
        try:
            if "," in s:
                s=s.replace(".","").replace(",",".")
            return float(s)
        except Exception:return None

    def _radar_date(self,value):
        import datetime,re
        if isinstance(value,datetime.datetime):return value.date()
        if isinstance(value,datetime.date):return value
        s=str(value or "").strip()
        if not s:return None
        for fmt in ("%d/%m/%Y","%d/%m/%y","%Y-%m-%d","%d-%m-%Y"):
            try:return datetime.datetime.strptime(s[:10],fmt).date()
            except Exception:pass
        m=re.search(r'(\d{1,2})/(\d{1,2})/(\d{2,4})',s)
        if m:
            try:
                y=int(m.group(3));y=y+2000 if y<100 else y
                return datetime.date(y,int(m.group(2)),int(m.group(1)))
            except Exception:pass
        return None

    def _radar_read_xls(self,path):
        # xlrd fica embarcado no pacote para ler o .xls antigo exportado pelo ERP.
        import sys
        vendor=APP_DIR/"vendor"
        if str(vendor) not in sys.path:sys.path.insert(0,str(vendor))
        import xlrd,datetime
        wb=xlrd.open_workbook(str(path),on_demand=True)
        sh=wb.sheet_by_index(0);rows=[]
        for r in range(sh.nrows):
            vals=[]
            for c in range(sh.ncols):
                cell=sh.cell(r,c);v=cell.value
                if cell.ctype==xlrd.XL_CELL_DATE:
                    try:v=xlrd.xldate_as_datetime(v,wb.datemode).date().isoformat()
                    except Exception:pass
                vals.append(v)
            rows.append(vals)
        name=str(sh.name or "Planilha")
        try:wb.release_resources()
        except Exception:pass
        return rows,name

    def _radar_header_row(self,rows,kind):
        import re
        best=(0,-1)
        for i,row in enumerate((rows or [])[:25]):
            hs=[self._radar_norm(x) for x in row]
            joined=" | ".join(hs);score=sum(1 for x in hs if x)
            if any(x in joined for x in ("cliente","parceiro","razao","nome")):score+=5
            if any(x in joined for x in ("codigo","codparc","cod cliente","cod parceiro")):score+=3
            if kind=="history":
                months=sum(1 for x in hs if re.search(r'\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)',x))
                score+=months*3
            else:
                if any(x in joined for x in ("produto","codprod","descricao")):score+=6
                if "alerta" in joined:score+=4
                if "media" in joined and "dia" in joined:score+=4
                if "proxima" in joined and "compra" in joined:score+=4
                if "ultima" in joined and "compra" in joined:score+=3
            if score>best[0]:best=(score,i)
        return best[1]

    def _radar_find_col(self,headers,phrases,exclude=()):
        hs=[self._radar_norm(x) for x in headers]
        ps=[self._radar_norm(x) for x in phrases]
        ex=[self._radar_norm(x) for x in exclude]
        # Primeiro correspondência mais específica.
        for p in ps:
            for i,h in enumerate(hs):
                if p and p in h and not any(e and e in h for e in ex):return i
        # Depois todos os tokens da frase presentes.
        for p in ps:
            toks=[x for x in p.split() if len(x)>1]
            for i,h in enumerate(hs):
                if toks and all(t in h for t in toks) and not any(e and e in h for e in ex):return i
        return None

    def _radar_parse_history_rows(self,rows):
        import re
        hi=self._radar_header_row(rows,"history")
        if hi<0:return {},{"error":"Não encontrei o cabeçalho do histórico."}
        headers=[str(x or "").strip() for x in rows[hi]]
        code=self._radar_find_col(headers,["codparc","codigo parceiro","codigo cliente","cod cliente","cod parceiro","codigo"],["produto"])
        name=self._radar_find_col(headers,["nome parceiro","razao social","cliente","parceiro","nome"],["codigo","cod "])
        if code is None:code=0
        if name is None:name=1 if len(headers)>1 else 0
        month_cols=[]
        for i,h in enumerate(headers):
            n=self._radar_norm(h)
            if re.search(r'\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)',n):
                month_cols.append(i)
        if len(month_cols)<6:
            # Fallback: colunas com maioria numérica, ignorando totais/médias.
            cand=[]
            for c,h in enumerate(headers):
                if c in (code,name):continue
                hn=self._radar_norm(h)
                if any(x in hn for x in ("total","media","saldo","codigo","qtd","quant")):continue
                vals=[self._radar_num(r[c] if c<len(r) else None) for r in rows[hi+1:hi+35]]
                ok=sum(v is not None for v in vals)
                if ok>=max(2,len(vals)//3):cand.append(c)
            month_cols=cand[-12:]
        if len(month_cols)>12:month_cols=month_cols[-12:]
        out={}
        for row in rows[hi+1:]:
            if not any(str(x or "").strip() for x in row):continue
            cv=row[code] if code<len(row) else "";nv=row[name] if name<len(row) else ""
            c=str(cv or "").strip()
            if c.endswith(".0"):
                try:c=str(int(float(c)))
                except Exception:pass
            nm=str(nv or "").strip()
            if not c and not nm:continue
            key=c or ("NOME:"+self._radar_norm(nm))
            vals=[]
            for j in month_cols:
                v=self._radar_num(row[j] if j<len(row) else None)
                vals.append(0.0 if v is None else v)
            if not vals:continue
            old=out.get(key)
            if old:
                old["months"]=[a+b for a,b in zip(old["months"],vals)]
            else:
                out[key]={"code":c,"name":nm,"months":vals}
        labels=[headers[j] if j<len(headers) else f"M{i+1}" for i,j in enumerate(month_cols)]
        for x in out.values():
            vals=x["months"];n=len(vals)
            avg=sum(vals)/n if n else 0
            recent=vals[-3:] if n>=3 else vals
            prev=vals[-6:-3] if n>=6 else vals[:-len(recent)] if n>len(recent) else []
            ravg=sum(recent)/len(recent) if recent else 0
            pavg=sum(prev)/len(prev) if prev else 0
            trend=((ravg-pavg)/pavg*100) if pavg>0 else None
            x.update({"month_labels":labels,"average":avg,"recent3_avg":ravg,"previous3_avg":pavg,"trend_pct":trend,"latest":vals[-1] if vals else 0,"total":sum(vals)})
        return out,{"header_row":hi+1,"headers":headers,"month_labels":labels,"clients":len(out)}

    def _radar_parse_recurrence_rows(self,rows):
        import datetime
        hi=self._radar_header_row(rows,"recurrence")
        if hi<0:return [],{"error":"Não encontrei o cabeçalho da recorrência."}
        headers=[str(x or "").strip() for x in rows[hi]]
        code=self._radar_find_col(headers,["codparc","codigo parceiro","codigo cliente","cod cliente","cod parceiro"],["produto"])
        name=self._radar_find_col(headers,["nome parceiro","razao social","cliente","parceiro","nome"],["codigo","cod "])
        pcode=self._radar_find_col(headers,["codprod","codigo produto","cod produto","referencia"],["cliente","parceiro"])
        pdesc=self._radar_find_col(headers,["descricao produto","produto","descricao","item"],["codigo","cod "])
        purchases=self._radar_find_col(headers,["qtd compras","quantidade compras","numero compras","n compras","compras"])
        avgdays=self._radar_find_col(headers,["media dias","dias medio","intervalo medio","media entre compras","dias entre compras"])
        last=self._radar_find_col(headers,["ultima compra","data ultima","ult compra"])
        nxt=self._radar_find_col(headers,["proxima compra","data proxima","previsao compra","previsao"])
        alert=self._radar_find_col(headers,["alerta","status"])
        if code is None:code=0
        if name is None:name=1 if len(headers)>1 else 0
        today=datetime.date.today();items=[]
        for row in rows[hi+1:]:
            if not any(str(x or "").strip() for x in row):continue
            def val(i):
                return row[i] if i is not None and i<len(row) else ""
            c=str(val(code) or "").strip()
            if c.endswith(".0"):
                try:c=str(int(float(c)))
                except Exception:pass
            nm=str(val(name) or "").strip()
            pc=str(val(pcode) or "").strip() if pcode is not None else ""
            pd=str(val(pdesc) or "").strip() if pdesc is not None else ""
            if not c and not nm:continue
            av=self._radar_num(val(avgdays));lp=self._radar_date(val(last));np=self._radar_date(val(nxt))
            if np is None and lp is not None and av and av>0:
                try:np=lp+datetime.timedelta(days=int(round(av)))
                except Exception:pass
            days_to=(np-today).days if np else None
            at=str(val(alert) or "").strip()
            atn=self._radar_norm(at)
            overdue=bool(days_to is not None and days_to<=0)
            report_alert=bool(at and atn not in ("nao","não","ok","normal","sem alerta"))
            score=0
            if overdue:score+=65+min(25,abs(int(days_to or 0)))
            elif days_to is not None and days_to<=7:score+=35+(7-days_to)
            if report_alert:score=max(score,55)
            q=self._radar_num(val(purchases))
            if q:score+=min(10,int(q))
            items.append({"client_code":c,"client_name":nm,"product_code":pc,"product":pd,"purchases":q,"avg_days":av,
                          "last_purchase":lp.isoformat() if lp else "","next_purchase":np.isoformat() if np else "",
                          "days_to_next":days_to,"alert":at,"overdue":overdue,"score":score})
        return items,{"header_row":hi+1,"headers":headers,"items":len(items)}

    def _radar_import(self,kind,parent=None,on_done=None):
        from PyQt6.QtWidgets import QFileDialog,QMessageBox
        import datetime,shutil,hashlib
        title="Histórico dos últimos 12 meses" if kind=="history" else "Recorrência / recompra"
        path,_=QFileDialog.getOpenFileName(parent or self,f"Selecionar {title}","","Planilhas Excel antigas (*.xls);;Todos os arquivos (*)")
        if not path:return
        try:
            rows,sheet=self._radar_read_xls(path)
            if kind=="history":payload,diag=self._radar_parse_history_rows(rows)
            else:payload,diag=self._radar_parse_recurrence_rows(rows)
            if diag.get("error") or not payload:
                heads=" | ".join(str(x) for x in (diag.get("headers") or [])[:18])
                raise ValueError((diag.get("error") or "Nenhum dado reconhecido.")+(f"\n\nCabeçalhos encontrados: {heads}" if heads else ""))
            now=datetime.datetime.now();src=Path(path)
            dest=self._radar_sources_dir()/(f"{kind}_{now.strftime('%Y%m%d_%H%M%S')}{src.suffix.lower()}")
            shutil.copy2(src,dest)
            sha=hashlib.sha256(dest.read_bytes()).hexdigest()
            data=self._radar_load()
            meta={"imported_at":now.isoformat(timespec="seconds"),"source_name":src.name,"saved_copy":dest.name,"sha256":sha,"sheet":sheet,"diagnostic":diag}
            if kind=="history":data["history"]={"meta":meta,"clients":payload}
            else:data["recurrence"]={"meta":meta,"items":payload}
            self._radar_save()
            count=len(payload)
            QMessageBox.information(parent or self,"Radar da Carteira",f"{title} atualizado com sucesso.\n\nRegistros reconhecidos: {count}\nArquivo: {src.name}")
            if callable(on_done):on_done()
        except Exception as e:
            QMessageBox.warning(parent or self,"Radar da Carteira",f"Não consegui importar esta planilha.\n\n{e}")

    def _radar_all_clients(self):
        data=self._radar_load();out={}
        for code,x in (data.get("history",{}).get("clients",{}) or {}).items():
            if isinstance(x,dict):out[str(code)]={"code":str(x.get("code") or code),"name":str(x.get("name") or "")}
        for it in (data.get("recurrence",{}).get("items",[]) or []):
            if not isinstance(it,dict):continue
            code=str(it.get("client_code") or "")
            key=code or ("NOME:"+self._radar_norm(it.get("client_name")))
            out.setdefault(key,{"code":code,"name":str(it.get("client_name") or "")})
        return out

    def _radar_resolve_client(self,whatsapp_name):
        name=str(whatsapp_name or "").strip()
        if not name:return None
        data=self._radar_load();links=data.get("links",{}) or {}
        code=str(links.get(name) or "")
        clients=self._radar_all_clients()
        if code and code in clients:return clients[code]
        n=self._radar_norm(name);matches=[]
        for key,x in clients.items():
            if self._radar_norm(x.get("name"))==n and n:matches.append((key,x))
        if len(matches)==1:
            key,x=matches[0]
            # auto-link seguro: nome normalizado exatamente igual e único
            data.setdefault("links",{})[name]=key;self._radar_save()
            return x
        return None

    def _radar_profile_by_code(self,key):
        data=self._radar_load();hist=(data.get("history",{}).get("clients",{}) or {}).get(key) or {}
        rec=[x for x in (data.get("recurrence",{}).get("items",[]) or []) if str(x.get("client_code") or "")==str(key)]
        if not rec and str(key).startswith("NOME:"):
            nn=str(key)[5:]
            rec=[x for x in (data.get("recurrence",{}).get("items",[]) or []) if self._radar_norm(x.get("client_name"))==nn]
        rec.sort(key=lambda x:(-int(x.get("score") or 0),x.get("days_to_next") if x.get("days_to_next") is not None else 99999))
        return {"history":hist if isinstance(hist,dict) else {},"recurrence":rec}

    def _radar_contact_payload(self,whatsapp_name):
        client=self._radar_resolve_client(whatsapp_name)
        if not client:return {}
        code=str(client.get("code") or "")
        key=code if code in self._radar_all_clients() else ("NOME:"+self._radar_norm(client.get("name")))
        p=self._radar_profile_by_code(key)
        return {"client":client,"history":p.get("history") or {},"recurrence":(p.get("recurrence") or [])[:8]}

    def _radar_client_summary_text(self,whatsapp_name):
        p=self._radar_contact_payload(whatsapp_name)
        if not p:return ""
        c=p.get("client") or {};h=p.get("history") or {};rec=p.get("recurrence") or []
        lines=[f"• Cadastro: {c.get('name') or whatsapp_name}"+(f" • cód. {c.get('code')}" if c.get('code') else "")]
        tr=h.get("trend_pct")
        if tr is not None:
            direction="queda" if tr<0 else "alta"
            lines.append(f"• Tendência últimos 3 meses: {direction} de {abs(tr):.1f}% versus os 3 anteriores")
        if h.get("average") is not None:
            lines.append(f"• Média mensal 12 meses: R$ {float(h.get('average') or 0):,.2f}".replace(",", "X").replace(".",",").replace("X","."))
        hot=[x for x in rec if bool(x.get("overdue")) or (x.get("days_to_next") is not None and int(x.get("days_to_next"))<=7) or x.get("alert")]
        if hot:
            lines.append("• Recompras em atenção:")
            for x in hot[:4]:
                d=x.get("days_to_next");when=("atrasado "+str(abs(int(d)))+" dia(s)") if d is not None and d<=0 else (f"previsto em {int(d)} dia(s)" if d is not None else "em alerta")
                prod=str(x.get("product") or x.get("product_code") or "produto")
                lines.append(f"  - {prod}: {when}")
        return "\n".join(lines)

    def _radar_priorities(self):
        data=self._radar_load();clients=self._radar_all_clients();rows={}
        def row_for(key):
            if key not in rows:
                c=clients.get(key,{})
                rows[key]={"key":key,"code":str(c.get("code") or ""),"name":str(c.get("name") or ""),"score":0,"reasons":[],"trend":None,"due":[]}
            return rows[key]
        for key,h in (data.get("history",{}).get("clients",{}) or {}).items():
            if not isinstance(h,dict):continue
            r=row_for(str(key));tr=h.get("trend_pct");r["trend"]=tr
            if tr is not None and tr<=-30:r["score"]+=35;r["reasons"].append(f"faturamento caiu {abs(tr):.0f}%")
            elif tr is not None and tr<=-15:r["score"]+=20;r["reasons"].append(f"faturamento caiu {abs(tr):.0f}%")
        for it in (data.get("recurrence",{}).get("items",[]) or []):
            if not isinstance(it,dict):continue
            code=str(it.get("client_code") or "");key=code or ("NOME:"+self._radar_norm(it.get("client_name")))
            r=row_for(key);sc=int(it.get("score") or 0)
            if sc>0:
                r["score"]+=min(80,sc)
                prod=str(it.get("product") or it.get("product_code") or "produto")
                d=it.get("days_to_next")
                if it.get("overdue"):reason=f"{prod} em recompra atrasada"
                elif d is not None and int(d)<=7:reason=f"{prod} previsto em {int(d)} dia(s)"
                else:reason=f"{prod} em alerta de recorrência"
                if reason not in r["reasons"]:r["reasons"].append(reason)
                r["due"].append(it)
        out=[x for x in rows.values() if x.get("score",0)>0]
        out.sort(key=lambda x:(-int(x.get("score") or 0),str(x.get("name") or "").lower()))
        return out

    def _radar_source_status(self,kind):
        import datetime
        data=self._radar_load();meta=(data.get(kind,{}) or {}).get("meta") or {}
        ts=str(meta.get("imported_at") or "")
        if not ts:return {"text":"Nenhuma planilha carregada","age":None,"state":"red","meta":meta}
        try:
            dt=datetime.datetime.fromisoformat(ts);age=(datetime.datetime.now()-dt).days
        except Exception:age=None
        limit=35 if kind=="history" else 10
        warn=25 if kind=="history" else 7
        state="green" if age is not None and age<=warn else ("yellow" if age is not None and age<=limit else "red")
        label=f"{meta.get('source_name') or 'arquivo'} • atualizado há {age} dia(s)" if age is not None else str(meta.get("source_name") or "arquivo")
        return {"text":label,"age":age,"state":state,"meta":meta}

    def _radar_show_dialog(self):
        from PyQt6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QFrame,QTableWidget,QTableWidgetItem,QHeaderView,QMessageBox,QAbstractItemView
        from PyQt6.QtCore import Qt
        dlg=QDialog(self);dlg.setWindowTitle("🎯 Radar da Carteira — CRM automático");dlg.resize(1120,760)
        lay=QVBoxLayout(dlg)
        title=QLabel("🎯 RADAR DA CARTEIRA");title.setStyleSheet("font-size:22px;font-weight:900;color:#0B3349;");lay.addWidget(title)
        sub=QLabel("O ALIYVO cruza faturamento dos últimos 12 meses com recorrência de compra. Você só atualiza as duas planilhas.")
        sub.setWordWrap(True);sub.setStyleSheet("color:#60717F;font-weight:600;");lay.addWidget(sub)

        sources=QHBoxLayout();sources.setSpacing(10)
        hist_frame=QFrame();rec_frame=QFrame()
        def source_card(frame,heading,detail):
            frame.setStyleSheet("QFrame{border:1px solid #CFDCE5;border-radius:10px;background:#F8FBFD;}")
            v=QVBoxLayout(frame);h=QLabel(heading);h.setStyleSheet("font-size:13px;font-weight:900;color:#173B52;border:none;");v.addWidget(h)
            d=QLabel(detail);d.setWordWrap(True);d.setStyleSheet("font-size:10px;color:#637585;border:none;");v.addWidget(d)
            st=QLabel();st.setWordWrap(True);st.setStyleSheet("font-weight:800;border:none;padding:5px;");v.addWidget(st)
            b=QPushButton("Selecionar planilha .XLS");v.addWidget(b)
            return st,b
        hist_status,hist_btn=source_card(hist_frame,"📊 HISTÓRICO — ÚLTIMOS 12 MESES","Atualize mensalmente. Mostra queda, alta e média de compras por cliente.")
        rec_status,rec_btn=source_card(rec_frame,"🔁 RECORRÊNCIA / RECOMPRA","Atualize semanalmente. Mostra produtos próximos da recompra ou já atrasados.")
        sources.addWidget(hist_frame,1);sources.addWidget(rec_frame,1);lay.addLayout(sources)

        cards=QHBoxLayout();over=QLabel();soon=QLabel();drop=QLabel();links=QLabel()
        for c in (over,soon,drop,links):
            c.setMinimumHeight(58);c.setAlignment(Qt.AlignmentFlag.AlignCenter);cards.addWidget(c,1)
        lay.addLayout(cards)

        table=QTableWidget(0,6);table.setHorizontalHeaderLabels(["Prioridade","Cliente","Motivo","Tendência","Recompras","Vínculo WhatsApp"])
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows);table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers);table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch)
        lay.addWidget(table,1)

        current=QLabel("");current.setWordWrap(True);current.setStyleSheet("background:#EDF6FF;color:#174A70;border-radius:8px;padding:8px;font-weight:700;");lay.addWidget(current)

        def paint_source(kind,label):
            s=self._radar_source_status(kind);colors={"green":("#DFF5E8","#176B3A"),"yellow":("#FFF2B7","#6A5600"),"red":("#FFDDE2","#981B2F")}
            bg,fg=colors.get(s["state"],colors["red"]);label.setText(s["text"]);label.setStyleSheet(f"background:{bg};color:{fg};font-weight:800;border:none;border-radius:6px;padding:6px;")

        def refresh():
            paint_source("history",hist_status);paint_source("recurrence",rec_status)
            rows=self._radar_priorities();data=self._radar_load()
            overdue=sum(1 for x in (data.get("recurrence",{}).get("items",[]) or []) if x.get("overdue"))
            upcoming=sum(1 for x in (data.get("recurrence",{}).get("items",[]) or []) if x.get("days_to_next") is not None and 0<int(x.get("days_to_next"))<=7)
            falling=sum(1 for x in (data.get("history",{}).get("clients",{}) or {}).values() if isinstance(x,dict) and x.get("trend_pct") is not None and x.get("trend_pct")<=-15)
            linked=len(data.get("links",{}) or {})
            over.setText(f"🔴 {overdue}\nRECOMPRAS ATRASADAS");soon.setText(f"🟡 {upcoming}\nPRÓXIMOS 7 DIAS");drop.setText(f"📉 {falling}\nCLIENTES EM QUEDA");links.setText(f"🔗 {linked}\nVÍNCULOS WHATSAPP")
            over.setStyleSheet("background:#FFDDE2;color:#981B2F;border-radius:9px;font-weight:900;padding:6px;")
            soon.setStyleSheet("background:#FFF2B7;color:#6A5600;border-radius:9px;font-weight:900;padding:6px;")
            drop.setStyleSheet("background:#E8E4FF;color:#49358C;border-radius:9px;font-weight:900;padding:6px;")
            links.setStyleSheet("background:#DDEEFF;color:#155B8A;border-radius:9px;font-weight:900;padding:6px;")
            table.setRowCount(len(rows))
            reverse={str(v):k for k,v in (data.get("links",{}) or {}).items()}
            for i,r in enumerate(rows):
                sc=int(r.get("score") or 0);prio="🔴 ALTA" if sc>=70 else ("🟠 MÉDIA" if sc>=35 else "🟡 ATENÇÃO")
                trend=r.get("trend");tr="-" if trend is None else f"{trend:+.1f}%"
                due=len(r.get("due") or []);key=str(r.get("key") or "")
                vals=[prio,str(r.get("name") or r.get("code") or key),"; ".join((r.get("reasons") or [])[:3]),tr,str(due),reverse.get(key,"Não vinculado")]
                for c,v in enumerate(vals):
                    it=QTableWidgetItem(v);it.setData(Qt.ItemDataRole.UserRole,key);table.setItem(i,c,it)
            current_name=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if current_name:
                summary=self._radar_client_summary_text(current_name)
                current.setText(f"CONVERSA ATUAL — {current_name}\n"+(summary or "Ainda não vinculada a um cadastro da carteira. Selecione o cliente acima e use “Vincular conversa atual”."))
            else:current.setText("CONVERSA ATUAL — abra um cliente no WhatsApp para cruzar o Radar com a conversa.")

        def selected_key():
            row=table.currentRow()
            it=table.item(row,0) if row>=0 else None
            return str(it.data(Qt.ItemDataRole.UserRole) or "") if it else ""

        def link_current():
            key=selected_key();wa=str(getattr(self,"_diagnostic_active_name","") or "").strip()
            if not key:
                QMessageBox.information(dlg,"Radar","Selecione primeiro um cliente na lista.");return
            if not wa:
                QMessageBox.information(dlg,"Radar","Abra primeiro a conversa desse cliente no WhatsApp.");return
            data=self._radar_load();data.setdefault("links",{})[wa]=key;self._radar_save();refresh()
            QMessageBox.information(dlg,"Radar",f"Vínculo salvo:\n{wa} → {table.item(table.currentRow(),1).text()}")

        def open_selected():
            key=selected_key()
            if not key:return
            data=self._radar_load();wa=""
            for name,k in (data.get("links",{}) or {}).items():
                if str(k)==key:wa=str(name);break
            if not wa:
                c=self._radar_all_clients().get(key) or {};wa=str(c.get("name") or "")
            if wa:
                dlg.accept();QTimer.singleShot(120,lambda wa=wa:self._attendance_open_chat(wa))

        hist_btn.clicked.connect(lambda:self._radar_import("history",dlg,refresh))
        rec_btn.clicked.connect(lambda:self._radar_import("recurrence",dlg,refresh))
        row=QHBoxLayout();openb=QPushButton("💬 Abrir cliente");linkb=QPushButton("🔗 Vincular conversa atual");reloadb=QPushButton("↻ Atualizar painel");close=QPushButton("Fechar")
        row.addWidget(openb);row.addWidget(linkb);row.addWidget(reloadb);row.addStretch(1);row.addWidget(close);lay.addLayout(row)
        openb.clicked.connect(open_selected);linkb.clicked.connect(link_current);reloadb.clicked.connect(refresh);close.clicked.connect(dlg.accept);table.cellDoubleClicked.connect(lambda _r,_c:open_selected())
        refresh();dlg.exec()

'''
text=text[:idx]+radar+text[idx:]

# Mantém metadado de update coerente.
text=text.replace('aliyvo_version="0.23.03"','aliyvo_version="0.23.04"')
main.write_text(text,encoding='utf-8')
print('PATCH_RADAR_V2304=OK')

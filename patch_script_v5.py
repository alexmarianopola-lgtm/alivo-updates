from pathlib import Path
import sys,re,ast,json

p=Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/build/_app/main.py')
root=Path(__file__).resolve().parent
meta=json.loads((root/'update-v5.json').read_text(encoding='utf-8'))
version=str(meta['version']).strip().lstrip('vV')
text=p.read_text(encoding='utf-8')
text=re.sub(r'ALIYVO_VERSION\s*=\s*"[^"]+"', f'ALIYVO_VERSION = "{version}"', text, count=1)

# -----------------------------------------------------------------------------
# v0.22.18 - Referências tolerantes a pontuação/espaço.
# Ex.: MB309.3 = MB-309.3 = MB3093 = MB309-3 = MB 309 3 -> MB3093
# Mantemos a busca exata primeiro; a busca canônica entra como fallback/suplemento.
# -----------------------------------------------------------------------------

# 1) Assistente Técnico: extração de referências + consulta canônica.
pat=r'''(?s)        # Códigos explícitos: evita tratar ano/modelo curto como referência\.\n        codes=\[\].*?\n        part_words=\{'''
m=re.search(pat,text)
if not m:
    raise SystemExit('technical code block not found')

replacement=r'''        # Referências/códigos: aceita variações de ponto, hífen e espaço.
        # Chave canônica: mantém apenas letras+números (MB309.3 -> MB3093).
        codes=[]
        code_keys={}
        def _add_ref_candidate(value):
            raw=str(value or "").strip()
            if not raw:
                return
            key=re.sub(r"[^A-Z0-9]","",raw.upper())
            if len(key)<5 or not any(ch.isdigit() for ch in key):
                return
            if re.fullmatch(r"(?:19|20)\d{2}",key):
                return
            if key not in code_keys:
                code_keys[key]=raw
                codes.append(raw)

        for c in extract_codes_strict(text):
            _add_ref_candidate(c)

        # Formas contínuas: MB309.3, MB-309.3, 5168-BG etc.
        for c in re.findall(r"(?<![A-Za-z0-9])([A-Za-z0-9][A-Za-z0-9./_-]{4,})(?![A-Za-z0-9])",text):
            _add_ref_candidate(c)

        # Forma espaçada que clientes digitam no WhatsApp: MB 309 3 / ZL 2050 etc.
        # Exclui palavras de contexto para não transformar 'MOD 2014' em código.
        blocked_prefix={"MOD","MODELO","ANO","QTD","QTDE","VALOR","PRECO","REF","COD","CODIGO"}
        spaced_rx=re.compile(r"(?i)(?<![A-Z0-9])([A-Z]{1,4})\s*[-./]?\s*(\d{2,8})(?:\s*[-./]?\s*([A-Z0-9]{1,4}))?(?![A-Z0-9])")
        for mm in spaced_rx.finditer(text):
            prefix=(mm.group(1) or "").upper()
            if prefix in blocked_prefix:
                continue
            parts=[x for x in mm.groups() if x]
            _add_ref_candidate("".join(parts))

        exact=[]
        if codes:
            try:
                con=sqlite3.connect(DB_PATH); cur=con.cursor()
                seen=set()
                # SQL canônico somente como segunda camada. 33 mil itens é leve sob clique.
                canon_cod="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(codprod,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                canon_ref="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(refforn,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                canon_compl="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(compldesc,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                for code in codes[:10]:
                    nq=norm(code)
                    key=re.sub(r"[^A-Z0-9]","",str(code).upper())
                    # Primeiro mantém a pesquisa existente/exata.
                    rows=cur.execute("""
                        SELECT id,codprod,refforn,marca,descricao,compldesc,
                        CASE WHEN codprod=? THEN 100 WHEN refforn=? THEN 98
                             WHEN n_codprod=? THEN 95 WHEN n_refforn=? THEN 93
                             WHEN n_compldesc LIKE ? THEN 80 ELSE 0 END score
                        FROM produtos
                        WHERE codprod=? OR refforn=? OR n_codprod=? OR n_refforn=? OR n_compldesc LIKE ?
                        ORDER BY score DESC LIMIT 8
                    """,(code,code,nq,nq,f"%{nq}%",code,code,nq,nq,f"%{nq}%")).fetchall()
                    # Depois procura a mesma referência ignorando . - / _ e espaços.
                    if key:
                        rows2=cur.execute(f"""
                            SELECT id,codprod,refforn,marca,descricao,compldesc,
                            CASE WHEN {canon_cod}=? THEN 94
                                 WHEN {canon_ref}=? THEN 92
                                 WHEN {canon_compl} LIKE ? THEN 79 ELSE 0 END score
                            FROM produtos
                            WHERE {canon_cod}=? OR {canon_ref}=? OR {canon_compl} LIKE ?
                            ORDER BY score DESC LIMIT 10
                        """,(key,key,f"%{key}%",key,key,f"%{key}%")).fetchall()
                        rows=list(rows)+list(rows2)
                    for r in rows:
                        if r[0] not in seen:
                            seen.add(r[0]); exact.append(r)
                con.close()
            except Exception:
                exact=[]

        if codes:
            display_refs=[]
            for c in codes[:8]:
                k=re.sub(r"[^A-Z0-9]","",str(c).upper())
                label=str(c)
                display_refs.append(label if label.upper()==k else f"{label} → {k}")
            lines += ["","REFERÊNCIAS DETECTADAS"," • ".join(display_refs)]

        part_words={'''
text=text[:m.start()]+replacement+text[m.end():]

# 2) Busca manual do Assistente/Base Soma: se a busca normal não retornar nada,
# tenta a mesma chave ignorando separadores na referência/código/complemento.
method_pat=r'''(?s)(    def search_products\(self\):.*?        rows=cur\.fetchall\(\)\n)(        con\.close\(\)\n        self\.last_results=rows)'''
mm=re.search(method_pat,text)
if not mm:
    raise SystemExit('search_products fetch block not found')

fallback=r'''        if not rows:
            refkey=re.sub(r"[^A-Z0-9]","",str(q).upper())
            if len(refkey)>=4 and any(ch.isdigit() for ch in refkey):
                canon_cod="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(codprod,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                canon_ref="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(refforn,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                canon_compl="REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(COALESCE(compldesc,'')),' ',''),'-',''),'.',''),'/',''),'_','')"
                rows=cur.execute(f"""
                    SELECT id,codprod,refforn,marca,descricao,compldesc,
                    CASE WHEN {canon_cod}=? THEN 94
                         WHEN {canon_ref}=? THEN 92
                         WHEN {canon_compl} LIKE ? THEN 79 ELSE 0 END score
                    FROM produtos
                    WHERE {canon_cod}=? OR {canon_ref}=? OR {canon_compl} LIKE ?
                    ORDER BY score DESC,codprod
                    LIMIT 80
                """,(refkey,refkey,f"%{refkey}%",refkey,refkey,f"%{refkey}%")).fetchall()
'''
text=text[:mm.end(1)]+fallback+text[mm.end(1):]

ast.parse(text)
p.write_text(text,encoding='utf-8')
print('patched tolerant references',version)

"""Regras locais de frete do ALIYVO.

Este módulo não usa internet, IA ou API. Ele mantém separada da interface a
lógica recebida na planilha de transportadoras, para que as faixas possam ser
testadas sem carregar o PyQt/WhatsApp.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import re
import unicodedata


SC = "Abdon Batista|Abelardo Luz|Agrolândia|Agronômica|Alfredo Wagner|Alto Bela Vista|Anchieta|Angelina|Anita Garibaldi|Anitápolis|Antônio Carlos|Apiúna|Arabutã|Araquari|Araranguá|Armazém|Arroio Trinta|Arvoredo|Ascurra|Atalanta|Aurora|Balneário Arroio do Silva|Balneário Barra do Sul|Balneário Camboriú|Balneário Gaivota|Balneário Piçarras|Balneário Rincão|Bandeirante|Barra Bonita|Barra Velha|Bela Vista do Toldo|Belmonte|Benedito Novo|Biguaçu|Blumenau|Bocaina do Sul|Bom Jardim da Serra|Bom Jesus|Bom Jesus do Oeste|Bom Retiro|Bombinhas|Botuverá|Braço do Norte|Braço do Trombudo|Brunópolis|Brusque|Caibi|Calmon|Camboriú|Campo Alegre|Campo Belo do Sul|Campo Erê|Campos Novos|Canelinha|Canoinhas|Capinzal|Capivari de Baixo|Capão Alto|Catanduvas|Caxambu do Sul|Caçador|Celso Ramos|Cerro Negro|Chapadão do Lageado|Chapecó|Cocal do Sul|Concórdia|Cordilheira Alta|Coronel Freitas|Coronel Martins|Correia Pinto|Corupá|Criciúma|Cunha Porã|Cunhataí|Curitibanos|Descanso|Dionísio Cerqueira|Dona Emma|Doutor Pedrinho|Entre Rios|Ermo|Erval Velho|Faxinal dos Guedes|Flor do Sertão|Florianópolis|Formosa do Sul|Forquilhinha|Fraiburgo|Frei Rogério|Galvão|Garopaba|Garuva|Gaspar|Governador Celso Ramos|Gravatal|Grão Pará|Guabiruba|Guaraciaba|Guaramirim|Guarujá do Sul|Guatambú|Herval d'Oeste|Ibiam|Ibicaré|Ibirama|Ilhota|Imaruí|Imbituba|Imbuia|Indaial|Iomerê|Ipira|Iporã do Oeste|Ipuaçu|Ipumirim|Iraceminha|Irani|Irati|Irineópolis|Itaiópolis|Itajaí|Itapema|Itapiranga|Itapoá|Ituporanga|Itá|Içara|Jaborá|Jacinto Machado|Jaguaruna|Jaraguá do Sul|Jardinópolis|Joaçaba|Joinville|José Boiteux|Jupiá|Lacerdópolis|Lages|Laguna|Lajeado Grande|Laurentino|Lauro Muller|Lebon Régis|Leoberto Leal|Lindóia do Sul|Lontras|Luiz Alves|Luzerna|Macieira|Mafra|Major Gercino|Major Vieira|Maracajá|Maravilha|Marema|Massaranduba|Matos Costa|Meleiro|Mirim Doce|Modelo|Mondaí|Monte Carlo|Monte Castelo|Morro Grande|Morro da Fumaça|Navegantes|Nova Erechim|Nova Itaberaba|Nova Trento|Nova Veneza|Novo Horizonte|Orleans|Otacílio Costa|Ouro|Ouro Verde|Paial|Painel|Palhoça|Palma Sola|Palmeira|Palmitos|Papanduva|Paraíso|Passo de Torres|Passos Maia|Paulo Lopes|Pedras Grandes|Penha|Peritiba|Pescaria Brava|Petrolândia|Pinhalzinho|Pinheiro Preto|Piratuba|Planalto Alegre|Pomerode|Ponte Alta|Ponte Alta do Norte|Ponte Serrada|Porto Belo|Porto União|Pouso Redondo|Praia Grande|Presidente Castello Branco|Presidente Getúlio|Presidente Nereu|Princesa|Quilombo|Rancho Queimado|Rio Fortuna|Rio Negrinho|Rio Rufino|Rio das Antas|Rio do Campo|Rio do Oeste|Rio do Sul|Rio dos Cedros|Riqueza|Rodeio|Romelândia|Salete|Saltinho|Salto Veloso|Sangão|Santa Cecília|Santa Helena|Santa Rosa de Lima|Santa Rosa do Sul|Santa Terezinha|Santa Terezinha do Progresso|Santiago do Sul|Santo Amaro da Imperatriz|Saudades|Schroeder|Seara|Serra Alta|Siderópolis|Sombrio|Sul Brasil|São Bento do Sul|São Bernardino|São Bonifácio|São Carlos|São Cristovão do Sul|São Domingos|São Francisco do Sul|São Joaquim|São José|São José do Cedro|São José do Cerrito|São João Batista|São João do Itaperiú|São João do Oeste|São João do Sul|São Lourenço do Oeste|São Ludgero|São Martinho|São Miguel da Boa Vista|São Miguel do Oeste|São Pedro de Alcântara|Taió|Tangará|Tigrinhos|Tijucas|Timbé do Sul|Timbó|Timbó Grande|Treviso|Treze Tílias|Treze de Maio|Trombudo Central|Três Barras|Tubarão|Tunápolis|Turvo|União do Oeste|Urubici|Urupema|Urussanga|Vargem|Vargem Bonita|Vargeão|Vidal Ramos|Videira|Vitor Meireles|Witmarsum|Xanxerê|Xavantina|Xaxim|Zortéa|Água Doce|Águas Frias|Águas Mornas|Águas de Chapecó".split("|")

RS = "Aceguá|Agudo|Ajuricaba|Alecrim|Alegrete|Alegria|Almirante Tamandaré do Sul|Alpestre|Alto Alegre|Alto Feliz|Alvorada|Amaral Ferrador|Ametista do Sul|André da Rocha|Anta Gorda|Antônio Prado|Arambaré|Araricá|Aratiba|Arroio Grande|Arroio do Meio|Arroio do Padre|Arroio do Sal|Arroio do Tigre|Arroio dos Ratos|Arvorezinha|Augusto Pestana|Bagé|Balneário Pinhal|Barra Funda|Barra do Guarita|Barra do Quaraí|Barra do Ribeiro|Barra do Rio Azul|Barracão|Barros Cassal|Barão|Barão de Cotegipe|Barão do Triunfo|Benjamin Constant do Sul|Bento Gonçalves|Boa Vista das Missões|Boa Vista do Buricá|Boa Vista do Cadeado|Boa Vista do Incra|Boa Vista do Sul|Bom Jesus|Bom Princípio|Bom Progresso|Bom Retiro do Sul|Boqueirão do Leão|Bossoroca|Bozano|Braga|Brochier|Butiá|Cacequi|Cachoeira do Sul|Cachoeirinha|Cacique Doble|Caibaté|Caiçara|Camaquã|Camargo|Cambará do Sul|Campestre da Serra|Campina das Missões|Campinas do Sul|Campo Bom|Campo Novo|Campos Borges|Candelária|Candiota|Canela|Canguçu|Canoas|Canudos do Vale|Capela de Santana|Capitão|Capivari do Sul|Capão Bonito do Sul|Capão da Canoa|Capão do Cipó|Capão do Leão|Carazinho|Caraá|Carlos Barbosa|Carlos Gomes|Casca|Caseiros|Catuípe|Caxias do Sul|Caçapava do Sul|Centenário|Cerrito|Cerro Branco|Cerro Grande|Cerro Grande do Sul|Cerro Largo|Chapada|Charqueadas|Charrua|Chiapetta|Chuvisca|Chuí|Cidreira|Ciríaco|Colinas|Colorado|Condor|Constantina|Coqueiro Baixo|Coqueiros do Sul|Coronel Barros|Coronel Bicaco|Coronel Pilar|Cotiporã|Coxilha|Crissiumal|Cristal|Cristal do Sul|Cruz Alta|Cruzaltense|Cruzeiro do Sul|Cândido Godói|David Canabarro|Derrubadas|Dezesseis de Novembro|Dilermando de Aguiar|Dois Irmãos|Dois Irmãos das Missões|Dois Lajeados|Dom Feliciano|Dom Pedrito|Dom Pedro de Alcântara|Dona Francisca|Doutor Maurício Cardoso|Doutor Ricardo|Eldorado do Sul|Encantado|Encruzilhada do Sul|Engenho Velho|Entre Rios do Sul|Entre-Ijuís|Erebango|Erechim|Ernestina|Erval Grande|Erval Seco|Esmeralda|Esperança do Sul|Espumoso|Estação|Esteio|Estrela|Estrela Velha|Estância Velha|Eugênio de Castro|Fagundes Varela|Farroupilha|Faxinal do Soturno|Faxinalzinho|Fazenda Vilanova|Feliz|Flores da Cunha|Floriano Peixoto|Fontoura Xavier|Formigueiro|Forquetinha|Fortaleza dos Valos|Frederico Westphalen|Garibaldi|Garruchos|Gaurama|General Câmara|Gentil|Getúlio Vargas|Giruá|Glorinha|Gramado|Gramado Xavier|Gramado dos Loureiros|Gravataí|Guabiju|Guaporé|Guarani das Missões|Guaíba|Harmonia|Herval|Herveiras|Horizontina|Hulha Negra|Humaitá|Ibarama|Ibiaçá|Ibiraiaras|Ibirapuitã|Ibirubá|Igrejinha|Ijuí|Ilópolis|Imbé|Imigrante|Independência|Inhacorá|Ipiranga do Sul|Ipê|Iraí|Itaara|Itacurubi|Itapuca|Itaqui|Itati|Itatiba do Sul|Ivorá|Ivoti|Jaboticaba|Jacuizinho|Jacutinga|Jaguari|Jaguarão|Jaquirana|Jari|Jóia|Júlio de Castilhos|Lagoa Bonita do Sul|Lagoa Vermelha|Lagoa dos Três Cantos|Lagoão|Lajeado|Lajeado do Bugre|Lavras do Sul|Liberato Salzano|Lindolfo Collor|Linha Nova|Machadinho|Mampituba|Manoel Viana|Maquiné|Maratá|Marau|Marcelino Ramos|Mariana Pimentel|Mariano Moro|Marques de Souza|Mata|Mato Castelhano|Mato Leitão|Mato Queimado|Maximiliano de Almeida|Maçambará|Minas do Leão|Miraguaí|Montauri|Monte Alegre dos Campos|Monte Belo do Sul|Montenegro|Mormaço|Morrinhos do Sul|Morro Redondo|Morro Reuter|Mostardas|Muitos Capões|Muliterno|Muçum|Nicolau Vergueiro|Nonoai|Nova Alvorada|Nova Araçá|Nova Bassano|Nova Boa Vista|Nova Bréscia|Nova Candelária|Nova Esperança do Sul|Nova Hartz|Nova Palma|Nova Petrópolis|Nova Prata|Nova Pádua|Nova Ramada|Nova Roma do Sul|Nova Santa Rita|Novo Barreiro|Novo Cabrais|Novo Hamburgo|Novo Machado|Novo Tiradentes|Novo Xingu|Não-Me-Toque|Osório|Paim Filho|Palmares do Sul|Palmeira das Missões|Palmitinho|Panambi|Pantano Grande|Paraí|Paraíso do Sul|Pareci Novo|Parobé|Passa Sete|Passo Fundo|Passo do Sobrado|Paulo Bento|Paverama|Pedras Altas|Pedro Osório|Pejuçara|Pelotas|Picada Café|Pinhal|Pinhal Grande|Pinhal da Serra|Pinheirinho do Vale|Pinheiro Machado|Pinto Bandeira|Pirapó|Piratini|Planalto|Ponte Preta|Pontão|Porto Alegre|Porto Lucena|Porto Mauá|Porto Vera Cruz|Porto Xavier|Portão|Pouso Novo|Poço das Antas|Presidente Lucena|Progresso|Protásio Alves|Putinga|Quaraí|Quatro Irmãos|Quevedos|Quinze de Novembro|Redentora|Relvado|Restinga Sêca|Rio Grande|Rio Pardo|Rio dos Índios|Riozinho|Roca Sales|Rodeio Bonito|Rolador|Rolante|Ronda Alta|Rondinha|Roque Gonzales|Rosário do Sul|Sagrada Família|Saldanha Marinho|Salto do Jacuí|Salvador das Missões|Salvador do Sul|Sananduva|Sant'Ana do Livramento|Santa Bárbara do Sul|Santa Cecília do Sul|Santa Clara do Sul|Santa Cruz do Sul|Santa Margarida do Sul|Santa Maria|Santa Maria do Herval|Santa Rosa|Santa Tereza|Santa Vitória do Palmar|Santana da Boa Vista|Santiago|Santo Antônio da Patrulha|Santo Antônio das Missões|Santo Antônio do Palma|Santo Antônio do Planalto|Santo Augusto|Santo Cristo|Santo Expedito do Sul|Santo Ângelo|Sapiranga|Sapucaia do Sul|Sarandi|Seberi|Sede Nova|Segredo|Selbach|Senador Salgado Filho|Sentinela do Sul|Serafina Corrêa|Sertão|Sertão Santana|Sete de Setembro|Severiano de Almeida|Silveira Martins|Sinimbu|Sobradinho|Soledade|São Borja|São Domingos do Sul|São Francisco de Assis|São Francisco de Paula|São Gabriel|São Jerônimo|São Jorge|São José das Missões|São José do Herval|São José do Hortêncio|São José do Inhacorá|São José do Norte|São José do Ouro|São José do Sul|São José dos Ausentes|São João da Urtiga|São João do Polêsine|São Leopoldo|São Lourenço do Sul|São Luiz Gonzaga|São Marcos|São Martinho|São Martinho da Serra|São Miguel das Missões|São Nicolau|São Paulo das Missões|São Pedro da Serra|São Pedro das Missões|São Pedro do Butiá|São Pedro do Sul|São Sebastião do Caí|São Sepé|São Valentim|São Valentim do Sul|São Valério do Sul|São Vendelino|São Vicente do Sul|Sério|Tabaí|Tapejara|Tapera|Tapes|Taquara|Taquari|Taquaruçu do Sul|Tavares|Tenente Portela|Terra de Areia|Teutônia|Tio Hugo|Tiradentes do Sul|Toropi|Torres|Tramandaí|Travesseiro|Trindade do Sul|Triunfo|Três Arroios|Três Cachoeiras|Três Coroas|Três Forquilhas|Três Palmeiras|Três Passos|Três de Maio|Tucunduva|Tunas|Tupanci do Sul|Tupanciretã|Tupandi|Tuparendi|Turuçu|Ubiretama|Unistalda|União da Serra|Uruguaiana|Vacaria|Vale Real|Vale Verde|Vale do Sol|Vanini|Venâncio Aires|Vera Cruz|Veranópolis|Vespasiano Corrêa|Viadutos|Viamão|Vicente Dutra|Victor Graeff|Vila Flores|Vila Lângaro|Vila Maria|Vila Nova do Sul|Vista Alegre|Vista Alegre do Prata|Vista Gaúcha|Vitória das Missões|Westfália|Xangri-lá|Água Santa|Áurea".split("|")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-zA-Z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


CITY_STATES: dict[str, set[str]] = {}
CITY_DISPLAY: dict[tuple[str, str], str] = {}
for _uf, _names in (("SC", SC), ("RS", RS)):
    for _name in _names:
        _key = normalize_text(_name)
        CITY_STATES.setdefault(_key, set()).add(_uf)
        CITY_DISPLAY[(_key, _uf)] = _name


def city_choices() -> list[str]:
    return sorted(
        (f"{name} - {uf}" for (key, uf), name in CITY_DISPLAY.items()),
        key=normalize_text,
    )


def resolve_city(value: str) -> dict:
    raw = str(value or "").strip()
    if not raw:
        return {"ok": False, "reason": "Informe a cidade."}

    explicit = None
    m = re.search(r"(?:^|[\s,/\-])\b(SC|RS)\b\s*$", raw, re.I)
    if m:
        explicit = m.group(1).upper()
        raw = raw[:m.start(1)].rstrip(" ,/-")

    key = normalize_text(raw)
    states = CITY_STATES.get(key, set())
    if explicit:
        if explicit in states:
            return {
                "ok": True,
                "city": CITY_DISPLAY[(key, explicit)],
                "uf": explicit,
            }
        return {"ok": False, "reason": "Cidade não encontrada em SC/RS."}
    if len(states) == 1:
        uf = next(iter(states))
        return {"ok": True, "city": CITY_DISPLAY[(key, uf)], "uf": uf}
    if len(states) > 1:
        return {
            "ok": False,
            "reason": "Essa cidade existe em SC e RS. Escolha a opção com a UF.",
        }
    return {"ok": False, "reason": "Cidade não encontrada. Escolha uma opção da lista."}


def parse_brl(value) -> Decimal | None:
    if isinstance(value, Decimal):
        return value if value >= 0 else None
    if isinstance(value, (int, float)):
        return Decimal(str(value)) if value >= 0 else None
    text = str(value or "").strip().replace("R$", "").replace(" ", "")
    if not text:
        return None
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):
        # No uso brasileiro, "1.200" normalmente significa mil e duzentos.
        text = text.replace(".", "")
    try:
        parsed = Decimal(text)
        return parsed if parsed >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def brl(value: Decimal) -> str:
    text = f"{value:,.2f}"
    return "R$ " + text.replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass(frozen=True)
class FreightRule:
    uf: str
    cutoff: str
    free_from: Decimal | None
    tiers: tuple[tuple[Decimal, Decimal], ...] = ()
    note: str = ""
    negotiated: bool = False


@dataclass(frozen=True)
class FreightService:
    key: str
    carrier: str
    branch: str
    code: str
    rules: dict[str, FreightRule]

    @property
    def label(self) -> str:
        return f"{self.carrier} · {self.branch} ({self.code})"


def _d(value) -> Decimal:
    return Decimal(str(value))


SERVICES = (
    FreightService("matriz_sao_miguel", "São Miguel", "Matriz", "10404", {
        "SC": FreightRule("SC", "17:00", _d(1200), ((_d(800), _d(45)), (_d(0), _d(65))), "Até 2 itens: corte 17:30"),
        "RS": FreightRule("RS", "17:00", _d(1500), ((_d(1000), _d(50)), (_d(500), _d(65)), (_d(0), _d(75))), "Até 2 itens: corte 17:30"),
    }),
    FreightService("matriz_fabris", "Fabris", "Matriz", "3743", {
        "SC": FreightRule("SC", "16:00", _d(1200), ((_d(800), _d(45)), (_d(0), _d(65)))),
    }),
    FreightService("matriz_sao_joao", "São João", "Matriz", "10699", {
        "SC": FreightRule("SC", "Em negociação", None, (), "Valores em negociação", True),
    }),
    FreightService("matriz_leomar", "Leomar", "Matriz", "2240", {
        "RS": FreightRule("RS", "12:00", _d(2000), ((_d(1200), _d(40)), (_d(700), _d(55)), (_d(0), _d(70)))),
    }),
    FreightService("tres_sao_miguel", "São Miguel", "Três Cachoeiras", "10628", {
        "RS": FreightRule("RS", "16:00", _d(1500), ((_d(1000), _d(40)), (_d(500), _d(55)), (_d(0), _d(65)))),
    }),
    FreightService("tres_sao_joao", "São João", "Três Cachoeiras", "10699", {
        "SC": FreightRule("SC", "Em negociação", None, (), "Valores em negociação", True),
    }),
    FreightService("tres_leomar", "Leomar", "Três Cachoeiras", "2240", {
        "RS": FreightRule("RS", "12:00", _d(2000), ((_d(1200), _d(40)), (_d(700), _d(55)), (_d(0), _d(65)))),
    }),
    FreightService("itajai_sao_miguel", "São Miguel", "Itajaí", "31195", {
        "SC": FreightRule("SC", "15:00", _d(1200), ((_d(800), _d(45)), (_d(0), _d(65)))),
        "RS": FreightRule("RS", "15:00", _d(2500), ((_d(2000), _d(60)), (_d(1500), _d(75)), (_d(800), _d(95)), (_d(0), _d(120)))),
    }),
    FreightService("itajai_fabris", "Fabris", "Itajaí", "3743", {
        "SC": FreightRule("SC", "12:00", _d(1200), ((_d(800), _d(45)), (_d(0), _d(65)))),
    }),
    FreightService("itajai_sao_joao", "São João", "Itajaí", "10699", {
        "SC": FreightRule("SC", "Em negociação", _d(1200), (), "Frete abaixo do mínimo em negociação"),
    }),
)

SERVICE_BY_KEY = {service.key: service for service in SERVICES}


def services_for_uf(uf: str) -> list[FreightService]:
    uf = str(uf or "").upper()
    return [service for service in SERVICES if uf in service.rules]


def quote_freight(city: str, service_key: str, order_value) -> dict:
    place = resolve_city(city)
    if not place.get("ok"):
        return {"ok": False, "reason": place.get("reason", "Cidade inválida.")}
    value = parse_brl(order_value)
    if value is None:
        return {"ok": False, "reason": "Informe um valor válido. Ex.: 980,00"}
    service = SERVICE_BY_KEY.get(str(service_key or ""))
    if service is None:
        return {"ok": False, "reason": "Escolha a transportadora."}
    rule = service.rules.get(place["uf"])
    if rule is None:
        return {"ok": False, "reason": "Essa transportadora não tem regra para a UF escolhida."}

    base = {
        "ok": True,
        "city": place["city"],
        "uf": place["uf"],
        "value": value,
        "service_key": service.key,
        "carrier": service.carrier,
        "branch": service.branch,
        "code": service.code,
        "service_label": service.label,
        "cutoff": rule.cutoff,
        "note": rule.note,
        "free_from": rule.free_from,
    }

    if rule.free_from is not None and value >= rule.free_from:
        return {**base, "status": "free", "fee": _d(0), "missing": _d(0)}

    for minimum, fee in rule.tiers:
        if value >= minimum:
            missing = (rule.free_from - value) if rule.free_from is not None else None
            return {**base, "status": "paid", "fee": fee, "missing": missing}

    return {
        **base,
        "status": "negotiated",
        "fee": None,
        "missing": (rule.free_from - value) if rule.free_from is not None else None,
    }


def copy_message(quote: dict) -> str:
    if not quote.get("ok"):
        return ""
    carrier = quote["carrier"]
    cutoff = quote.get("cutoff")
    cutoff_text = "" if not cutoff or cutoff == "Em negociação" else f" Horário de corte: {cutoff}."
    if quote["status"] == "free":
        return f"O pedido tem frete grátis pela {carrier}.{cutoff_text}".strip()
    if quote["status"] == "paid":
        text = f"O frete pela {carrier} fica {brl(quote['fee'])}."
        if quote.get("missing") is not None and quote["missing"] > 0:
            text += f" Faltam {brl(quote['missing'])} em produtos para o frete grátis."
        return (text + cutoff_text).strip()
    return f"O frete pela {carrier} precisa ser confirmado com a transportadora."


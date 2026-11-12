"""Versioned club-identity proposals. Strengths are fictional priors."""

FOREIGN = {
    "ARG": "River Plate|Boca Juniors|Racing Club|Estudiantes de La Plata|Vélez Sarsfield|Lanús|Independiente|San Lorenzo|Rosario Central|Talleres|Argentinos Juniors|Defensa y Justicia|Huracán|Newell’s Old Boys|Belgrano|Godoy Cruz|Banfield|Unión de Santa Fe|Platense",
    "BOL": "Bolívar|The Strongest|Always Ready|Blooming|Oriente Petrolero|Wilstermann|Nacional Potosí|Aurora|Guabirá|Real Tomayapo|Independiente Petrolero",
    "CHI": "Colo-Colo|Universidad de Chile|Universidad Católica|Palestino|Coquimbo Unido|Unión Española|Huachipato|Everton de Viña del Mar|Audax Italiano|Cobresal|Ñublense|O’Higgins",
    "COL": "Atlético Nacional|Millonarios|Junior de Barranquilla|América de Cali|Independiente Medellín|Independiente Santa Fe|Deportes Tolima|Deportivo Cali|Once Caldas|Deportivo Pereira|La Equidad|Atlético Bucaramanga",
    "ECU": "LDU Quito|Independiente del Valle|Barcelona SC|Emelec|Aucas|Universidad Católica del Ecuador|El Nacional|Delfín|Mushuc Runa|Deportivo Cuenca|Orense|Macará",
    "PAR": "Olimpia|Cerro Porteño|Libertad|Guaraní|Sportivo Luqueño|Nacional (PAR)|Sportivo Ameliano|General Caballero JLM|Sportivo Trinidense|2 de Mayo|Sol de América",
    "PER": "Universitario|Alianza Lima|Sporting Cristal|Melgar|Cusco FC|Cienciano|Sport Huancayo|ADT|Deportivo Garcilaso|Atlético Grau|Universidad César Vallejo|Alianza Atlético",
    "URU": "Peñarol|Nacional (URU)|Defensor Sporting|Liverpool Montevideo|Danubio|Boston River|Montevideo Wanderers|Cerro Largo|Racing Montevideo|River Plate Montevideo|Montevideo City Torque|Plaza Colonia",
    "VEN": "Deportivo Táchira|Caracas FC|Deportivo La Guaira|Carabobo FC|Monagas SC|Metropolitanos FC|Portuguesa FC|Academia Puerto Cabello|Zamora FC|Estudiantes de Mérida|UCV FC|Rayo Zuliano",
}

# Ordered development priors within each federation, with a separate top-flight tier.
BRAZIL = {
    "RJ": "Flamengo|Fluminense|Botafogo|Vasco|Volta Redonda|Nova Iguaçu|Portuguesa-RJ|Madureira|Boavista-RJ|Bangu|Olaria|Maricá|America-RJ|Resende|Audax Rio",
    "SP": "Palmeiras|Corinthians|São Paulo|Santos|Bragantino|Mirassol|Novorizontino|Ponte Preta|Guarani-SP|Botafogo-SP|Ituano|São Bernardo|Ferroviária|Portuguesa-SP|Água Santa|Inter de Limeira|Votuporanguense|Monte Azul|Santo André|São Caetano|Taubaté|Linense",
    "MG": "Atlético-MG|Cruzeiro|América-MG|Athletic Club|Tombense|Villa Nova-MG|Pouso Alegre|Uberlândia|Itabirito|Democrata-GV",
    "RS": "Grêmio|Internacional|Juventude|Caxias|Ypiranga-RS|São José-RS|Brasil de Pelotas|São Luiz-RS|Guarany de Bagé|Pelotas|Avenida",
    "PR": "Athletico-PR|Coritiba|Operário-PR|Londrina|Maringá|Cascavel|Cianorte|Azuriz|Paraná Clube",
    "SC": "Criciúma|Chapecoense|Avaí|Figueirense|Brusque|Joinville|Barra-SC|Marcílio Dias|Concórdia",
    "GO": "Goiás|Atlético-GO|Vila Nova-GO|Aparecidense|Goiânia|Goianésia|Goiatuba|Anápolis",
    "BA": "Bahia|Vitória|Juazeirense|Barcelona de Ilhéus|Jequié|Jacuipense",
    "CE": "Fortaleza|Ceará|Ferroviário-CE|Iguatu|Horizonte|Maracanã-CE|Floresta",
    "PE": "Sport|Náutico|Santa Cruz-PE|Retrô|Central-PE|Salgueiro",
    "PA": "Paysandu|Remo|Tuna Luso|Águia de Marabá|Cametá",
    "RN": "ABC|América-RN|Santa Cruz-RN|Potiguar de Mossoró",
    "AL": "CRB|CSA|ASA|Penedense|CSE",
    "MA": "Sampaio Corrêa|Maranhão|Moto Club|Imperatriz",
    "PB": "Botafogo-PB|Sousa|Treze|Campinense",
    "PI": "Altos|Parnahyba|River-PI|Fluminense-PI",
    "AM": "Amazonas|Manaus|Manauara|Nacional-AM",
    "SE": "Confiança|Sergipe|Lagarto|Itabaiana",
    "DF": "Brasiliense|Ceilândia|Capital-DF|Gama",
    "MT": "Cuiabá|Mixto|Luverdense|União Rondonópolis",
    "MS": "Operário-MS|Dourados|Costa Rica-MS",
    "ES": "Rio Branco-ES|Porto Vitória|Desportiva Ferroviária",
    "RO": "Porto Velho|Barcelona-RO|Ji-Paraná",
    "TO": "Tocantinópolis|União-TO",
    "AC": "Rio Branco-AC|Humaitá|Independência-AC",
    "AP": "Trem|Oratório",
    "RR": "São Raimundo-RR|Grêmio Sampaio",
}

ALIASES = {
    "Vasco": ("Vasco da Gama",),
    "Athletico-PR": ("Athletico Paranaense",),
    "Bragantino": ("Red Bull Bragantino",),
    "Sport": ("Sport Recife", "Sport Club do Recife"),
    "Vitória": ("Vitória-BA",),
    "Atlético-MG": ("Atlético Mineiro",),
    "Atlético-GO": ("Atlético Goianiense",),
    "Vila Nova-GO": ("Vila Nova",),
    "Estudiantes de La Plata": ("Estudiantes",),
    "Junior de Barranquilla": ("Junior", "Atlético Junior"),
    "Independiente Santa Fe": ("Santa Fe",),
    "Everton de Viña del Mar": ("Everton (CHI)",),
    "Universidad Católica": ("Universidad Católica (CHI)",),
    "Universidad Católica del Ecuador": ("Universidad Católica (ECU)", "Universidad Católica (Ecuador)"),
    "Nacional (PAR)": ("Nacional Asunción", "Nacional (PARAGUAY)"),
    "Liverpool Montevideo": ("Liverpool (URU)",),
    "Racing Montevideo": ("Racing (URU)",),
    "Newell’s Old Boys": ("Newell's Old Boys",),
    "Ñublense": ("Ñublense (CHI)",),
    "O’Higgins": ("O'Higgins",),
}

FOREIGN_PEAK = {"ARG": 81, "BOL": 73, "CHI": 76, "COL": 77, "ECU": 78,
                "PAR": 77, "PER": 74, "URU": 78, "VEN": 71}
BRA_STRONG = frozenset(("Coritiba", "Goiás", "Atlético-GO", "Ceará", "Sport", "Cuiabá",
                        "América-MG", "Criciúma", "Avaí", "Chapecoense", "Remo", "Paysandu",
                        "Náutico", "Ponte Preta", "Novorizontino", "Juventude", "Vila Nova-GO",
                        "CRB", "Operário-PR", "Amazonas", "Volta Redonda", "Londrina", "Athletic Club"))


def entries():
    for country, roster in sorted(FOREIGN.items()):
        for index, name in enumerate(roster.split("|")):
            yield country, None, name, max(60, round(FOREIGN_PEAK[country] - .95 * index, 1))
    for state, roster in sorted(BRAZIL.items()):
        for index, name in enumerate(roster.split("|")):
            yield "BRA", state, name, (72 - index % 3 if name in BRA_STRONG
                                       else max(56, 65 - index // 2))

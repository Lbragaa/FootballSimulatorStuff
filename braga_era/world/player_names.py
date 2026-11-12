"""Deterministic synthetic names with separate identity and nationality."""
from random import Random
from ..history import digest

POLICY = "south-american-player-names-1"
SPANISH_GIVEN = "Adrián Alejandro Andrés Bruno Camilo Carlos Cristian Diego Emiliano Esteban Facundo Felipe Franco Gabriel Gonzalo Ignacio Javier Joaquín Jorge José Juan Julián Leonardo Lucas Luis Manuel Martín Mateo Matías Miguel Nicolás Pablo Rafael Rodrigo Samuel Santiago Sebastián Tomás Vicente"
SPANISH_FAMILY = "Acosta Aguilar Alvarado Benítez Cabrera Cárdenas Castro Delgado Díaz Domínguez Escobar Espinoza Fernández Flores Franco García González Herrera Jiménez López Martínez Medina Molina Morales Moreno Navarro Núñez Ortiz Paredes Pérez Ramírez Reyes Ríos Rivera Rodríguez Rojas Romero Salazar Sánchez Silva Soto Suárez Torres Vargas Vera Villalba"
COUNTRY = {
    "ARG": ("Agustín Bautista Lautaro Thiago", "Ferreyra Mansilla Sosa Arce Bustos Correa"),
    "BOL": ("Álvaro Limberg Rubén", "Mamani Quispe Choque Condori Calle Arancibia"),
    "CHI": ("Benjamín Cristóbal Gaspar", "Araya Jara Riquelme Sepúlveda Valdés Alarcón"),
    "COL": ("Jhon Yerson Johan", "Mosquera Caicedo Banguera Cuesta Zapata Murillo"),
    "ECU": ("Piero Moisés Jordy", "Mina Caicedo Estupiñán Cevallos Minda Valencia"),
    "PAR": ("Derlis Julio Antonio", "Gamarra Cáceres Ayala Cardozo Lezcano Sanabria"),
    "PER": ("Renato Paolo Gianluca", "Huamán Quispe Advíncula Yupanqui Farfán Chacón"),
    "URU": ("Federico Enzo Álvaro", "Bentancur Zabaleta Techera Pereira Varela"),
    "VEN": ("Yeferson Salomón Darwin", "Rondón Soteldo Orozco Fariñez Peñaranda Cova"),
    "BRA": ("Adriano André Antônio Bruno Caio Cauã Daniel Davi Eduardo Felipe Gabriel Gustavo Henrique Hugo Igor João José Leonardo Lucas Luiz Marcelo Marcos Matheus Miguel Murilo Pedro Rafael Renan Rodrigo Samuel Thiago Victor Vinícius Vítor",
            "Almeida Alves Andrade Araújo Azevedo Barros Batista Borges Cardoso Carvalho Costa Cunha Dias Fernandes Ferreira Fonseca Freitas Gomes Lima Lopes Machado Martins Mendes Monteiro Moraes Nascimento Nunes Oliveira Pereira Ribeiro Rocha Santos Silva Souza Teixeira Vieira"),
}


def generate(seed, player_id, host, used):
    rng = Random(int(digest([POLICY, seed, player_id]), 16))
    if host not in COUNTRY:
        raise ValueError("Registered South American country required")
    country = host if rng.random() < .88 else rng.choice(sorted(set(COUNTRY) - {host}))
    local_given, local_family = (values.split() for values in COUNTRY[country])
    common_given = local_given if country == "BRA" else SPANISH_GIVEN.split()
    common_family = local_family if country == "BRA" else SPANISH_FAMILY.split()
    for _ in range(128):
        given = rng.choice(local_given if rng.random() < .35 else common_given)
        surname = rng.choice(local_family if rng.random() < .40 else common_family)
        rest = [name for name in common_given if name != given]
        first = [given, rng.choice(rest)] if rng.random() < .35 else [given]
        family = [name for name in common_family if name != surname]
        last = [surname, rng.choice(family)] if rng.random() < .40 else [surname]
        name = " ".join(first + last)
        if name not in used:
            return name, country
    raise ValueError("Synthetic name uniqueness bound exhausted")

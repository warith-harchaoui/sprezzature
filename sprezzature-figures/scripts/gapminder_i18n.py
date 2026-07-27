#!/usr/bin/env python3
"""
gapminder_i18n — French translations for the Hans Rosling tribute chart.

Keeps ``make_gapminder.py`` bilingual: the same real data, rendered once in
English and once in idiomatic French (axes, legend, region names, and every
country / historical-entity label). Countries not listed fall back to their
English name (which is often identical in French, e.g. ``France``, ``Canada``).

Author
------
`Warith Harchaoui, Ph.D. <https://www.linkedin.com/in/warith-harchaoui/>`_
"""

from __future__ import annotations

REGIONS_FR = {
    "Asia": "Asie", "Africa": "Afrique", "Americas": "Amériques",
    "Europe": "Europe", "Oceania": "Océanie",
}

# Interface strings, keyed by a stable identifier used in make_gapminder.py.
LABELS_FR = {
    "title_link": "Hommage à Hans Rosling",
    "title_rest": " &#8212; Santé et richesse des nations &#8212; 1950&#8211;2025",
    "subtitle": "Chaque bulle représente un pays. Sa taille indique la population et sa couleur la région.",
    "x_axis": "PIB par habitant (échelle log) &#8594;",
    "y_axis": "Espérance de vie (années) &#8594;",
    "legend_region": "RÉGION",
    "legend_population": "POPULATION",
    "data_link": "Données en hommage à Hans Rosling",
    "title_a11y": "Hommage à Hans Rosling — Santé et richesse des nations",
    "pop_1b": "1 milliard", "pop_250m": "250 millions", "pop_50m": "50 millions",
    "desc": (
        "Graphique à bulles animé en hommage à Hans Rosling, à partir de données réelles pour "
        "tous les pays, une image par année de 1950 à 2025. Chaque bulle est un pays : "
        "l'horizontale est le PIB par habitant (échelle log), la verticale l'espérance de vie, "
        "l'aire la population, la couleur la région du monde. Un compteur d'années défile année par "
        "année tandis que les bulles montent vers le haut et la droite. Les fédérations (URSS, "
        "Yougoslavie, Tchécoslovaquie) apparaissent comme une seule bulle jusqu'à leur dissolution, "
        "puis leurs États successeurs apparaissent ; les nations divisées (Allemagne de l'Est et de "
        "l'Ouest, Vietnam et Yémen du Nord et du Sud) apparaissent comme deux bulles jusqu'à leur "
        "fusion. Les années récentes sont en partie projetées."),
}

# Historical / period-correct names, mirroring NAME_HISTORY in make_gapminder.py.
HISTORY_FR = {
    "Myanmar": "Birmanie", "Sri Lanka": "Ceylan", "Tanganyika": "Tanganyika",
    "Rhodesia": "Rhodésie", "East Bengal": "Bengale-Oriental",
    "East Pakistan": "Pakistan oriental", "Belgian Congo": "Congo belge",
    "Congo-Kinshasa": "Congo-Kinshasa", "Zaire": "Zaïre", "DR Congo": "RD Congo",
    "Ceylon": "Ceylan", "Burma": "Birmanie",
}

COUNTRIES_FR = {
    "Afghanistan": "Afghanistan", "Albania": "Albanie", "Algeria": "Algérie",
    "Angola": "Angola", "Argentina": "Argentine", "Armenia": "Arménie",
    "Australia": "Australie", "Austria": "Autriche", "Azerbaijan": "Azerbaïdjan",
    "Bahrain": "Bahreïn", "Bangladesh": "Bangladesh", "Barbados": "Barbade",
    "Belarus": "Biélorussie", "Belgium": "Belgique", "Benin": "Bénin",
    "Bolivia": "Bolivie", "Bosnia and Herzegovina": "Bosnie-Herzégovine",
    "Botswana": "Botswana", "Brazil": "Brésil", "Bulgaria": "Bulgarie",
    "Burkina Faso": "Burkina Faso", "Burundi": "Burundi", "Cambodia": "Cambodge",
    "Cameroon": "Cameroun", "Canada": "Canada", "Cape Verde": "Cap-Vert",
    "Central African Republic": "République centrafricaine", "Chad": "Tchad",
    "Chile": "Chili", "China": "Chine", "Colombia": "Colombie", "Comoros": "Comores",
    "Congo": "Congo", "Costa Rica": "Costa Rica", "Cote d'Ivoire": "Côte d'Ivoire",
    "Croatia": "Croatie", "Cuba": "Cuba", "Cyprus": "Chypre", "Czechia": "Tchéquie",
    "Czechoslovakia": "Tchécoslovaquie",
    "Democratic Republic of Congo": "République démocratique du Congo",
    "Denmark": "Danemark", "Djibouti": "Djibouti", "Dominica": "Dominique",
    "Dominican Republic": "République dominicaine", "East Germany": "Allemagne de l'Est",
    "Ecuador": "Équateur", "Egypt": "Égypte", "El Salvador": "Salvador",
    "Equatorial Guinea": "Guinée équatoriale", "Estonia": "Estonie",
    "Eswatini": "Eswatini", "Ethiopia": "Éthiopie", "Finland": "Finlande",
    "France": "France", "Gabon": "Gabon", "Gambia": "Gambie", "Georgia": "Géorgie",
    "Germany": "Allemagne", "Ghana": "Ghana", "Greece": "Grèce",
    "Guatemala": "Guatemala", "Guinea": "Guinée", "Guinea-Bissau": "Guinée-Bissau",
    "Haiti": "Haïti", "Honduras": "Honduras", "Hong Kong": "Hong Kong",
    "Hungary": "Hongrie", "Iceland": "Islande", "India": "Inde",
    "Indonesia": "Indonésie", "Iran": "Iran", "Iraq": "Irak", "Ireland": "Irlande",
    "Israel": "Israël", "Italy": "Italie", "Jamaica": "Jamaïque", "Japan": "Japon",
    "Jordan": "Jordanie", "Kazakhstan": "Kazakhstan", "Kenya": "Kenya",
    "Kuwait": "Koweït", "Kyrgyzstan": "Kirghizistan", "Laos": "Laos",
    "Latvia": "Lettonie", "Lebanon": "Liban", "Lesotho": "Lesotho",
    "Liberia": "Liberia", "Libya": "Libye", "Lithuania": "Lituanie",
    "Luxembourg": "Luxembourg", "Madagascar": "Madagascar", "Malawi": "Malawi",
    "Malaysia": "Malaisie", "Mali": "Mali", "Malta": "Malte",
    "Mauritania": "Mauritanie", "Mauritius": "Maurice", "Mexico": "Mexique",
    "Moldova": "Moldavie", "Mongolia": "Mongolie", "Montenegro": "Monténégro",
    "Morocco": "Maroc", "Mozambique": "Mozambique", "Myanmar": "Myanmar",
    "Namibia": "Namibie", "Nepal": "Népal", "Netherlands": "Pays-Bas",
    "New Zealand": "Nouvelle-Zélande", "Nicaragua": "Nicaragua", "Niger": "Niger",
    "Nigeria": "Nigeria", "North Korea": "Corée du Nord",
    "North Macedonia": "Macédoine du Nord", "North Vietnam": "Vietnam du Nord",
    "North Yemen": "Yémen du Nord", "Norway": "Norvège", "Oman": "Oman",
    "Pakistan": "Pakistan", "Palestine": "Palestine", "Panama": "Panama",
    "Paraguay": "Paraguay", "Peru": "Pérou", "Philippines": "Philippines",
    "Poland": "Pologne", "Portugal": "Portugal", "Puerto Rico": "Porto Rico",
    "Qatar": "Qatar", "Romania": "Roumanie", "Russia": "Russie", "Rwanda": "Rwanda",
    "Saint Lucia": "Sainte-Lucie", "Sao Tome and Principe": "Sao Tomé-et-Principe",
    "Saudi Arabia": "Arabie saoudite", "Senegal": "Sénégal", "Serbia": "Serbie",
    "Seychelles": "Seychelles", "Sierra Leone": "Sierra Leone", "Singapore": "Singapour",
    "Slovakia": "Slovaquie", "Slovenia": "Slovénie", "South Africa": "Afrique du Sud",
    "South Korea": "Corée du Sud", "South Vietnam": "Vietnam du Sud",
    "South Yemen": "Yémen du Sud", "Spain": "Espagne", "Sri Lanka": "Sri Lanka",
    "Sweden": "Suède", "Switzerland": "Suisse", "Syria": "Syrie", "Taiwan": "Taïwan",
    "Tajikistan": "Tadjikistan", "Tanzania": "Tanzanie", "Thailand": "Thaïlande",
    "Togo": "Togo", "Trinidad and Tobago": "Trinité-et-Tobago", "Tunisia": "Tunisie",
    "Turkey": "Turquie", "Turkmenistan": "Turkménistan", "USSR": "URSS",
    "Uganda": "Ouganda", "Ukraine": "Ukraine",
    "United Arab Emirates": "Émirats arabes unis", "United Kingdom": "Royaume-Uni",
    "United States": "États-Unis", "Uruguay": "Uruguay", "Uzbekistan": "Ouzbékistan",
    "Venezuela": "Venezuela", "Vietnam": "Vietnam", "West Germany": "Allemagne de l'Ouest",
    "Yemen": "Yémen", "Yugoslavia": "Yougoslavie", "Zambia": "Zambie",
    "Zimbabwe": "Zimbabwe",
}

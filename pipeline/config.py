PAYS_CODES = [
    'ITA', 'FJI', 'CAN', 'MEX', 'IDN', 'GRL', 'NAM', 'JAM', 'GRC', 'GEO',
    'DEU', 'AUS', 'JPN', 'NLD', 'MMR', 'SWE', 'USA', 'NOR', 'BEL', 'ISL',
    'KOR', 'TUR', 'IRL', 'ZMB', 'POL', 'JOR', 'MDV', 'ASM', 'AGO', 'BRB',
    'ESP', 'BEN', 'BIH', 'ALB', 'BRA', 'KHM', 'MAR', 'MOZ', 'TZA', 'BMU',
    'CHL', 'CHN', 'NPL', 'NZL', 'COL', 'COK', 'MKD', 'HRV', 'PAN', 'DOM',
    'ECU', 'EGY', 'PER', 'FRA', 'GNQ', 'SWZ', 'BGR', 'SMR', 'FIN', 'LKA',
    'SEN', 'SGP', 'SVN', 'MLT', 'GUY', 'VNM', 'IND', 'HUN', 'MCO', 'NCL',
    'KEN', 'LSO', 'QAT', 'KAZ', 'LAO', 'LTU', 'MNE', 'MYS', 'MUS', 'OMN',
    'ZAF', 'MDA', 'SUR', 'THA', 'GBR', 'NIC', 'PRI', 'PRY', 'PHL', 'CHE',
    'PRT', 'SLE', 'REU', 'ROU', 'LCA', 'STP', 'SYC', 'UKR', 'MDG', 'TGO',
    'TTO', 'TUN', 'ARG', 'VIR', 'TKM', 'UZB', 'BGD', 'KGZ', 'PLW', 'GRD',
    'PNG', 'MWI', 'VEN', 'BTN', 'PAK', 'CZE', 'KNA', 'SLB', 'CRI', 'TON',
    'VUT', 'TCA', 'TJK', 'AUT', 'AZE', 'BLR', 'BOL', 'BDI', 'CMR', 'CPV',
    'XKX', 'SRB', 'CYP', 'CUB', 'DMA', 'EST', 'GAB', 'CIV', 'LUX', 'LVA',
    'MNG', 'COG', 'RWA', 'WSM', 'UGA', 'BHR', 'URY', 'COM', 'PYF', 'GMB',
    'GTM', 'ARE', 'SLV', 'GHA', 'GUF', 'SVK', 'HKG', 'BLZ', 'ZWE', 'RUS',
    'IRN', 'KWT', 'DNK', 'BWA'
]

INDICATEURS = {
    "SH.H2O.BASW.ZS":    "Accès eau potable (%)",
    "EG.ELC.ACCS.ZS":    "Accès électricité (%)",
    "IT.NET.USER.ZS":    "Accès Internet (%)",
    "SI.SPR.PCAP":       "Revenu moyen/habitant ($/jour)",
    "ST.INT.ARVL":       "Arrivées touristes internationaux",
    "NY.GDP.PCAP.CD":    "PIB par habitant (USD)",
    "SP.DYN.LE00.IN":    "Espérance de vie (années)",
    "SH.STA.TRAF.P5":    "Mortalité accidents route (pour 100k)",
}

ANNEES = range(2010, 2024)
OUTPUT_CSV = "output/donnees_touriste.csv"
OUTPUT_DB  = "output/donnees_touriste.db"
TABLE_NAME = "pays_touriste"
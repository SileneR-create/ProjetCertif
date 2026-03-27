import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PAYS_CODES = pd.read_csv(os.path.join(BASE_DIR,"DATA", "processed", "WorldTravel_ISO.csv"))["code_3L"].tolist()

INDICATEURS = {
    # 🏥 SÉCURITÉ & SANTÉ
    "SH.H2O.BASW.ZS":    "Accès eau potable (% pop)",
    "SP.DYN.LE00.IN":   "Espérance de vie (années)",
    "SH.MED.PHYS.ZS":   "Médecins (pour 1000 habitants)",
    "SH.XPD.CHEX.PC.CD":"Dépenses santé par habitant (USD)",

    # 🚗 INFRASTRUCTURE & TRANSPORT
    "EG.ELC.ACCS.ZS":    "Accès électricité (% pop)",
    "IT.NET.USER.ZS":    "Accès Internet (% pop)",
    "EN.URB.MCTY.TL.ZS": "Pop. dans grandes agglomérations (%)",
    "EN.POP.DNST":       "Densité de population (hab/km²)",

    # 💰 ÉCONOMIE LOCALE & COÛT DE LA VIE
    "SI.SPR.PCAP":       "Revenu moyen par habitant ($/jour)",
    "SI.POV.DDAY":       "Pauvreté < 3$/jour (% pop)",
    "SI.POV.NAHC":       "Pauvreté seuil national (% pop)",
    "SI.SPR.PC40":       "Revenu 40% les plus pauvres ($/jour)",

    # 🌿 ENVIRONNEMENT & CLIMAT
    "SP.URB.TOTL.IN.ZS": "Population urbaine (% total)",
    "SP.RUR.TOTL.ZS":    "Population rurale (% total)",

    # 🌍 Tourisme
    "ST.INT.ARVL":       "Arrivées touristes internationaux (nb)",
    "ST.INT.DPRT":       "Départs touristes internationaux (nb)",
    "ST.INT.RCPT.CD":    "Recettes tourisme (USD)",
    "ST.INT.RCPT.XP.ZS": "Recettes tourisme (% exportations)",
    "ST.INT.TVLR.CD":    "Recettes voyages touristiques (USD)",
    "ST.INT.XPND.CD":    "Dépenses tourisme (USD)",
    "BX.GSR.TRVL.ZS":   "Services voyage (% exports de services)",
        
    # 💱 Économie pratique
    "NY.GDP.PCAP.CD":   "PIB par habitant (USD)",
}

ANNEES = range(2010, 2024)
OUTPUT_CSV = "DATA/external/donnees_touriste.csv"
OUTPUT_DB  = "DATA/external/donnees_touriste.db"
TABLE_NAME = "pays_touriste"


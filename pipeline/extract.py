import wbgapi as wb
from config import PAYS_CODES, INDICATEURS, ANNEES

def extract():
    print("📥 [EXTRACT] Téléchargement des données World Bank...")

    df = wb.data.DataFrame(
        series=list(INDICATEURS.keys()),
        economy=PAYS_CODES,
        time=ANNEES
    )

    print(f"✅ Shape brut : {df.shape}")
    return df
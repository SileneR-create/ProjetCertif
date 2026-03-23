from extract import extract
from transform import transform
from load import load
import traceback

def run_pipeline():
    print("🚀 Démarrage de la pipeline...\n")

    try:
        df_brut   = extract()        # pas de paramètre
        df_propre = transform(df_brut)
        load(df_propre)
        print("\n✅ Pipeline terminée avec succès !")
        return df_propre

    except Exception as e:
        print(f"\n❌ Erreur dans la pipeline : {e}")
        traceback.print_exc()

if __name__ == "__main__":
    df = run_pipeline()
    print(df)
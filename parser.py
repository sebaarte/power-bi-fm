import pandas as pd
import tkinter as tk
from tkinter import filedialog
import os
import sys
import chardet

# =============================================================
# 1. Ouvrir l'explorateur Windows pour choisir un fichier HTML
# =============================================================
root = tk.Tk()
root.withdraw()

fichier_html = filedialog.askopenfilename(
    title="Sélectionner un fichier HTML",
    filetypes=[("Fichiers HTML", "*.html *.htm"), ("Tous les fichiers", "*.*")]
)

if not fichier_html:
    print("❌ Aucun fichier sélectionné. Arrêt du script.")
    sys.exit()

print(f"✅ Fichier sélectionné : {fichier_html}")

# =============================================================
# 2. Détecter l'encodage du fichier source
# =============================================================
with open(fichier_html, "rb") as f:
    resultat = chardet.detect(f.read())
    encodage_source = resultat["encoding"]
    confiance = resultat["confidence"]

print(f"🔍 Encodage détecté : {encodage_source} (confiance : {confiance:.0%})")

# =============================================================
# 3. Lire le contenu HTML avec le bon encodage
# =============================================================
try:
    with open(fichier_html, "r", encoding=encodage_source) as f:
        contenu_html = f.read()

    liste_tables = pd.read_html(contenu_html, decimal=".")
    print(f"📊 {len(liste_tables)} tableau(x) trouvé(s) dans le fichier HTML.")

except Exception as e:
    print(f"❌ Erreur lors de la lecture : {e}")
    print("🔄 Tentative avec UTF-8...")
    try:
        with open(fichier_html, "r", encoding="utf-8") as f:
            contenu_html = f.read()
        liste_tables = pd.read_html(contenu_html, decimal=".")
    except Exception as e2:
        print(f"❌ Échec définitif : {e2}")
        sys.exit()

# =============================================================
# 4. Traiter chaque tableau et sauvegarder en CSV
# =============================================================
dossier_sortie = os.path.dirname("./output_files/")
nom_base = os.path.splitext(os.path.basename(fichier_html))[0]

ENCODAGE_SORTIE = "utf-8-sig"

for i, df in enumerate(liste_tables):

    print(f"\n--- Tableau {i + 1} ---")
    print(f"    Dimensions : {df.shape[0]} lignes × {df.shape[1]} colonnes")

    # ---------------------------------------------------------
    # 4a. Remplacer tous les "-" par des champs vides (NaN)
    # ---------------------------------------------------------
    nb_remplacements = (df == "-").sum().sum() + \
                       (df == "—").sum().sum() + \
                       (df == "–").sum().sum()

    df = df.replace(["-", "—", "–"], pd.NA)
    df = df.apply(lambda col: col.map(
        lambda x: pd.NA if isinstance(x, str) and x.strip() in ["-", "—", "–"] else x
    ))

    print(f"    🔄 {nb_remplacements} valeur(s) '-' remplacée(s) par des champs vides")

    # ---------------------------------------------------------
    # 4a-bis. Tenter de convertir toutes les colonnes en numérique
    # ---------------------------------------------------------
    nb_converties = 0
    for col in df.columns:
        if df[col].dtype == "object" or str(df[col].dtype) == "string":
            converti = pd.to_numeric(df[col], errors="coerce")
            # On ne garde la conversion que si au moins une valeur a pu être convertie
            nb_non_null_avant = df[col].notna().sum()
            nb_non_null_apres = converti.notna().sum()
            # Si on ne perd pas TOUTES les valeurs, on accepte la conversion
            if nb_non_null_apres > 0 and nb_non_null_apres >= nb_non_null_avant * 0.5:
                df[col] = converti
                nb_converties += 1

    print(f"    🔢 {nb_converties} colonne(s) texte convertie(s) en numérique")

    # ---------------------------------------------------------
    # 4b. Identifier les colonnes numériques
    # ---------------------------------------------------------
    colonnes_numeriques = df.select_dtypes(include=["float64", "float32", "int64", "int32"]).columns
    print(f"    Colonnes numériques détectées : {list(colonnes_numeriques)}")

    # ---------------------------------------------------------
    # 4c. Aperçu
    # ---------------------------------------------------------
    print(f"\n    Aperçu (5 premières lignes) :")
    print(df.head().to_string())

    # ---------------------------------------------------------
    # 4d. Sauvegarder en CSV
    # ---------------------------------------------------------
    if len(liste_tables) == 1:
        fichier_csv = os.path.join(dossier_sortie, f"{nom_base}.csv")
    else:
        fichier_csv = os.path.join(dossier_sortie, f"{nom_base}_tableau{i + 1}.csv")

    df.to_csv(
        fichier_csv,
        index=False,
        sep=";",
        decimal=",",
        encoding=ENCODAGE_SORTIE
    )

    print(f"\n    💾 Sauvegardé en [{ENCODAGE_SORTIE}] : {fichier_csv}")

print("\n✅ Terminé ! Tous les tableaux ont été convertis en CSV.")

# King County Real Estate Lab

Application Streamlit pour explorer les transactions residentielles du comte de King (Seattle, WA), segmenter le marche et evaluer une propriete individuelle a partir de comparables.

## Fonctionnalites

- Tableau de bord interactif avec filtres de marche
- Visualisations `matplotlib` pour le prix, le volume, les zipcodes et la qualite des biens
- Evaluateur de propriete avec comparables et fourchette de juste valeur
- Assistant IA optionnel via l'API OpenAI pour generer une note d'analyse en francais

## Lancer le projet

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Option IA

L'onglet `Assistant IA` fonctionne si vous fournissez une cle API OpenAI:

```bash
set OPENAI_API_KEY=votre_cle
```

Vous pouvez aussi coller la cle directement dans l'interface.

## Fichiers

- `app.py` : application Streamlit complete
- `kc_house_data.csv` : dataset historique
- `dictionnaire_variables (1).txt` : dictionnaire des variables

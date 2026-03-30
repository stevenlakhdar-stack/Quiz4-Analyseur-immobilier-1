# Analyseur immobilier interactif - King County

Application Streamlit conçue pour explorer le marché résidentiel du comté de King (région de Seattle) à partir du dataset `kc_house_data.csv`.

## Ce que fait l'application

- exploration interactive du marché avec filtres sur prix, période, surface, qualité et localisation
- visualisations financières en `matplotlib`
- repérage de transactions décotées par rapport à leur zipcode
- valorisation d'un bien individuel via un moteur de comparables
- génération d'une note d'analyse en français avec un LLM via l'API OpenAI

## Lancer l'application

1. Créez un environnement Python.
2. Installez les dépendances :

```bash
pip install -r requirements.txt
```

3. Lancez Streamlit :

```bash
streamlit run app.py
```

## Intégration LLM

L'application fonctionne sans clé API, avec un commentaire local de secours.

Pour activer la génération IA :

- définissez `OPENAI_API_KEY`
- optionnellement, définissez `OPENAI_MODEL` (par défaut : `gpt-5.4-mini`)

Exemples :

```bash
set OPENAI_API_KEY=sk-...
set OPENAI_MODEL=gpt-5.4-mini
streamlit run app.py
```

## Fichiers

- `app.py` : application principale
- `kc_house_data.csv` : données source
- `dictionnaire_variables (1).txt` : dictionnaire des colonnes

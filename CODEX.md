CRITIQUE : Ton optimisation précédente a OVERFITTÉ. Train ROI +25% mais Test ROI -100% (perte totale). Claude Code a fait mieux : Train -0.96%, Test +12.31% — un modèle qui généralise.
Ton erreur : tu as optimisé les paramètres sur le train set et ça ne tient pas sur le test. Un ROI train de +25% est un red flag évident d'overfitting.
Reprends de zéro avec une approche rigoureuse :
RÈGLES ANTI-OVERFITTING

JAMAIS optimiser les paramètres sur le train set puis évaluer sur le test set avec ces mêmes paramètres optimisés
Utiliser une validation croisée : 2021=train, 2022=validation, 2023=test out-of-sample
Les paramètres doivent être modérés : blend_weight entre 0.40-0.55, edge_threshold entre 3%-7%, shrinkage_k entre 30-80, HFA entre 1.03-1.10
Si le ROI train est > 15%, c'est de l'overfitting. Un bon modèle a un ROI train entre -5% et +10%
Le seul chiffre qui compte c'est le ROI TEST (out-of-sample)

CE QUE CLAUDE CODE A FAIT (à battre)

Blend 50/50 modèle/marché
Edge minimum 7%
Marchés : Over/Under 2.5 uniquement (pas H2H)
HFA 1.08
Shrinkage K=50
Résultat : 42 paris EPL 2023, ROI +12.31%, win rate 54.8%, Sharpe 0.97

TA MISSION

Implémenter une validation croisée propre (2021=train, 2022=val, 2023=test)
Grid search sur la validation 2022 (PAS sur le test 2023)
Trouver les meilleurs paramètres sur 2022, puis évaluer UNE SEULE FOIS sur 2023
Tester sur les 5 ligues × 3 saisons (EPL, La Liga, Bundesliga, Serie A, Ligue 1)
Comparer Kelly 1/4, Full Kelly, et Flat 1%
Afficher : ROI train, ROI validation, ROI test, win rate, Sharpe, max drawdown, nombre de paris
Tracer la courbe de calibration (probabilité prédite vs fréquence observée)
Equity curve pour chaque stratégie de staking

MÉTRIQUES À BATTRE

ROI test > +12.31% (Claude Code EPL 2023)
Sharpe > 0.97
Win rate > 54.8%
Nombre de paris > 42

BONUS : SAISON EN COURS

Ajouter la saison 2024-2025 comme deuxième test out-of-sample
Si le modèle est profitable sur 2023 ET 2024-2025, c'est validé

Le but : un modèle ROBUSTE qui gagne sur des données qu'il n'a JAMAIS vues. Pas un modèle qui mémorise le passé.

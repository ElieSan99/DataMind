# DataMind : Dashboard Analytics Agentique pour E-commerce

## Contexte et Objectifs

DataMind est une plateforme d'analyse intelligente conçue pour fournir des insights exploitables à partir de données e-commerce. Le projet s'appuie sur le dataset brésilien Olist, comprenant 100 000 commandes s'étalant de 2016 à 2018.

L'objectif principal était de dépasser les tableaux de bord statiques traditionnels en implémentant une approche "IA Agentique". Plutôt que de proposer des graphiques figés, le système utilise un orchestrateur qui comprend les requêtes en langage naturel, sélectionne les agents spécialisés appropriés et génère des visualisations dynamiques (Plotly) en temps réel.

## Architecture Technique

### Stack Intelligence Artificielle
- **Orchestrateur** : Développé avec LangGraph (v2) pour gérer un raisonnement multi-étapes avec maintien de l'état.
- **Agents Spécialisés** : 
  - Agent de Ventes : Analyse des tendances de revenus et de la performance des produits.
  - Agent de Cohortes : Étude de la rétention client et segmentation RFM.
  - Agent de Graphiques : Génération dynamique de JSON Plotly pour le rendu frontend.
- **LLM** : Propulsé par Groq (Llama 3.3 70b) pour une vitesse d'inférence inférieure à la seconde.

### Infrastructure et Backend
- **Framework** : FastAPI (Python) avec gestion asynchrone des tâches et streaming via SSE (Server-Sent Events).
- **Base de données** : PostgreSQL (hébergé sur Supabase) pour les requêtes transactionnelles et analytiques.
- **Déploiement** : 
  - Backend : Conteneurisé avec Docker et déployé sur Google Cloud Run (Serverless).
  - CI/CD : Automatisation des tests et du déploiement via GitHub Actions (Build Docker, Google Artifact Registry).

### Frontend
- **Framework** : Next.js 14+ (TypeScript, Tailwind CSS).
- **Communication** : Client SSE pour le streaming des tokens et des graphiques en temps réel, offrant une expérience utilisateur fluide.

## Solutions Implémentées

- **Streaming de Tokens** : Génération de réponses en temps réel pour réduire la latence perçue par l'utilisateur.
- **Génération Dynamique de Graphiques** : Le système détecte automatiquement le besoin d'une représentation visuelle et la génère à la volée.
- **Déploiement Résilient** : Optimisation du démarrage des conteneurs sur GCP Cloud Run, avec chargement différé (lazy loading) des modules d'IA et configuration du boost CPU au démarrage.
- **CI/CD Automatisé** : Un pipeline robuste qui valide le frontend et le backend avant toute mise à jour en production.

## Résultats

- **Accélération de la Prise de Décision** : Les utilisateurs obtiennent des analyses de cohortes complexes ou des tendances de vente via une simple question en langage naturel.
- **Infrastructure Scalable** : L'architecture serverless permet au système de passer à zéro instance lorsqu'il n'est pas utilisé, optimisant les coûts tout en gérant les pics de trafic.
- **Excellence UX** : Le retour d'information en temps réel et les visuels dynamiques offrent une sensation de produit premium comparée aux outils de BI traditionnels.

## Limites Actuelles et Améliorations Futures

- **Données Statiques** : L'implémentation actuelle utilise un import statique du dataset Olist. L'intégration de pipelines de données en temps réel (CDC) serait la prochaine étape.
- **Cas Limites du Raisonnement LLM** : Des requêtes extrêmement complexes ou ambiguës peuvent mener à une sélection d'agent sous-optimale ; un ingénierie de prompt plus poussée et des datasets d'évaluation (LLM-as-a-judge) sont nécessaires.
- **Limites de l'Offre Gratuite** : L'utilisation des paliers gratuits pour les API (Groq/Supabase) peut entraîner des interruptions de service temporaires sous forte charge.


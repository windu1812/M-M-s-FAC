# Guide de l'équipe CreditLens

À lire une fois en entier avant de commencer, puis à garder sous la main. Si une étape n'est pas claire, demande sur
le groupe, ou demande à ton assistant IA : « Explique-moi l'étape 5 de docs/guide-equipe.md ».

## En bref

1. Chacun a **une issue GitHub**, **une branche** et **ses propres fichiers**. On ne travaille jamais sur `main`.
2. Au début de chaque séance : se mettre sur sa branche et récupérer `main` (section 5).
3. À la fin de chaque séance : lancer les tests, puis faire un commit et un push. Une fois la tranche finie : ouvrir une pull request,
   relue par un coéquipier (section 6).
4. Jamais de `.env` dans Git, jamais de `--force`, jamais de chiffre inventé.

## 1. Qui fait quoi

| Qui | Issue | Tranche de `docs/plan.md` | Ta branche | Tes fichiers |
|---|---|---|---|---|
| Arthur | #3 (PR #4) | 2. Données SEC EDGAR | `3-data-fetch-and-clean-financial-data-from-sec-edgar` | `app/creditlens/data/` |
| Coco | #6 | 3. Ratios | `6-ratios-compute-ebitda-total-debt-net-debt-and-the-credit-ratios` | `app/creditlens/ratios.py`, `app/tests/test_ratios.py` |
| Maiwenn | #7 | 4. Drapeaux vert / orange / rouge | `7-flags-green-orange-red-thresholds-from-a-config-file` | `app/config/thresholds.toml`, `app/creditlens/flags.py`, `app/tests/test_flags.py` |
| Marc | #8 | 5. Tableau de bord | `8-dashboard-ticker-input-summary-cards-and-5-year-ratio-table` | `app/streamlit_app.py`, `app/creditlens/display.py`, `app/tests/test_app.py`, `app/tests/test_display.py` |
| François | #9 | 6. Graphiques et export Excel | `9-charts-and-excel-export` | `app/creditlens/charts.py`, `app/creditlens/export.py`, `app/tests/test_charts.py`, `app/tests/test_export.py` |

**Tranche 7, intégration et démo (à partir du 27 novembre) :**
- Arthur pilote : il fait tourner l'application de bout en bout et prépare la démo ;
- Maiwenn rédige le `README.md` de la racine et `AI-USAGE.md` ;
- tout le monde teste.

**Où trouver ce que ta tranche doit faire :**
- ton issue sur GitHub ;
- ta ligne de `docs/plan.md` ;
- les critères qu'elle cite dans `docs/acceptance.md`.

Les formules sont dans `docs/product.md`. Le format des tableaux échangés entre modules est fixé dans
`docs/architecture.md`, section « Contracts between parts ». Ainsi personne n'attend le code d'un autre : tu
travailles avec un petit tableau d'exemple qui suit ce format, marqué SAMPLE DATA.

**Relecture des pull requests** (proposition, à changer si vous voulez) :

| Pull request de | Relue par | Pourquoi |
|---|---|---|
| Arthur (données) | Coco | les ratios utilisent les données |
| Coco (ratios) | Maiwenn | les drapeaux utilisent les ratios |
| Maiwenn (drapeaux) | Coco | même raison, dans l'autre sens |
| Marc (tableau de bord) | François | les graphiques s'affichent dans la page |
| François (graphiques, Excel) | Marc | même raison, dans l'autre sens |

**Calendrier** (proposé dans `docs/plan.md`, à confirmer) :
- pull requests des tranches 2 à 6 ouvertes au plus tard le jeudi 26 novembre ;
- intégration du 27 au 29 novembre ;
- répétition de la démo le 30 novembre ;
- rendu le mardi 1er décembre 2026 à 23 h 59.

## 2. Les mots à connaître

- **Dépôt** (*repository*, « repo ») : le projet complet sur GitHub, avec tout son historique. Il n'y en a qu'un :
  https://github.com/windu1812/M-M-s-FAC. Chacun en a une copie sur son ordinateur (un *clone*).
- **Branche** : une version parallèle du projet. `main` est la version officielle. Chacun travaille sur sa
  branche sans gêner les autres.
- **Commit** : un enregistrement de tes changements, accompagné d'un message qui dit ce qui a changé.
- **Push** : envoyer tes commits de ton ordinateur vers GitHub. **Pull** : l'inverse, récupérer ce qui est sur
  GitHub.
- **Pull request (PR)** : une demande pour faire entrer ta branche dans `main`. Un coéquipier la relit avant.
- **Merge (fusion)** : faire entrer les changements d'une branche dans une autre.
- **Conflit** : deux personnes ont modifié les mêmes lignes, et Git te demande laquelle garder (section 10).

## 3. Première fois : accéder au projet (une fois par ordinateur)

### 3.1 Avoir le droit d'envoyer ton travail

1. Envoie ton pseudo GitHub à Arthur. Il t'invite sur le dépôt.
2. Accepte l'invitation : clique sur le lien de l'e-mail de GitHub, ou ouvre
   https://github.com/windu1812/M-M-s-FAC/invitations. Sans cela, tu peux lire le code (le dépôt est public),
   mais pas envoyer tes changements.

### 3.2 Installer les outils

- **git** : `git --version` doit afficher une version. Sinon, sur Mac lance `xcode-select --install`, sur Windows
  installe-le depuis https://git-scm.com.
- **GitHub CLI** (`gh`) : installe-le depuis https://cli.github.com, puis lance `gh auth login` et choisis
  GitHub.com, HTTPS, puis la connexion par le navigateur. Ensuite `git push` fonctionne sans mot de passe.
- **Python 3.12** : `python3.12 --version` (Windows : `py -0p`). Sinon, installe-le depuis python.org.
- **VS Code** et ton assistant IA, Claude Code ou Cline (voir `START-HERE.md`).

### 3.3 Copier le projet sur ton ordinateur

Choisis un dossier simple, par exemple `Documents`. Évite un dossier qui se trouve déjà dans un autre projet, ou
qui est synchronisé (iCloud Drive, OneDrive, Dropbox) : la synchronisation peut abîmer le dossier `.git`.

```bash
cd ~/Documents
git clone https://github.com/windu1812/M-M-s-FAC.git
cd M-M-s-FAC
```

Dans VS Code, fais *File → Open Folder…* et choisis `M-M-s-FAC`. Puis ouvre un terminal avec
*Terminal → New Terminal* : il est déjà placé dans le dossier du projet. Toutes les commandes de ce guide partent
de là, sauf indication contraire.

Les fichiers qui commencent par un point (`.claude`, `.gitignore`) sont cachés dans le Finder
(`Cmd + Shift + .` pour les voir), mais visibles dans VS Code. Ne les supprime pas.

### 3.4 Où sont les choses

Les fichiers marqués `*` n'existent pas encore : c'est ta tranche qui les crée.

```text
M-M-s-FAC/
├── app/                        l'application : tout le code est ici
│   ├── streamlit_app.py        la page (Marc)
│   ├── creditlens/             les modules Python
│   │   ├── data/               données SEC EDGAR (Arthur)
│   │   ├── ratios.py *         ratios (Coco)
│   │   ├── flags.py *          drapeaux (Maiwenn)
│   │   ├── display.py *        valeurs prêtes à afficher : arrondis, « not available » (Marc)
│   │   ├── charts.py *         graphiques (François)
│   │   └── export.py *         fichier Excel (François)
│   ├── config/thresholds.toml *  seuils des drapeaux (Maiwenn)
│   ├── tests/                  les tests, et fixtures/ pour les petits fichiers d'exemple
│   ├── requirements.txt        les bibliothèques Python
│   ├── .env.example            le modèle de réglages (ton .env, lui, n'est jamais commité)
│   └── README.md               installer, lancer, tester
├── docs/
│   ├── product.md              ce que fait le produit, les formules
│   ├── architecture.md         comment c'est construit, les formats entre modules
│   ├── acceptance.md           les critères « terminé », les résultats calculés à la main
│   ├── plan.md                 les tranches, les responsables, l'avancement
│   ├── guide-equipe.md         ce guide
│   └── ai-log/                 les notes IA de chaque branche
├── AGENTS.md, CLAUDE.md, .claude/, .clinerules/   règles et compétences des assistants IA
├── AI-USAGE.md                 déclaration de l'usage de l'IA (regroupée à la fin)
└── README.md                   présentation du projet
```

### 3.5 Installer l'application

Sur Mac :

```bash
cd app
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env
.venv/bin/python -m pytest
cd ..
```

Sur Windows : `py -3.12 -m venv .venv`, puis `.venv\Scripts\python` à la place de `.venv/bin/python`, et
`copy .env.example .env`. Les détails et les erreurs fréquentes sont dans `app/README.md`.

La dernière ligne des tests doit indiquer des `passed` et aucun `failed`. Ouvre ensuite `app/.env` dans VS Code et
complète `SEC_USER_AGENT=Prénom Nom prenom.nom@edhec.com`. Ce fichier reste sur ton ordinateur : ne le commite
jamais et ne le colle jamais dans un chat. Les tests n'en ont pas besoin ; seul le vrai téléchargement des données
SEC l'utilise.

## 4. Aller sur ta branche (une fois)

Ta branche existe déjà sur GitHub : Arthur l'a créée depuis ton issue. **Ne lance pas `gh issue develop`**, cela
créerait une deuxième branche.

```bash
git fetch origin
git switch 6-ratios-compute-ebitda-total-debt-net-debt-and-the-credit-ratios
git branch --show-current
```

Remplace le nom par celui de **ta** branche (tableau de la section 1). Astuce : tape `git switch 6-` puis la
touche Tab, et le terminal complète le nom. La dernière commande doit afficher ta branche.

## 5. La routine de chaque séance

### Au début

```bash
git switch <ta-branche>
git pull
git fetch origin
git merge origin/main --no-edit
```

- `git pull` récupère ce que tu as toi-même déjà poussé, depuis un autre ordinateur par exemple.
- `git merge origin/main` récupère ce que les autres ont déjà fusionné dans `main`.
- S'il affiche `CONFLICT`, va à la section 10.

### Pendant : travailler avec ton assistant IA

Dans le terminal de VS Code, à la racine du projet, lance `claude` (ou ouvre Cline, en mode Plan). Pour la
première séance, tu peux écrire par exemple :

```text
/build-feature Je suis Coco. Tranche 3 de docs/plan.md (issue #6), sur ma branche
6-ratios-compute-ebitda-total-debt-net-debt-and-the-credit-ratios.
```

L'assistant lit les règles de l'équipe (`AGENTS.md`) et les documents de `docs/`. Il propose un plan avant d'écrire
du code : lis-le, puis réponds « ok » ou pose tes questions. À la fin de chaque changement, il doit t'expliquer en
français simple chaque nouveau fichier et chaque nouvelle fonction. S'il ne le fait pas, demande-le-lui : tu devras
savoir les expliquer pendant les questions du jury.

### Avant chaque commit : les tests

```bash
cd app
.venv/bin/python -m pytest
cd ..
```

Des tests qui échouent pendant que la tranche avance, c'est normal. La tranche n'est terminée que quand tous
passent.

### À la fin : commit et push

```bash
git status
git add app/creditlens/ratios.py app/tests/test_ratios.py docs/plan.md
git commit -m "feat: compute EBITDA and total debt"
git push
```

- `git status` liste ce qui a changé : vérifie qu'il n'y a que **tes** fichiers avant le `git add`. Évite
  `git add .` sans avoir regardé.
- Le message commence par un type, puis une phrase courte en anglais, comme les commits déjà présents :
  - `feat:` pour une fonctionnalité ;
  - `fix:` pour une correction ;
  - `test:` pour des tests ;
  - `docs:` pour les documents.
  
  Exemple : `test: add the CALC1 to CALC4 known answers`.
- Fais des petits commits souvent, plutôt qu'un énorme à la fin. Fais au moins un push par séance : ton travail est
  alors sauvegardé sur GitHub.
- Tu peux aussi demander à l'assistant « propose un commit ». Il te montre le message et les fichiers, et c'est toi
  qui valides.

## 6. Ouvrir la pull request

Quand ta tranche est finie :
- tous les tests passent ;
- ta ligne de `docs/plan.md` est à jour ;
- tes notes IA sont dans `docs/ai-log/<ta-branche>.md`.

Tu peux aussi l'ouvrir plus tôt en brouillon pour montrer où tu en es.

```bash
gh pr create --base main --draft
gh pr create --base main
```

La première commande ouvre une PR en brouillon, la seconde une PR prête à relire. Tu peux aussi demander à ton
assistant « ouvre la pull request de ma tranche ».

**Titre :** par exemple « Ratios: compute the credit ratios (slice 3) ».

**Description :**
- ce qui a changé ;
- les tests lancés et leur résultat ;
- `Closes #6`, avec ton numéro d'issue : l'issue se fermera toute seule à la fusion.

Ensuite :

1. **Ajoute ton relecteur** (tableau de la section 1) : `gh pr edit --add-reviewer <son-pseudo>`, ou la case
   « Reviewers » sur la page de la PR.
2. **Le relecteur** lit l'onglet « Files changed ». Il peut récupérer la branche pour la tester :
   - il commite d'abord son propre travail ;
   - il lance `gh pr checkout <numéro>` ;
   - il peut lancer `/review-changes` dans Claude Code ;
   - il revient sur sa branche avec `git switch <sa-branche>`.

   Puis il laisse des commentaires, ou clique sur « Approve ».
3. **L'auteur corrige** sur la même branche (commit + push) : la PR se met à jour toute seule.
4. **Une fois la PR approuvée, l'auteur fusionne :**
   - clique sur **Merge pull request** ;
   - garde **Create a merge commit**. Ne choisis ni « Squash » ni « Rebase » : les autres branches contiennent déjà
     ces commits. Avec Squash ou Rebase, Git ne les reconnaîtrait plus, et les PR suivantes afficheraient des
     changements en double ;
   - clique ensuite sur **Delete branch**.

## 7. Après la fusion

```bash
git switch main
git pull
```

Ta branche est terminée. S'il faut corriger quelque chose ensuite, crée une nouvelle petite branche depuis `main`,
puis suis la même routine jusqu'à une nouvelle PR :

```bash
git switch main
git pull
git switch -c fix/ratios-negative-equity
```

## 8. Les règles d'or

1. **Jamais de commit sur `main`.** GitHub le refuse de toute façon : `main` n'accepte que des pull requests.
2. **Jamais `git push --force`, `git reset --hard` ni `git rebase`** : ces commandes peuvent effacer du travail. En
   cas de doute, demande.
3. **Jamais de `.env` dans Git.** Jamais de clé ni d'e-mail dans le code, et jamais dans un chat.
4. **Tu ne modifies que tes fichiers** (section 1). Pour un fichier partagé, voir la section 9.
5. **Dans `docs/plan.md`, seulement ta ligne** du tableau des tranches, et tes lignes du journal (*Progress log*).
6. **Tes notes IA vont dans `docs/ai-log/<ta-branche>.md`**, pas dans `AI-USAGE.md`. Maiwenn les regroupe à la fin.
7. **Les tests n'appellent jamais internet.** Ils utilisent de petits fichiers d'exemple dans `app/tests/fixtures/`.
   Fais commencer leur nom par celui de ton module (`ratios_sample.csv`, `flags_sample.csv`) pour éviter les
   collisions.
8. **Aucun chiffre inventé** : une valeur manquante s'affiche « not available ».
9. **Pas de nouvelle bibliothèque sans l'accord de l'équipe.** Toutes celles prévues (pandas, Plotly, openpyxl…)
   sont déjà dans `app/requirements.txt`.

## 9. Les fichiers partagés

| Fichier | Règle |
|---|---|
| `app/streamlit_app.py` | Fichier de Marc. François y ajoute seulement les lignes qui placent les graphiques et le bouton Excel, après en avoir parlé avec Marc. |
| `app/creditlens/display.py` | Fichier de Marc. Les graphiques et l'Excel s'en servent : s'il manque quelque chose, François demande à Marc. |
| `docs/plan.md`, `docs/acceptance.md` | Seulement ta ligne et le statut de tes critères. |
| `app/requirements.txt` | Demander à l'équipe avant. |
| `AGENTS.md`, `CLAUDE.md`, `.claude/`, `.clinerules/` | Les règles de l'équipe et des assistants : pas de modification sans l'accord de l'équipe. |
| `README.md` (racine), `AI-USAGE.md` | Maiwenn, en tranche 7. |

## 10. Résoudre un conflit

Un conflit arrive quand `git merge origin/main` trouve des lignes modifiées à la fois par toi et par quelqu'un
d'autre. Le cas le plus fréquent est `docs/plan.md` : les lignes du tableau sont voisines, et Git considère comme
un conflit deux changements sur des lignes qui se touchent, même si chacun n'a modifié que la sienne.

Git affiche :

```text
CONFLICT (content): Merge conflict in docs/plan.md
```

Le fichier contient alors des marqueurs `<<<<<<<`, `=======` et `>>>>>>>` autour des deux versions. Il faut garder la
version à jour de chaque ligne (ta ligne à toi, la ligne de l'autre à lui), puis supprimer les marqueurs. Le plus
simple est de demander à ton assistant :

```text
J'ai un conflit après git merge origin/main dans docs/plan.md. Résous-le en gardant ma ligne et celle
des autres, puis montre-moi le résultat avant de commiter.
```

Ensuite :

```bash
cd app
.venv/bin/python -m pytest
cd ..
git add docs/plan.md
git commit --no-edit
git push
```

Pour tout annuler et revenir à l'état d'avant le merge : `git merge --abort`.

## 11. Problèmes fréquents

| Ce que tu vois | Pourquoi | Que faire |
|---|---|---|
| `Permission denied` ou `403` au `git push` | Invitation pas acceptée, ou `gh auth login` pas fait | Section 3.1, puis `gh auth login` |
| `! [rejected] ... (fetch first)` | GitHub a des commits que tu n'as pas | `git pull`, puis `git push` |
| `push declined due to repository rule violations` | Tu as commité sur `main` | Ne force rien. Demande à ton assistant : « J'ai commité sur main par erreur, déplace ces commits sur ma branche <nom> sans rien perdre. » |
| `Your local changes ... would be overwritten` | Tu as des changements pas encore commités | Fais d'abord un commit (section 5), puis recommence |
| `ModuleNotFoundError` | Ce n'est pas le Python du projet | Depuis `app/`, utilise toujours `.venv/bin/python` |
| `fatal: not a git repository` | Le terminal n'est pas dans le dossier du projet | `cd ~/Documents/M-M-s-FAC`, ou l'endroit où tu as cloné le projet |
| Tu ne sais plus sur quelle branche tu es | – | `git branch --show-current` |

## 12. Aide-mémoire

```bash
# Début de séance
git switch <ta-branche>
git pull
git fetch origin
git merge origin/main --no-edit

# Tests
cd app
.venv/bin/python -m pytest
cd ..

# Enregistrer et envoyer
git status
git add <tes fichiers>
git commit -m "feat: ..."
git push

# Tranche finie
gh pr create --base main
```

---
title: Démarrer Linux MCP Server sous Windows
tags:
  - MCP
  - Windows
  - WSL
  - RHEL
---

# Démarrer Linux MCP Server sous Windows

## Architecture

- Le client MCP tourne dans WSL.
- `linux-mcp-server` tourne sous Windows.
- Le serveur utilise la configuration SSH Windows pour joindre les hôtes RHEL, y compris les alias et le jump host.
- Le client MCP rejoint le serveur Windows par HTTP sur `127.0.0.1:8765`.

> Pour tester les changements locaux, le dépôt Windows doit contenir ces changements. Ne pas lancer le paquet PyPI avec `--no-project --with linux-mcp-server` pour ce test.

## Cloner le dépôt sous Windows

Dans PowerShell, cloner le dépôt une seule fois à l’emplacement utilisé dans cette procédure :

```powershell
New-Item -ItemType Directory -Force "C:\github\mcp_servers\rhel" | Out-Null
git clone https://github.com/saq-infra/linux-mcp-server.git "C:\github\mcp_servers\rhel\linux-mcp-server"
```

Si le dépôt est déjà cloné à cet emplacement, ne relance pas `git clone`; passe directement à l’étape de démarrage. Vérifie que le clone contient la version des changements que tu veux tester avant de lancer le serveur.

## Prérequis

Dans PowerShell, vérifier que `uv` est installé :

```powershell
uv --version
```

Si nécessaire, l’installer :

```powershell
winget install --id astral-sh.uv -e
```

Vérifier que l’alias SSH Windows fonctionne :

```powershell
ssh "<nom_serveur>" "hostname; id -un"
```

Remplacer `<nom_serveur>` par un alias défini dans `C:\Users\<utilisateur>\.ssh\config` avant d’exécuter la commande.

## Préparer la policy HTTP

Dans PowerShell, créer le dossier et la policy en UTF-8 sans BOM :

```powershell
$policyDir = Join-Path $HOME ".linux-mcp-server"
New-Item -ItemType Directory -Force $policyDir | Out-Null

$policyPath = Join-Path $policyDir "policy.yaml"
$policy = 'rules: [{all_users: true, host: "sl*", tools: ["@fixed"], action: ssh_default}]'

[System.IO.File]::WriteAllText(
    $policyPath,
    $policy,
    [System.Text.UTF8Encoding]::new($false)
)

Get-Content $policyPath
```

Adapter `sl*` aux alias SSH autorisés. Cette règle s’applique à tous les appelants et autorise le groupe standard `@fixed`. Garder le serveur lié à `127.0.0.1` et ne pas exposer le endpoint au réseau sans authentification appropriée.

## Démarrer le serveur depuis le dépôt Windows

Dans la même fenêtre PowerShell, aller dans le checkout Windows :

```powershell
$repo = "C:\github\mcp_servers\rhel\linux-mcp-server"
Set-Location $repo
uv sync
```

Définir la configuration du serveur :

```powershell
$env:LINUX_MCP_TRANSPORT = "http"
$env:LINUX_MCP_HOST = "127.0.0.1"
$env:LINUX_MCP_PORT = "8765"
$env:LINUX_MCP_HOST_MODE = "remote-only"
$env:LINUX_MCP_POLICY_PATH = $policyPath
$env:LINUX_MCP_ALLOWED_LOG_PATHS = "/var/log/messages,/var/log/secure,/var/log/audit/audit.log"
```

Démarrer le serveur avec le code de ce dépôt :

```powershell
uv run --project $repo -- python -m linux_mcp_server
```

Garder cette fenêtre ouverte. Pour arrêter le serveur, utiliser `Ctrl+C`. Après toute modification du code ou de l’environnement, arrêter puis relancer le serveur.

### Vérifier le code source chargé

Cette commande doit afficher un chemin sous `C:\github\mcp_servers\rhel\linux-mcp-server\src\` :

```powershell
uv run --project $repo -- python -c "import linux_mcp_server.utils.validation as v; print(v.__file__)"
```

Pour vérifier le validateur POSIX après avoir synchronisé le correctif dans le checkout Windows :

```powershell
uv run --project $repo -- python -c "from pathlib import PurePosixPath; import linux_mcp_server.utils.validation as v; print(v.__file__); print(v.validate_path('/etc/os-release')); print(v.validate_remote_path('/etc/os-release'))"
```

La sortie attendue pour les deux appels est `/etc/os-release`. Si `validate_remote_path` n’existe pas dans le checkout ou si la validation échoue avec `Path must be absolute`, ce checkout ne contient pas le correctif requis.

## Vérifier l’écoute HTTP

Dans une deuxième fenêtre PowerShell :

```powershell
Test-NetConnection 127.0.0.1 -Port 8765
```

`TcpTestSucceeded` doit être `True`. Cela confirme que le port écoute, pas que SSH, la policy ou la lecture d’un fichier fonctionnent.

## Connecter le client MCP depuis WSL

Ajouter le endpoint une seule fois :

```bash
hermes mcp add rhel_mcp_windows --url http://127.0.0.1:8765/mcp
```

Si une question d’authentification apparaît pour cette configuration locale sans authentification, répondre `n`.

Tester la connexion et la découverte des outils :

```bash
hermes mcp test rhel_mcp_windows
```

Ce test ne valide pas à lui seul la connexion SSH vers un hôte, l’autorisation de chaque outil ni les permissions de fichiers RHEL.

## Tester l’accès distant

Le test se fait en plusieurs étapes et utilise deux environnements :

1. **PowerShell Windows** : le serveur MCP doit déjà tourner dans sa première fenêtre. Ne la ferme pas.
2. **Une deuxième fenêtre PowerShell Windows** : vérifie que SSH peut joindre RHEL.
3. **Terminal WSL** : vérifie la connexion MCP, puis demande au client MCP d’appeler les outils.

### Étape 1 : vérifier SSH depuis Windows

Dans une nouvelle fenêtre PowerShell Windows, exécuter :

```powershell
ssh "<nom_serveur>" "hostname; id -un"
```

Remplacer `<nom_serveur>` par un alias configuré dans le SSH Windows avant d’exécuter la commande. Elle doit afficher le nom de l’hôte et l’utilisateur distant. Si elle échoue, régler d’abord l’accès SSH/VPN/jump host; le client MCP n’intervient pas encore dans ce test.

### Étape 2 : vérifier le port MCP

Dans la même deuxième fenêtre PowerShell :

```powershell
Test-NetConnection 127.0.0.1 -Port 8765
```

Vérifier que `TcpTestSucceeded` vaut `True`. Cela confirme que le serveur HTTP Windows est joignable depuis Windows.

### Étape 3 : vérifier le client MCP depuis WSL

Dans un terminal WSL, exécuter :

```bash
hermes mcp test rhel_mcp_windows
```

Ce test vérifie que le client WSL peut joindre le endpoint MCP Windows et découvrir les outils. Il ne teste pas encore une commande SSH vers RHEL.

### Étape 4 : appeler un outil MCP

Dans ce même terminal WSL, démarrer le client interactif :

```bash
hermes
```

Dans la conversation Hermes, saisir ce prompt :

```text
Utilise le serveur MCP rhel_mcp_windows et appelle l’outil get_system_information pour l’hôte <nom_serveur>. Rapporte le résultat ou le message d’erreur exact.
```

Cet appel vérifie le trajet complet : client MCP WSL → HTTP local → serveur MCP Windows → SSH Windows → hôte RHEL.

### Étape 5 : tester la lecture d’un fichier distant

Dans la même conversation Hermes, saisir :

```text
Utilise le serveur MCP rhel_mcp_windows et appelle l’outil read_file avec host="<nom_serveur>" et path="/etc/os-release". Rapporte le résultat ou le message d’erreur exact.
```

`/etc/os-release` est un chemin du système RHEL distant. Si le résultat contient les informations de version de RHEL, la lecture a réussi.

### Étape 6 : tester la lecture d’un journal

Dans PowerShell, le serveur doit avoir été démarré avec `/var/log/messages` inclus dans `LINUX_MCP_ALLOWED_LOG_PATHS`. L’utilisateur SSH doit aussi avoir le droit de lecture sur ce fichier, ou le sudo ciblé doit être activé et autorisé côté RHEL.

Dans Hermes, saisir :

```text
Utilise le serveur MCP rhel_mcp_windows et appelle l’outil read_log_file avec host="<nom_serveur>", log_path="/var/log/messages" et last_lines=5. N’affiche pas le contenu du journal; indique seulement si l’appel réussit ou retourne son message d’erreur exact.
```

Interpréter les erreurs séparément :

- `Path must be absolute` : échec de validation avant l’exécution SSH; vérifier que le checkout Windows contient le correctif et redémarrer le serveur.
- `Access ... is not allowed` : le chemin n’est pas dans l’allowlist configurée au démarrage.
- `Permission denied` : le chemin a passé la validation et l’allowlist, mais la lecture distante est refusée par les permissions RHEL ou sudoers.

## Diagnostiquer les erreurs

### `Connection closed`

Vérifier que le processus PowerShell tourne toujours, puis tester le port avec `Test-NetConnection`. Vérifier aussi que le client MCP utilise l’URL `http://127.0.0.1:8765/mcp`.

### Erreur de chargement de policy

Vérifier le fichier et le chemin transmis au processus :

```powershell
$env:LINUX_MCP_POLICY_PATH
Get-Content $env:LINUX_MCP_POLICY_PATH
```

Le fichier doit commencer directement par `rules:` sans caractères BOM avant la clé. Redémarrer le serveur après une modification.

### `Authorization denied`

Vérifier que le motif `host` et le groupe `tools` de la policy correspondent à l’appel. La découverte des outils n’implique pas que chaque appel est autorisé.

### `Path must be absolute` pour un chemin comme `/etc/os-release`

Cette erreur se produit pendant la validation des paramètres, avant l’exécution SSH. Vérifier que le dépôt Windows contient la bonne version du code, inspecter le module importé, puis redémarrer le serveur.

### `Permission denied reading log file`

Le chemin a passé la validation et l’allowlist, mais l’utilisateur SSH n’a pas les droits de lecture sur la cible. Vérifier depuis PowerShell, sans afficher le contenu du fichier :

```powershell
ssh "<nom_serveur>" "id; ls -l /var/log/messages; test -r /var/log/messages && echo readable || echo not-readable"
```

Remplacer `<nom_serveur>` par l’alias SSH Windows avant d’exécuter la commande.

Ne pas confondre ce refus avec une erreur de chemin. Le sudo ciblé est un sujet séparé; il exige une configuration et une autorisation sudoers adaptées sur RHEL.

## Sécurité

- Garder `LINUX_MCP_HOST` à `127.0.0.1`.
- Ne pas exposer le endpoint HTTP sur `0.0.0.0` sans authentification documentée.
- Ne pas copier ni partager le contenu des clés privées SSH.
- Utiliser une policy limitée aux hôtes et outils nécessaires.
- Ne pas publier de contenu de journaux, qui peut contenir des données sensibles.

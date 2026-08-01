# LibrePhoneCam

Transformez votre téléphone en webcam pour Streamlabs, OBS et tout ce qui a une source navigateur, via votre propre wifi.
Aucune application à installer sur le téléphone, pas de compte, pas de cloud, gratuit et opensource.

*[English version](README.md)*

## Pourquoi

Fait pour les petits streameurs qui ne peuvent pas mettre plusieurs centaines
d'euros dans une caméra, ni payer un abonnement mensuel pour une application qui
fait la même chose. Vous avez déjà une bonne caméra : elle est dans votre poche.

## Installation

**[Téléchargez LibrePhoneCam.exe](../../releases/latest)** et lancer le programme.

> Windows va dire que l'éditeur est inconnu, car l'application n'est pas signée
> (un certificat coûte plusieurs centaines d'euros par an). Cliquez sur
> **Informations complémentaires**, puis **Exécuter quand même**.

## Utilisation

L'application s'ouvre avec tout ce qu'il faut :

1. **Scannez le QR code** avec votre téléphone, acceptez l'avertissement de
   certificat ([pourquoi ?](#lavertissement-de-certificat)), puis touchez
   **Démarrer la caméra**.
2. **Copiez la deuxième adresse** dans Streamlabs : `+` > **Navigateur**,
   taille 1920x1080.

Voilà. La caméra du téléphone est maintenant une source dans votre scène.

## Compatible avec

| | |
|---|---|
| **Téléphones** | iOS et Android |
| **Navigateurs** | Safari, Chrome, Firefox, Brave |
| **PC** | Windows, Linux |
| **Logiciels** | Streamlabs, OBS, tout ce qui a une source navigateur |

L'application est en **français et en anglais**, avec un bouton pour changer, et
dispose d'un **thème clair et sombre**.

## Comment ça marche

```
 Téléphone ────── vidéo (pair à pair) ──────►  Streamlabs
     │                                              │
     └──────► LibrePhoneCam sur votre PC ◄─────────┘
              (les présente, puis s'efface)
```

La qualité est automatique : la page demande à votre caméra ce qu'elle sait
faire et choisit le meilleur réglage transportable, jusqu'à 1080p60.

## Tout reste sur votre machine

Le programme ne se connecte à **aucun serveur externe**. Pas de compte, pas
d'inscription, pas de télémétrie, pas de relais cloud, rien qui appelle
l'extérieur. La seule chose qui tourne est un petit serveur web sur votre propre
PC.

La vidéo va directement du téléphone à Streamlabs via votre wifi. Elle ne passe
jamais par l'application, n'est jamais enregistrée, et n'atteint jamais
internet. Débranchez votre box : ça marche encore.

## L'avertissement de certificat

Les navigateurs n'autorisent la caméra qu'en https, et aucune autorité ne
délivre de certificat pour une adresse privée comme `192.168.1.10`.
L'application fabrique donc le sien. Votre téléphone ne peut pas le vérifier et
le signale.

C'est sans risque ici : le certificat est créé sur votre PC, y reste, et ne
couvre que votre réseau. Acceptez-le une fois et c'est réglé.

## En cas de souci

**La page ne charge pas sur le téléphone.** Autorisez l'application dans le
pare-feu Windows quand il le demande, et vérifiez que les deux appareils sont
sur le même wifi.

**Streamlabs/obs affiche un rectangle noir.** Clic droit sur la source, puis
**Actualiser**.

**Le flux s'arrête quand je change d'application.** Les téléphones suspendent la
caméra en arrière-plan. Gardez l'onglet au premier plan, et le téléphone branché.

## Depuis les sources

```bash
git clone https://github.com/YOUR-USERNAME/LibrePhoneCam
cd LibrePhoneCam
run.bat          # Windows, ou ./run.sh ailleurs. Installe tout et ouvre l'app.
build.bat        # construit LibrePhoneCam.exe dans dist/
```

Avec un argument, `run.bat` passe en version ligne de commande : `run.bat --help`.

```
librephonecam/   l'application et le serveur local
web/             la page du téléphone et celle de Streamlabs
tests/           lancez-les directement, sans framework
build-tools/     icône, configuration PyInstaller
```

Les contributions sont bienvenues.

## Licence

MIT

# Reverse Engineering du protocole RS485 Jacuzzi Joyonway

**Projet realise les 22-24 mars 2026**
**Materiel : Spa Joyonway avec controleur Balboa-like + PAC**

---

## 1. Contexte et objectif

Le spa est equipe d'un controleur **Joyonway** avec une carte PAC Balboa integree. Le fabricant fournit un module WiFi (192.168.1.98) qui communique via le cloud Alibaba/CoAP — aucun port local ouvert, aucune API exploitable en local.

**Objectif** : prendre le controle total du spa via Home Assistant, en interceptant et injectant des commandes sur le bus RS485 interne. A terme, pouvoir debrancher le panneau de commande physique en hiver et tout piloter depuis HA.

## 2. Materiel et connexion

### Bus RS485
- **Baudrate** : 115200 8N1
- **Connexion** : connecteur recupere d'un ancien boitier de commande (pas de modification du spa, garantie preservee)
- Le bus est partage entre le controleur, le panneau de commande, le module WiFi et la PAC

### Convertisseur RS485/WiFi : USR-W610
- **IP** : 192.168.1.11
- **Port TCP** : 8899
- **Interface web** : http://192.168.1.11 (admin/admin)
- **Mode** : Transparent Mode (CRITIQUE — le mode "Modbus TCP-RTU" bloque l'emission)
- **Config** : RS485 full-duplex (`m2m_udlx=on`)

Le W610 agit comme un pont transparent : tout ce qu'on envoie en TCP sort sur le bus RS485, et tout ce qui circule sur le bus est recu en TCP.

## 3. Decouverte du protocole

### 3.1 Premiere observation

A la connexion TCP, on recoit immediatement un flux continu de donnees : ~520 bytes/sec, soit environ 1920 trames/minute. Le bus est **tres actif** — le controleur broadcaste en permanence l'etat du systeme.

### 3.2 Structure des trames

Ce n'est **pas du Modbus**. C'est un protocole proprietaire de type Balboa, avec la structure suivante :

```
[0x7E] [length] [payload...] [CRC] [0x7E]
```

- **Delimiteur** : `0x7E` (debut et fin de trame)
- **Length** : nombre de bytes du payload + 2 (length + CRC)
- **CRC-8** : polynome `0x07`, valeur initiale `0x71`, calcule sur le payload (bytes apres length)

### 3.3 Adresses identifiees sur le bus

| Adresse | Role | Activite |
|---------|------|----------|
| `0x20` | Panneau de commande physique | Envoie des commandes A1 (consigne) et A4 (filtration) |
| `0x30` | Module WiFi Joyonway | Envoie des commandes A1, polle par le controleur |
| `0x40` | Emplacement libre | Polle regulierement, jamais de reponse |
| `0x50` | Emplacement libre | Polle regulierement, jamais de reponse |
| `0x58` | Carte principale / controleur | Broadcaste B4/B5/B6/B7/BB, envoie C0/C1/C2/C3/C5 |
| `0x61` | PAC / module puissance | Repond aux polls, trames C5 quasi vides |
| `0xF9` | Broadcast status | Prefixe des trames d'etat B4, B5, etc. |
| `0xFE` | Broadcast heartbeat | Trames periodiques |

**Observation cle** : les adresses `0x40` et `0x50` sont pollees mais ne repondent jamais. Ce sont des emplacements prevus pour des extensions (2e panneau, etc.). On peut potentiellement usurper une de ces adresses pour s'inserer "proprement" sur le bus — mais en pratique, le flood sur l'adresse `0x20` fonctionne tres bien.

## 4. Trames decodees

### 4.1 Trame B4 — Etat principal (broadcast)

**Identifiant** : `F9 BF B4`
**Taille** : 26 bytes (length = 0x1A)
**Frequence** : ~2 fois par seconde

C'est la trame la plus importante. Elle contient l'etat complet du spa.

```
7E 1A F9 BF B4 [b5..b25] 7E
```

| Byte (index payload) | Contenu | Encodage |
|----------------------|---------|----------|
| 9 | **Temperature eau** | Entier en °F (ex: 99 = 37.2°C) |
| 12 | **Etat pompes** | bit2 (0x04) = pompe 1, bit4 (0x10) = pompe 2 |
| 14 | **Flags chauffage** | 0x21 = idle, 0x20 = PAC seule, 0x35 = PAC + boiler |
| 16 | **Consigne temperature** | Entier en °F (ex: 68 = 20°C) |
| 17 | **Mode + Lumiere** | bit7-1: 0x90=normal, 0x10=programme. bit0: lumiere (1=allumee) |
| 19 | **Etat equipements** | Miroir pompes avec offset +1 |
| 20 | **Flag programme** | 0x30 = normal, 0x10 = programme actif |
| 21 | **Temperature sortie PAC** | Entier en °F (monte de ~2°C au-dessus de l'eau quand PAC active) |
| 25 | Checksum | CRC-8 |

**Limitation importante** : les temperatures sont en entier °F, soit une resolution de ~0.56°C. La valeur ne change que lorsqu'un seuil de degre Fahrenheit est franchi, ce qui donne l'impression de mises a jour irregulières.

### 4.2 Trame B5 — Programmes et filtration (broadcast)

**Identifiant** : `F9 BF B5`
**Taille** : 26 bytes
**Frequence** : ~1 fois par seconde

```
7E 1A F9 BF B5 [b5..b25] 7E
```

| Byte | Contenu | Encodage |
|------|---------|----------|
| 7-16 | Parametres fixes/usine | Jamais change, role inconnu |
| 17 | Plage 1 : flag + heure debut | `0xC0 \| heure` si active, `0x00 \| heure` si inactive |
| 18 | Plage 1 : minutes debut | 0-59 |
| 19 | Plage 1 : heure fin | 0-23 |
| 20 | Plage 1 : minutes fin | 0-59 |
| 21 | Plage 2 : flag + heure debut | `0x40 \| heure` si active, `0x00 \| heure` si inactive |
| 22 | Plage 2 : minutes debut | 0-59 |
| 23 | Plage 2 : heure fin | 0-23 |
| 24 | Plage 2 : minutes fin | 0-59 |
| 25 | Checksum | CRC-8 |

**Decodage des flags d'activation** :
- Plage 1 : bits 7-6 du byte 17. `0xC0` (bits 7+6) = active, `0x00` = inactive
- Plage 2 : bit 6 du byte 21. `0x40` = active, `0x00` = inactive
- L'heure de debut est encodee dans les 6 bits bas (masque `0x3F`)

Ce decodage a ete confirme par une serie de captures avec differents horaires :
- 02:00-22:30 → byte 17 = 0xC2 (0xC0 | 2)
- 03:01-23:31 → byte 17 = 0xC3 (0xC0 | 3)
- 10:15-18:45 → byte 17 = 0xCA (0xC0 | 10)

### 4.3 Autres trames identifiees (non decodees en detail)

| Trame | Description |
|-------|-------------|
| `F9 BF B6` | Horloge / compteurs |
| `F9 BF B7` | Horodatage (date/heure) |
| `F9 BF BB` | Etat LEDs / affichage du panneau |
| `58 BF C0/C1/C2/C3/C5` | Trames controleur (polling, valeurs analogiques) |
| `30 BF A1` | Commandes du module WiFi |
| `61 BF C5` | Reponse PAC aux polls (quasi toujours zeros) |

La trame **58 BF C2** est particulierement interessante : elle contient des valeurs analogiques qui varient avec la puissance de chauffage. Plusieurs paires de bytes evoluent en fonction du temps quand le chauffage est actif, potentiellement des mesures de courant, tension ou temperature internes. Non decode en detail.

## 5. Ecriture de commandes

### 5.1 Methode : spoof du panneau de commande

On usurpe l'adresse `0x20` (panneau de commande) pour envoyer des commandes au controleur. La methode est de type **"fire and forget"** en flood :

1. Ouvrir une connexion TCP vers le W610
2. Envoyer la trame de commande en boucle toutes les ~50ms
3. Continuer pendant 10 secondes
4. Le controleur accepte la commande apres quelques secondes d'envoi continu

**Pourquoi le flood ?** Le bus est partage et le controleur polle les peripheriques en round-robin. Il faut que notre commande soit presente au bon moment du cycle de polling. 10 secondes de flood garantissent plusieurs cycles complets.

**Pas besoin de repondre aux polls** du controleur. Il accepte les trames "spontanees" sur l'adresse 0x20.

### 5.2 Commande A1 — Changement de consigne

**Format** :
```
7E 12 20 BF A1 01 20 00 A1 00 00 80 80 02 04 [0xFF-temp_f] [temp_f] 00 [CRC] 7E
```

- `20` = adresse source (panneau)
- `BF A1` = type commande (consigne)
- Bytes 11-12 = `02 04` : **bidirectionnel** (monte ET descend)
- Bytes 11-12 = `00 00` : ne fonctionne que pour MONTER (ancien format, ne pas utiliser)
- `[0xFF-temp_f]` = complement de la temperature (verification)
- `[temp_f]` = consigne en °F

**Plage** : 11-39°C (52-102°F), limites imposees par le controleur.

**Cas particulier du mode programme** : si le spa est en mode "programme" (B4 byte 17 = 0x10), il faut d'abord envoyer une consigne de 50°F (10°C, hors plage) pour forcer le retour en mode normal, puis envoyer la consigne souhaitee.

### 5.3 Commande A4 — Configuration filtration

**Format** :
```
7E 12 20 BF A4 01 20 00 A1 [flag] [p1_sh p1_sm p1_eh p1_em] [p2_sh p2_sm p2_eh p2_em] [CRC] 7E
```

**Flags** :

| Flag | Action |
|------|--------|
| `0x22` | Activer + modifier plage 1 |
| `0x12` | Desactiver plage 1 |
| `0x88` | Activer + modifier plage 2 |
| `0x48` | Desactiver plage 2 |

**Structure des flags** :
- Plage 1 : `0x20` (active) | `0x10` (concernee) + `0x02` = `0x22` pour activer
- Plage 1 : `0x10` (concernee) + `0x02` = `0x12` pour desactiver
- Plage 2 : `0x80` (active) | `0x40` (concernee) + `0x08` = `0x88` pour activer
- Plage 2 : `0x40` (concernee) + `0x08` = `0x48` pour desactiver

Les bytes de la plage **non concernee** doivent etre a `0x00`.

**Comportement observe** : lors de l'envoi d'une commande A4, le controleur passe brievement en mode "programme" (B4 byte 17 = 0x10) pendant l'application, puis revient automatiquement en mode normal (0x90).

### 5.4 Commande A1 — Pompes (jets) — DECODE (24 mars 2026)

Les pompes utilisent la meme commande `A1` que la consigne, mais avec un format different (bytes 7-8 au lieu de 13-14).

**Format** :
```
7E 12 20 BF A1 01 20 00 A1 [mask] [state] 00 00 00 00 00 00 00 [CRC] 7E
```

| Commande | mask | state | Effet |
|----------|------|-------|-------|
| Pompe 1 ON | `0x04` | `0x04` | Active la pompe 1 (jets) |
| Pompe 1 OFF | `0x04` | `0x00` | Arrete la pompe 1 |
| Pompe 2 ON | `0x10` | `0x10` | Active la pompe 2 (jets) |
| Pompe 2 OFF | `0x10` | `0x00` | Arrete la pompe 2 |

- `mask` (byte 8) = identifiant de la pompe (memes bits que B4 byte 12)
- `state` (byte 9) = meme valeur que mask pour ON, `0x00` pour OFF
- Les bytes 10-15 restent a `0x00` (contrairement a la commande consigne)

Le controleur differencie la commande consigne de la commande pompe grace aux bytes qui suivent : la consigne a `0x80 0x80 0x02 0x04` aux positions 10-13, tandis que la pompe a `0x00` partout.

### 5.5 Commande AE — Lumiere — DECODE (24 mars 2026)

La lumiere utilise une commande distincte `AE` (pas `A1`).

**Format** :
```
7E 0E 20 BF AE 00 [state] 01 00 00 00 00 00 00 [CRC] 7E
```

| Commande | state (byte 5) | Effet |
|----------|-----------------|-------|
| Lumiere ON | `0x11` | Allume la lumiere |
| Lumiere OFF | `0x00` | Eteint la lumiere |

L'etat de la lumiere est reflete dans B4 byte 17 (mode), bit0 :
- `0x90` = normal, lumiere eteinte
- `0x91` = normal, lumiere allumee
- `0x10` = programme, lumiere eteinte
- `0x11` = programme, lumiere allumee

## 6. Systeme de chauffage

Le spa dispose de **deux sources de chauffage** :

| Source | Puissance | Detection |
|--------|-----------|-----------|
| PAC (pompe a chaleur) | ~1200W | B4 byte 14 != 0x21, byte 21 monte |
| Boiler resistif | ~4000W | B4 byte 14 = 0x35 |
| **Total** | **~4800W** | Via Shelly (sensor externe) |

### Detection dans B4 byte 14

| Valeur | Signification |
|--------|--------------|
| `0x21` (0010 0001) | Idle — aucun chauffage |
| `0x20` (0010 0000) | PAC seule active |
| `0x35` (0011 0101) | PAC + boiler actifs |

Detection simplifiee : `chauffage_actif = (byte14 != 0x21)`

### Temperature sortie PAC (B4 byte 21)

Quand la PAC est active, byte 21 monte d'environ 2°C au-dessus de la temperature eau. C'est la temperature de l'eau en sortie de l'echangeur de la PAC.

### Communication PAC sur le bus

La PAC a l'adresse `0x61` sur le bus. Elle est pollee regulierement par le controleur, mais ses trames de reponse (`61 BF C5`) sont **quasi entierement a zeros**, que la PAC soit en marche ou non. La PAC ne communique pas son etat de fonctionnement via le bus RS485 — le controleur la pilote probablement par un simple relais.

La trame `58 BF C2` du controleur contient des valeurs analogiques qui varient significativement pendant le chauffage (probablement des mesures internes de courant/temperature), mais leur decodage precis n'a pas ete realise.

## 7. Ce qui n'est PAS sur le bus RS485

- **Puissance electrique** : mesuree independamment par le module WiFi Joyonway (pas accessible localement). Le suivi de puissance dans HA utilise un Shelly externe.
- **Pompe de recirculation** : geree en interne par le controleur (relais 230V direct). Aucun etat dans les trames B4. Detectable indirectement via la consommation (~180W sur le Shelly).
- **Commandes pompes/jets** : DECODE le 24 mars 2026 — commande A1 avec mask/state
- **Commande lumiere** : DECODE le 24 mars 2026 — commande AE

## 8. Integration Home Assistant (HACS Custom Component)

### 8.1 Architecture

```
[Bus RS485] <---> [USR-W610] <--WiFi--> [HA DataUpdateCoordinator]
                  192.168.1.11:8899      (custom_components/joyonway/)
```

- **Lecture** : `rs485.py` se connecte au W610, lit 3 secondes, parse B4+B5
- **Ecriture** : commandes envoyees en flood via le coordinator (consigne, pompes, lumiere, filtration)
- Le coordinator interroge le bus toutes les 30 secondes
- Configuration 100% UI — aucun YAML necessaire

### 8.2 Entites creees

**Sensors (lecture du bus)** :
| Entite | Description |
|--------|-------------|
| `sensor.joyonway_spa_water_temperature` | Temperature eau en °C |
| `sensor.joyonway_spa_heat_pump_output` | Temperature sortie PAC en °C |
| `sensor.joyonway_spa_setpoint` | Consigne reelle lue du bus en °C |
| `sensor.joyonway_spa_mode` | normal / programme |
| `sensor.joyonway_spa_heating_mode` | off / pac / pac_boiler |
| `sensor.joyonway_spa_filtration_1` | active/inactive + attributs start/end |
| `sensor.joyonway_spa_filtration_2` | active/inactive + attributs start/end |

**Binary sensors** :
| Entite | Description |
|--------|-------------|
| `binary_sensor.joyonway_spa_pump_1` | Pompe 1 (jets) on/off |
| `binary_sensor.joyonway_spa_pump_2` | Pompe 2 (jets) on/off |
| `binary_sensor.joyonway_spa_heating` | Chauffage actif on/off |
| `binary_sensor.joyonway_spa_light` | Lumiere on/off |
| `binary_sensor.joyonway_spa_connectivity` | Connectivite W610 |

**Controls** :
| Entite | Description |
|--------|-------------|
| `switch.joyonway_spa_pump_1` | Toggle pompe 1 via RS485 |
| `switch.joyonway_spa_pump_2` | Toggle pompe 2 via RS485 |
| `switch.joyonway_spa_light` | Toggle lumiere via RS485 |
| `switch.joyonway_spa_filtration_1` | Toggle plage filtration 1 via RS485 |
| `switch.joyonway_spa_filtration_2` | Toggle plage filtration 2 via RS485 |
| `select.joyonway_spa_programme` | Selection programme (Manuel / Hors gel / Pret a plonger / En repos) |
| `number.joyonway_spa_setpoint_target` | Consigne cible 11-39°C (envoie RS485 au changement) |
| `number.joyonway_spa_session_duration` | Duree session "Je plonge" (1-12h) |
| `button.joyonway_spa_dive_in` | Lance une session (38°C + timer retour En repos) |
| `button.joyonway_spa_cancel_session` | Annule la session en cours |

### 8.3 Logique integree au coordinator

Toute la logique est geree par le `DataUpdateCoordinator`, sans automations YAML :

- **Application programme** : quand l'utilisateur change le `select`, le coordinator envoie automatiquement la consigne + la configuration filtration via RS485
- **Detection mode manuel** : si les reglages divergent du programme actif (changement depuis le panneau physique ou manuellement), bascule automatiquement sur "Manuel"
- **Synchronisation consigne** : si la consigne change sur le panneau physique, le slider se met a jour
- **Session "Je plonge"** : active "Pret a plonger" (38°C) et programme un timer interne. A expiration, retour automatique sur "En repos" (30°C) + notification
- **Persistance** : les entites programme, consigne et duree session sont restaurees au redemarrage de HA (RestoreEntity)

### 8.4 Programmes predéfinis

| Programme | Consigne | Plage 1 | Plage 2 |
|-----------|----------|---------|---------|
| Manuel | (pas de changement) | (pas de changement) | (pas de changement) |
| Hors gel (11°C, 24/7) | 11°C | 00:00-23:59 (24h/24) | OFF |
| Pret a plonger (38°C, 10h-23h) | 38°C | 10:00-23:00 | OFF |
| En repos (30°C, 12h-20h) | 30°C | 12:00-20:00 | OFF |

### 8.5 Fichiers du custom component

| Fichier | Role |
|---------|------|
| `rs485.py` | Communication RS485 : lecture bus, construction trames, flood commands |
| `coordinator.py` | DataUpdateCoordinator : polling, logique programmes, timer session |
| `sensor.py` | Sensors temperature, mode, heating_mode, filtration |
| `binary_sensor.py` | Binary sensors pompes, chauffage, lumiere, connectivite |
| `switch.py` | Switches pompes, lumiere, filtration on/off |
| `select.py` | Select programme avec RestoreEntity |
| `number.py` | Number consigne cible et duree session avec RestoreEntity |
| `button.py` | Buttons "Dive In" et "Cancel Session" |
| `config_flow.py` | Config flow UI (host + port) |
| `entity.py` | Classe de base JoyonwayEntity |
| `const.py` | Constantes, definitions des programmes |

## 10. Calcul du CRC-8

```python
def crc8(data, poly=0x07, init=0x71):
    crc = init
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ poly) & 0xFF
            else:
                crc = (crc << 1) & 0xFF
    return crc
```

Le CRC est calcule sur le payload (tous les bytes entre length et CRC).

## 11. Pieges et lecons apprises

1. **Mode W610** : le mode "Modbus TCP-RTU" ne transmet PAS les donnees vers le bus RS485. Il faut absolument le mode Transparent.

2. **Bidirectionnalite de la commande consigne** : les bytes 11-12 de la commande A1 doivent etre `02 04` pour pouvoir monter ET descendre la consigne. Avec `00 00`, seule la montee fonctionne.

3. **Mode programme** : quand le spa est en mode programme, il faut d'abord envoyer une consigne hors plage (50°F) pour forcer le retour en mode normal avant d'appliquer la vraie consigne.

4. **Passage temporaire en mode programme** : lors de l'envoi d'une commande A4 (filtration), le controleur passe brievement en mode "programme" (~1-2 secondes) puis revient en normal. C'est normal et ne necessite pas d'action.

5. **Resolution temperature** : les temperatures sont en entier °F (~0.56°C de resolution). Les mises a jour dans HA semblent "irregulieres" mais c'est simplement la granularite du capteur.

6. **Format input_datetime HA** : retourne "HH:MM:SS" alors que les scripts attendent "HH:MM". Necessaire de tronquer avec `[0:5]` dans les shell_commands et les conditions d'automation.

7. **Detection chauffage** : la logique initiale `not (flag_byte & 0x01)` etait incorrecte pour le cas PAC+boiler (0x35). La detection correcte est `flag_byte != 0x21`.

8. **Lumiere dans le byte mode** : le bit0 du mode_byte (B4 byte 17) encode la lumiere, pas seulement le mode. Il faut masquer avec `0xFE` pour extraire le mode et tester `& 0x01` pour la lumiere.

9. **Commandes A1 polymorphes** : la meme commande `A1` sert a la fois pour la consigne (bytes 10-13 = `80 80 02 04`) et les pompes (bytes 10-15 = `00`). Le controleur differencie les deux grace au contenu des bytes suivants.

## 12. Pistes d'evolution

- **Delestage surplus solaire** : chauffer le jacuzzi quand il y a du surplus de production solaire
- **Decodage C2** : exploiter les valeurs analogiques du controleur (puissance interne, temperatures)
- **Debrancher le panneau** : en hiver, HA pilote tout — le panneau physique devient optionnel (TOUTES les commandes sont maintenant decodees : consigne, filtration, pompes, lumiere)
- **Trames B6/B7** : decoder l'horloge interne et les compteurs du controleur

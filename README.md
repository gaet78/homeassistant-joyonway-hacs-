# Joyonway Spa RS485 — HACS Integration

> **English version below** — [Click here to jump to the English section](#english)

---

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

## Français

> **⚠️ Avertissement** : ce projet implique une connexion électrique au boîtier de contrôle de votre spa. **Coupez toujours l'alimentation** avant toute intervention. L'utilisation de ce projet se fait **à vos risques et périls** — l'auteur ne saurait être tenu responsable de tout dommage matériel, perte de garantie ou blessure. Si vous n'êtes pas à l'aise avec le câblage électrique, faites appel à un professionnel.

Intégration Home Assistant (HACS) pour le contrôle local complet d'un **spa Joyonway (type Balboa)** via RS485, sans dépendance cloud. Configuration entièrement via l'interface HA — aucun YAML nécessaire.

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/dashboard.png" alt="Dashboard Home Assistant" width="800">
  <br><em>Dashboard Spa dans Home Assistant</em>
</p>

### Fonctionnalités

- **Capteurs** : température eau, consigne, température sortie PAC, mode chauffage, programmes de filtration (2 créneaux), connectivité
- **Capteurs binaires** : pompe 1, pompe 2, chauffage, lumière
- **Interrupteurs** : pompe 1, pompe 2, lumière, filtration (on/off)
- **Consigne température** : slider 11-39°C, envoi direct sur le bus RS485
- **Programmes prédéfinis** : Hors gel, Prêt à plonger, En repos — appliquent consigne + filtration en un clic
- **Programmes personnalisés** : créez vos propres programmes via l'interface de configuration
- **Session "Je plonge"** : monte à 38°C et repasse en "En repos" après une durée configurable (1-12h)
- **Config flow UI** : ajoutez votre spa depuis l'interface HA, sans YAML

### Matériel requis

| Composant | Détails |
|-----------|---------|
| **Spa** | Joyonway avec contrôleur type Balboa |
| **Bridge RS485/WiFi** | [USR-W610](https://www.usr.cn/en/W610) (~45€ sur Amazon en 2026) ou bridge TCP-RS485 transparent similaire |
| **Connexion** | Bus RS485 (port panneau de contrôle supplémentaire ou port module WiFi inutilisé) |

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/usr-w610.jpg" alt="USR-W610 RS485/WiFi Bridge" width="400">
  <br><em>Bridge RS485/WiFi USR-W610</em>
</p>

### Câblage RS485

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/rs485-connector.jpg" alt="Connecteur RS485 du spa" width="400">
  <br><em>Connecteur 4 broches du bus RS485 (port écran de contrôle)</em>
</p>

Le câble contient 4 fils :

| Fil | Fonction | Branchement W610 |
|-----|----------|-----------------|
| **Orange** | RS485 Data- | Port **B** |
| **Marron** | RS485 Data+ | Port **A** |
| Rouge | +12V | Non utilisé |
| Noir | Ground | Non utilisé |

**Où se connecter :**
- **Option 1 (recommandée)** : le bus RS485 dispose d'un connecteur libre (probablement prévu pour le module WiFi). Si vous avez un ancien panneau de contrôle HS, vous pouvez récupérer son connecteur — aucun câble à couper, garantie préservée. Ce type de connecteur 4 broches est malheureusement difficile à trouver dans le commerce ; si vous n'en avez pas, il faudra peut-être couper et souder les fils directement.
- **Option 2** : sur la carte mère du contrôleur, il y a deux connecteurs **CN23** et **CN24**. Le panneau de contrôle est branché sur l'un des deux, l'autre est libre. Le connecteur 4 broches utilisé ici est plus courant et plus facile à trouver.

**Câble :** du simple câble réseau (Ethernet) fonctionne très bien pour relier le connecteur du spa au W610. Testé avec 10 mètres sans problème. Cela permet de placer le W610 **hors de la zone spa**, à l'abri de l'humidité.

### Configuration du USR-W610

**C'est critique** — le W610 doit être en **Mode Transparent**. Le mode Modbus TCP↔RTU bloque la transmission.

| Paramètre | Valeur |
|-----------|--------|
| Mode | Transparent |
| Port TCP | 8899 |
| Protocole | TCP Server |
| RS485 | 115200 8N1 |
| Full duplex | `m2m_udlx=on` |

### Installation

#### HACS (recommandé)

1. Ouvrez HACS dans Home Assistant
2. Menu 3 points → **Dépôts personnalisés**
3. Ajoutez l'URL de ce dépôt avec la catégorie **Intégration**
4. Recherchez "Joyonway" et installez
5. Redémarrez Home Assistant
6. **Paramètres → Appareils et services → Ajouter une intégration → Joyonway Spa RS485**
7. Entrez l'adresse IP et le port de votre W610

#### Manuelle

1. Copiez le dossier `custom_components/joyonway` dans le dossier `custom_components/` de votre Home Assistant
2. Redémarrez Home Assistant
3. **Paramètres → Appareils et services → Ajouter une intégration → Joyonway Spa RS485**

### Entités créées

Toutes les entités sont regroupées sous un appareil unique **"Joyonway Spa"**.

#### Capteurs (lecture du bus RS485)
| Entité | Description |
|--------|-------------|
| Water Temperature | Température de l'eau (°C) |
| Setpoint | Consigne active (°C) |
| Heat Pump Output | Température sortie PAC (°C) |
| Mode | normal / programme |
| Heating Mode | off / pac / pac_boiler |
| Filtration 1 | Créneau 1 (active/inactive + horaires en attributs) |
| Filtration 2 | Créneau 2 (active/inactive + horaires en attributs) |

#### Capteurs binaires
| Entité | Description |
|--------|-------------|
| Pump 1 | État pompe jets 1 |
| Pump 2 | État pompe jets 2 |
| Heating | Chauffage actif (PAC et/ou résistance) |
| Light | État lumière |
| Connectivity | Connectivité avec le bridge W610 |

#### Interrupteurs (écriture sur le bus RS485)
| Entité | Description |
|--------|-------------|
| Pump 1 | Basculer pompe jets 1 |
| Pump 2 | Basculer pompe jets 2 |
| Light | Basculer lumière |
| Filtration | Activer/désactiver la filtration (conserve les horaires) |

#### Contrôles
| Entité | Type | Description |
|--------|------|-------------|
| Programme | Select | Sélection du programme actif (prédéfinis + personnalisés) |
| Consigne | Number | Slider consigne température (11-39°C) |
| Durée session | Number | Durée de la session "Je plonge" (1-12h) |
| Je plonge ! | Button | Lance une session : chauffe à 38°C, repasse en "En repos" après la durée configurée |
| Annuler session | Button | Annule la session en cours et repasse en "En repos" |

### Gestion des programmes

#### Programmes par défaut

L'intégration est livrée avec 3 programmes prêts à l'emploi + le mode Manuel :

| Programme | Consigne | Filtration |
|-----------|----------|------------|
| Manuel | — | — |
| Hors gel (11°C, 24/7) | 11°C | 00:00 - 23:59 |
| Prêt à plonger (38°C, 10h-23h) | 38°C | 10:00 - 23:00 |
| En repos (30°C, 12h-20h) | 30°C | 12:00 - 20:00 |

Quand un programme est sélectionné, la consigne et la filtration sont envoyées automatiquement au spa via RS485. Si la consigne ou la filtration est modifiée manuellement (depuis HA ou le panneau physique du spa), le programme repasse automatiquement en **Manuel**.

**Tous les programmes sont modifiables et supprimables** — seul "Manuel" reste toujours présent. Si vous supprimez tous les programmes, vous pouvez les recréer à votre convenance.

#### Gérer les programmes

Depuis l'interface HA :

1. Allez dans **Paramètres → Appareils et services**
2. Trouvez **Joyonway Spa RS485** dans la liste
3. Cliquez sur l'icône **roue dentée** (⚙️) à côté de l'intégration
4. Choisissez une action :
   - **Ajouter un programme** : nom, consigne température, et horaires de filtration
   - **Modifier un programme** : sélectionnez le programme puis modifiez les paramètres
   - **Supprimer un programme** : sélectionnez le programme à retirer

Le nom du programme est automatiquement formaté avec un résumé : `Mon programme (35°C, 14h-22h)`.

### Fonctionnement

#### Architecture du bus RS485

Le bus RS485 du spa fonctionne en mode **maître/esclave**. Le contrôleur (maître) broadcast en permanence des trames d'état (~2x/sec). Le panneau de contrôle physique (esclave à l'adresse `0x20`) envoie des commandes quand l'utilisateur appuie sur un bouton.

L'intégration **usurpe l'adresse du panneau de contrôle** (`0x20`) pour envoyer des commandes. Comme le protocole ne prévoit pas d'accusé de réception, les commandes sont envoyées en mode **flood** (répétition toutes les 50ms) pour garantir que le contrôleur les reçoive.

#### Lecture et écriture

- **Lecture** : connexion TCP au W610, capture de 1 seconde de trafic bus, analyse des trames broadcast B4 (statut) et B5 (filtration)
- **Écriture** : flood de la trame de commande pendant 1 à 2 secondes selon le type (pompe/lumière : 1s, consigne/filtration : 2s)
- **Polling** : rafraîchissement automatique toutes les 30 secondes

#### Latence et temps de réponse

Du fait de cette architecture maître/esclave sans accusé de réception, **les commandes ne sont pas instantanées** :

| Action | Durée approximative | Explication |
|--------|-------------------|-------------|
| Pompe ou lumière | ~3 secondes | 1s de flood + 1s de lecture pour confirmer |
| Changement de consigne | ~5 secondes | 2s de flood + 1s de lecture |
| Application d'un programme | ~10 secondes | Envoi séquentiel de la filtration (2s) puis de la consigne (2s) + lectures |

Pendant l'application d'un programme, la synchronisation avec le bus RS485 est **suspendue pendant 30 secondes** pour éviter que l'ancienne valeur de consigne (encore sur le bus) n'écrase la nouvelle avant qu'elle soit prise en compte par le contrôleur.

> **Note** : ces durées ont été optimisées par des tests de latence. Le bus broadcast ~2 trames/sec, et 10 trames de flood (0.5s) suffisent pour que le contrôleur reçoive la commande. Les valeurs actuelles incluent une marge de sécurité.

> **Résolution température** : le contrôleur du spa utilise les **Fahrenheit en interne** avec une précision entière. Les mises à jour en Celsius apparaissent par paliers de ~0.56°C — c'est un comportement normal.

> **Pompe de recirculation** : elle ne peut pas être pilotée individuellement via le bus RS485. Elle est contrôlée uniquement par les programmes de filtration.

### Résumé du protocole

| Trame | Direction | Contenu |
|-------|-----------|---------|
| `F9 BF B4` | Broadcast (2x/sec) | Temp eau, consigne, pompes, chauffage, mode, temp PAC |
| `F9 BF B5` | Broadcast (1x/sec) | Programmes filtration (2 créneaux) |
| `20 BF A1` | Panneau → Contrôleur | Consigne OU on/off pompe |
| `20 BF A4` | Panneau → Contrôleur | Programme filtration |
| `20 BF AE` | Panneau → Contrôleur | On/off lumière |

Pour la documentation complète du protocole, voir [docs/protocol.md](docs/protocol.md)

### Compatibilité

Testé avec :
- Spa Joyonway avec boîtier **P69B133 3kW** ([fiche produit](https://www.boospa.net/fr/boitier-de-controle-p69b133-3kw-joyonway.html)) et pompe à chaleur intégrée
- Bridge RS485/WiFi USR-W610
- Home Assistant 2026.3+

Devrait fonctionner avec d'autres spas utilisant le même protocole propriétaire Joyonway/Balboa (délimiteur 0x7E, même structure de trame). Le protocole n'est **PAS** du Balboa standard — c'est une variante propriétaire.

### Cohabitation avec le panneau physique

L'intégration **coexiste** avec le panneau de contrôle physique du spa — les deux peuvent fonctionner en parallèle sans conflit. Si vous changez la consigne ou activez une pompe depuis le panneau physique, HA détectera le changement au prochain cycle de lecture (30 secondes max). De même, les commandes envoyées depuis HA sont visibles immédiatement sur le panneau.

> **Note** : si un programme est actif dans HA et que vous modifiez la consigne depuis le panneau physique, le programme repassera automatiquement en **Manuel** pour refléter le changement.

### Limitations connues

- **Heating mode 0x21** : la valeur `0x21` (PAC seule) apparaît aussi lors d'une simple recirculation (~176W). L'intégration ne peut pas distinguer les deux cas par le bus RS485 seul. Pour différencier, vous pouvez croiser avec un capteur de puissance externe (ex: Shelly Plug sur l'alimentation du spa — >500W = PAC active).
- **Pompe de recirculation** : pas d'état individuel sur le bus RS485, elle est pilotée uniquement par les programmes de filtration.
- **Puissance / consommation** : aucune donnée de puissance n'est disponible sur le bus RS485. L'app Joyonway mesure ces valeurs via le module WiFi interne, indépendamment.

### Exemple d'automatisation : alerte gel

Voici un exemple d'automatisation pour activer automatiquement le programme "Hors gel" quand la température extérieure descend sous 2°C :

```yaml
automation:
  - alias: "Spa - Alerte gel"
    trigger:
      - platform: numeric_state
        entity_id: sensor.temperature_exterieure  # votre capteur
        below: 2
        for: "00:30:00"
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: select.joyonway_spa_programme
            state: "Hors gel (11°C, 24/7)"
    action:
      - service: select.select_option
        target:
          entity_id: select.joyonway_spa_programme
        data:
          option: "Hors gel (11°C, 24/7)"
      - service: notify.votre_service  # optionnel
        data:
          message: "Alerte gel ! Le spa passe en mode Hors gel."
```

### Dépannage

| Problème | Solution |
|----------|----------|
| "Cannot connect" lors de la configuration | Vérifiez l'IP/port du W610, qu'il est alimenté et sur votre réseau |
| "No RS485 data" | Vérifiez le câblage RS485 (A/B), le W610 doit être en **Mode Transparent**, 115200 baud |
| Mises à jour température irrégulières | Normal — résolution 1°F (~0.56°C), mise à jour au changement de seuil |
| Les commandes ne fonctionnent pas | Vérifiez que le W610 n'est PAS en mode Modbus TCP↔RTU |
| Le programme repasse en "Manuel" tout seul | C'est normal — si la consigne ou la filtration est modifiée (depuis HA, le panneau physique, ou une autre automatisation), le programme actif est désactivé automatiquement |
| Programmes personnalisés non visibles après mise à jour | Redémarrez Home Assistant — les options flow sont chargées au démarrage |

### Licence

MIT

---

<a name="english"></a>

## English

# Joyonway Spa RS485 — HACS Integration

> **⚠️ Disclaimer**: this project involves wiring into your spa's control box. **Always disconnect power** before any intervention. Use this project **at your own risk** — the author is not responsible for any hardware damage, warranty loss, or injury. If you are not comfortable with electrical wiring, consult a professional.

Home Assistant integration (HACS) for full local control of **Joyonway (Balboa-like) spas** via RS485, without cloud dependency. Fully configured through the HA UI — no YAML needed.

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/dashboard.png" alt="Home Assistant Dashboard" width="800">
  <br><em>Spa dashboard in Home Assistant</em>
</p>

### Features

- **Sensors**: Water temperature, setpoint, heat pump output temperature, heating mode, filtration schedules (2 slots), connectivity
- **Binary sensors**: Pump 1, Pump 2, Heating, Light status
- **Switches**: Pump 1, Pump 2, Light, Filtration (on/off control)
- **Temperature setpoint**: 11-39°C slider, sent directly to the RS485 bus
- **Built-in programmes**: Frost protection, Ready to swim, Resting — set temperature + filtration in one click
- **Custom programmes**: create your own programmes through the configuration UI
- **"Dive in" session**: heats to 38°C and auto-returns to "Resting" after a configurable duration (1-12h)
- **UI config flow**: Add your spa from the HA interface, no YAML required

### Hardware Required

| Component | Details |
|-----------|---------|
| **Spa** | Joyonway with Balboa-like controller |
| **RS485/WiFi bridge** | [USR-W610](https://www.usr.cn/en/W610) (~€45 on Amazon in 2026) or similar transparent TCP-to-RS485 bridge |
| **Connection** | RS485 bus connector (from spare control panel port or unused WiFi module port) |

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/usr-w610.jpg" alt="USR-W610 RS485/WiFi Bridge" width="400">
  <br><em>USR-W610 RS485/WiFi Bridge</em>
</p>

### RS485 Wiring

<p align="center">
  <img src="https://raw.githubusercontent.com/gaet78/homeassistant-joyonway-hacs-/main/images/rs485-connector.jpg" alt="Spa RS485 connector" width="400">
  <br><em>4-pin RS485 bus connector (control panel port)</em>
</p>

The cable has 4 wires:

| Wire | Function | W610 Connection |
|------|----------|----------------|
| **Orange** | RS485 Data- | Port **B** |
| **Brown** | RS485 Data+ | Port **A** |
| Red | +12V | Not used |
| Black | Ground | Not used |

**Where to connect:**
- **Option 1 (recommended)**: the RS485 bus has a spare connector (likely intended for the WiFi module). If you have an old or faulty control panel, you can salvage its connector — no cutting required, warranty preserved. This specific 4-pin connector is unfortunately hard to find online; if you don't have a spare, you may need to cut and solder the wires directly.
- **Option 2**: on the controller motherboard, there are two connectors **CN23** and **CN24**. The control panel is plugged into one of them, the other is free. The 4-pin connector used here is more common and easier to source.

**Cable:** standard Ethernet cable works perfectly to connect the spa connector to the W610. Tested with 10 meters without any issue. This allows placing the W610 **outside the spa area**, away from moisture.

### USR-W610 Configuration

**This is critical** — the W610 must be in **Transparent Mode**. Modbus TCP↔RTU mode blocks transmission.

| Setting | Value |
|---------|-------|
| Mode | Transparent |
| TCP Port | 8899 |
| Protocol | TCP Server |
| RS485 | 115200 8N1 |
| Full duplex | `m2m_udlx=on` |

### Installation

#### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the 3 dots menu → **Custom repositories**
3. Add this repository URL with category **Integration**
4. Search for "Joyonway" and install
5. Restart Home Assistant
6. **Settings → Devices & Services → Add Integration → Joyonway Spa RS485**
7. Enter the IP address and port of your W610

#### Manual

1. Copy the `custom_components/joyonway` folder to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. **Settings → Devices & Services → Add Integration → Joyonway Spa RS485**

### Entities Created

All entities are grouped under a single **"Joyonway Spa"** device.

#### Sensors (read from RS485 bus)
| Entity | Description |
|--------|-------------|
| Water Temperature | Current water temperature (°C) |
| Setpoint | Active setpoint (°C) |
| Heat Pump Output | Heat pump output water temperature (°C) |
| Mode | normal / programme |
| Heating Mode | off / pac / pac_boiler |
| Filtration 1 | Schedule slot 1 (active/inactive + times in attributes) |
| Filtration 2 | Schedule slot 2 (active/inactive + times in attributes) |

#### Binary Sensors
| Entity | Description |
|--------|-------------|
| Pump 1 | Jet pump 1 status |
| Pump 2 | Jet pump 2 status |
| Heating | Heating active (heat pump and/or electric heater) |
| Light | Light status |
| Connectivity | Connection status with the W610 bridge |

#### Switches (write to RS485 bus)
| Entity | Description |
|--------|-------------|
| Pump 1 | Toggle jet pump 1 |
| Pump 2 | Toggle jet pump 2 |
| Light | Toggle light |
| Filtration | Toggle filtration on/off (preserves current schedule times) |

#### Controls
| Entity | Type | Description |
|--------|------|-------------|
| Programme | Select | Active programme selection (built-in + custom) |
| Setpoint | Number | Temperature setpoint slider (11-39°C) |
| Session Duration | Number | "Dive in" session duration (1-12h) |
| Dive in! | Button | Start a session: heats to 38°C, returns to "Resting" after the configured duration |
| Cancel Session | Button | Cancel the current session and return to "Resting" |

### Programme Management

#### Default Programmes

The integration ships with 3 ready-to-use programmes + Manual mode:

| Programme | Setpoint | Filtration |
|-----------|----------|------------|
| Manuel (Manual) | — | — |
| Hors gel / Frost protection (11°C, 24/7) | 11°C | 00:00 - 23:59 |
| Prêt à plonger / Ready to swim (38°C, 10h-23h) | 38°C | 10:00 - 23:00 |
| En repos / Resting (30°C, 12h-20h) | 30°C | 12:00 - 20:00 |

When a programme is selected, the setpoint and filtration schedule are automatically sent to the spa via RS485. If the setpoint or filtration is changed manually (from HA or the physical spa panel), the programme automatically switches back to **Manual**.

**All programmes are editable and deletable** — only "Manuel" always remains. If you delete all programmes, you can recreate them as you wish.

#### Managing Programmes

From the HA UI:

1. Go to **Settings → Devices & Services**
2. Find **Joyonway Spa RS485** in the list
3. Click the **gear icon** (⚙️) next to the integration
4. Choose an action:
   - **Add a programme**: name, target temperature, and filtration schedule
   - **Edit a programme**: select the programme then modify its settings
   - **Delete a programme**: select the programme to remove

The programme name is automatically formatted with a summary: `My programme (35°C, 2pm-10pm)`.

### How it Works

#### RS485 Bus Architecture

The spa's RS485 bus operates in **master/slave** mode. The controller (master) continuously broadcasts status frames (~2x/sec). The physical control panel (slave at address `0x20`) sends commands when the user presses a button.

The integration **spoofs the control panel address** (`0x20`) to send commands. Since the protocol has no acknowledgment mechanism, commands are sent in **flood mode** (repeated every 50ms) to ensure the controller receives them.

#### Reading and Writing

- **Reading**: connects to W610 TCP, captures 1 second of bus traffic, parses B4 (status) and B5 (filtration) broadcast frames
- **Writing**: floods the command frame for 1 to 2 seconds depending on type (pump/light: 1s, setpoint/filtration: 2s)
- **Polling**: automatic refresh every 30 seconds

#### Latency and Response Time

Due to this master/slave architecture with no acknowledgment, **commands are not instantaneous**:

| Action | Approximate duration | Explanation |
|--------|---------------------|-------------|
| Pump or light | ~3 seconds | 1s flood + 1s read cycle to confirm |
| Setpoint change | ~5 seconds | 2s flood + 1s read cycle |
| Programme application | ~10 seconds | Sequential send of filtration (2s) then setpoint (2s) + read cycles |

During programme application, RS485 bus synchronization is **suspended for 30 seconds** to prevent the old setpoint value (still on the bus) from overwriting the new one before the controller has applied it.

> **Note**: these durations have been optimized through latency testing. The bus broadcasts ~2 frames/sec, and 10 flood frames (0.5s) are enough for the controller to receive the command. Current values include a safety margin.

> **Temperature resolution**: the spa controller uses **Fahrenheit internally** with integer precision. Celsius updates appear in ~0.56°C steps — this is normal behavior.

> **Circulation pump**: it cannot be controlled individually via the RS485 bus. It is only controlled through filtration schedules.

### Protocol Summary

| Frame | Direction | Content |
|-------|-----------|---------|
| `F9 BF B4` | Broadcast (2x/sec) | Water temp, setpoint, pumps, heating, mode, HP output temp |
| `F9 BF B5` | Broadcast (1x/sec) | Filtration schedules (2 slots) |
| `20 BF A1` | Panel → Controller | Setpoint change OR pump on/off |
| `20 BF A4` | Panel → Controller | Filtration schedule change |
| `20 BF AE` | Panel → Controller | Light on/off |

For full protocol documentation, see [docs/protocol.md](docs/protocol.md)

### Compatibility

Tested with:
- Joyonway spa with **P69B133 3kW** control box ([product page](https://www.boospa.net/fr/boitier-de-controle-p69b133-3kw-joyonway.html)) with integrated heat pump
- USR-W610 RS485/WiFi bridge
- Home Assistant 2026.3+

This should work with other spas using the same Joyonway/Balboa proprietary protocol (0x7E delimiter, same frame structure). The protocol is **NOT** standard Balboa — it's a proprietary variant.

### Coexistence with the Physical Panel

The integration **coexists** with the physical control panel — both can operate in parallel without conflict. If you change the setpoint or activate a pump from the physical panel, HA will detect the change at the next read cycle (30 seconds max). Likewise, commands sent from HA are immediately visible on the panel.

> **Note**: if a programme is active in HA and you change the setpoint from the physical panel, the programme will automatically switch back to **Manual** to reflect the change.

### Known Limitations

- **Heating mode 0x21**: the value `0x21` (heat pump only) also appears during simple recirculation (~176W). The integration cannot distinguish between the two via the RS485 bus alone. To differentiate, you can cross-reference with an external power sensor (e.g., Shelly Plug on the spa power supply — >500W = heat pump active).
- **Circulation pump**: no individual status on the RS485 bus, it is only controlled through filtration schedules.
- **Power / consumption**: no power data is available on the RS485 bus. The Joyonway app measures these values via the internal WiFi module, independently.

### Automation Example: Frost Alert

Here's an example automation to automatically activate the "Frost protection" programme when the outdoor temperature drops below 2°C:

```yaml
automation:
  - alias: "Spa - Frost alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.outdoor_temperature  # your sensor
        below: 2
        for: "00:30:00"
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: select.joyonway_spa_programme
            state: "Hors gel (11°C, 24/7)"
    action:
      - service: select.select_option
        target:
          entity_id: select.joyonway_spa_programme
        data:
          option: "Hors gel (11°C, 24/7)"
      - service: notify.your_service  # optional
        data:
          message: "Frost alert! The spa switched to Frost protection mode."
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect" during setup | Check W610 IP/port, ensure it's powered and on your network |
| "No RS485 data" | Check RS485 wiring (A/B), W610 must be in **Transparent Mode**, 115200 baud |
| Temperature updates seem irregular | Normal — resolution is 1°F (~0.56°C), updates only on threshold change |
| Commands don't work | Verify W610 is NOT in Modbus TCP↔RTU mode |
| Programme switches to "Manuel" on its own | This is expected — if the setpoint or filtration is changed (from HA, the physical panel, or another automation), the active programme is automatically deactivated |
| Custom programmes not visible after update | Restart Home Assistant — options flows are loaded at startup |

### License

MIT

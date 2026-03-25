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

> **Version simple (package YAML)** : si vous préférez une installation sans intégration custom, voir [Joyonway_control_home_assistant](https://github.com/gaet78/Joyonway_control_home_assistant)

### Fonctionnalités

- **Capteurs** : température eau, consigne, température sortie PAC, mode, programmes de filtration (2 créneaux)
- **Capteurs binaires** : pompe 1, pompe 2, chauffage, lumière
- **Interrupteurs** : pompe 1, pompe 2, lumière (on/off)
- **Consigne température** : modifiable via appels de service
- **Programmes filtration** : configurables via appels de service
- **Config flow UI** : ajoutez votre spa depuis l'interface HA, sans YAML

### Matériel requis

| Composant | Détails |
|-----------|---------|
| **Spa** | Joyonway avec contrôleur type Balboa |
| **Bridge RS485/WiFi** | [USR-W610](https://www.usr.cn/en/W610) ou bridge TCP-RS485 transparent similaire |
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
- **Option 1 (recommandée)** : utiliser le connecteur d'un écran de contrôle de rechange ou en panne — rien à couper, la garantie est préservée
- **Option 2** : si pas de PAC, utiliser le connecteur blanc **CN23** ou **CN24** sur la carte mère du contrôleur

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
| Filtration 1 | Créneau 1 (active/inactive + horaires en attributs) |
| Filtration 2 | Créneau 2 (active/inactive + horaires en attributs) |

#### Capteurs binaires
| Entité | Description |
|--------|-------------|
| Pump 1 | État pompe jets 1 |
| Pump 2 | État pompe jets 2 |
| Heating | Chauffage actif (PAC et/ou résistance) |
| Light | État lumière |

#### Interrupteurs (écriture sur le bus RS485)
| Entité | Description |
|--------|-------------|
| Pump 1 | Basculer pompe jets 1 |
| Pump 2 | Basculer pompe jets 2 |
| Light | Basculer lumière |

### Fonctionnement

L'intégration usurpe l'adresse du panneau de contrôle physique (`0x20`) sur le bus RS485 pour envoyer des commandes.

- **Lecture** : connexion TCP au W610, capture de 3 secondes de trafic bus, analyse des trames broadcast B4 (statut) et B5 (filtration)
- **Écriture** : envoi répété de la trame de commande toutes les 50ms pendant 1 à 10 secondes (selon le type)
- **Polling** : rafraîchissement automatique toutes les 30 secondes

> **Temps de réponse** : les commandes (pompes, lumière, consigne) prennent quelques secondes avant confirmation dans HA. C'est normal — l'envoi de la commande par flood dure 1 à 10 secondes, puis il faut attendre le prochain cycle de lecture (3 secondes) pour que le retour d'état soit mis à jour.

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

Pour la documentation complète du protocole, voir le dépôt compagnon : [Joyonway_control_home_assistant — docs/protocol.md](https://github.com/gaet78/Joyonway_control_home_assistant/blob/main/docs/protocol.md)

### Compatibilité

Testé avec :
- Spa Joyonway avec boîtier **P69B133 3kW** ([fiche produit](https://www.boospa.net/fr/boitier-de-controle-p69b133-3kw-joyonway.html)) et pompe à chaleur intégrée
- Bridge RS485/WiFi USR-W610
- Home Assistant 2026.3+

Devrait fonctionner avec d'autres spas utilisant le même protocole propriétaire Joyonway/Balboa (délimiteur 0x7E, même structure de trame). Le protocole n'est **PAS** du Balboa standard — c'est une variante propriétaire.

### Dépannage

| Problème | Solution |
|----------|----------|
| "Cannot connect" lors de la configuration | Vérifiez l'IP/port du W610, qu'il est alimenté et sur votre réseau |
| "No RS485 data" | Vérifiez le câblage RS485 (A/B), le W610 doit être en **Mode Transparent**, 115200 baud |
| Mises à jour température irrégulières | Normal — résolution 1°F (~0.56°C), mise à jour au changement de seuil |
| Les commandes ne fonctionnent pas | Vérifiez que le W610 n'est PAS en mode Modbus TCP↔RTU |

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

> **Simple version (YAML package)**: if you prefer an installation without a custom integration, see [Joyonway_control_home_assistant](https://github.com/gaet78/Joyonway_control_home_assistant)

### Features

- **Sensors**: Water temperature, setpoint, heat pump output temperature, operating mode, filtration schedules (2 slots)
- **Binary sensors**: Pump 1, Pump 2, Heating, Light status
- **Switches**: Pump 1, Pump 2, Light (on/off control)
- **Temperature setpoint**: Adjustable via service calls
- **Filtration schedule**: Configurable via service calls
- **UI config flow**: Add your spa from the HA interface, no YAML required

### Hardware Required

| Component | Details |
|-----------|---------|
| **Spa** | Joyonway with Balboa-like controller |
| **RS485/WiFi bridge** | [USR-W610](https://www.usr.cn/en/W610) or similar transparent TCP-to-RS485 bridge |
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
- **Option 1 (recommended)**: use the connector from a spare or faulty control panel — no cutting required, warranty preserved
- **Option 2**: if no heat pump, use the white **CN23** or **CN24** connector on the controller motherboard

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
| Filtration 1 | Schedule slot 1 (active/inactive + times in attributes) |
| Filtration 2 | Schedule slot 2 (active/inactive + times in attributes) |

#### Binary Sensors
| Entity | Description |
|--------|-------------|
| Pump 1 | Jet pump 1 status |
| Pump 2 | Jet pump 2 status |
| Heating | Heating active (heat pump and/or electric heater) |
| Light | Light status |

#### Switches (write to RS485 bus)
| Entity | Description |
|--------|-------------|
| Pump 1 | Toggle jet pump 1 |
| Pump 2 | Toggle jet pump 2 |
| Light | Toggle light |

### How it Works

The integration spoofs the physical control panel address (`0x20`) on the RS485 bus to send commands.

- **Reading**: connects to W610 TCP, captures 3 seconds of bus traffic, parses B4 (status) and B5 (filtration) broadcast frames
- **Writing**: floods the command frame every 50ms for 1-10 seconds (depending on command type)
- **Polling**: automatic refresh every 30 seconds

> **Response time**: commands (pumps, light, setpoint) take a few seconds before confirmation in HA. This is expected — the flood send takes 1-10 seconds, then the next read cycle (3 seconds) is needed to update the state.

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

For full protocol documentation, see the companion repository: [Joyonway_control_home_assistant — docs/protocol.md](https://github.com/gaet78/Joyonway_control_home_assistant/blob/main/docs/protocol.md)

### Compatibility

Tested with:
- Joyonway spa with **P69B133 3kW** control box ([product page](https://www.boospa.net/fr/boitier-de-controle-p69b133-3kw-joyonway.html)) with integrated heat pump
- USR-W610 RS485/WiFi bridge
- Home Assistant 2026.3+

This should work with other spas using the same Joyonway/Balboa proprietary protocol (0x7E delimiter, same frame structure). The protocol is **NOT** standard Balboa — it's a proprietary variant.

### Troubleshooting

| Problem | Solution |
|---------|----------|
| "Cannot connect" during setup | Check W610 IP/port, ensure it's powered and on your network |
| "No RS485 data" | Check RS485 wiring (A/B), W610 must be in **Transparent Mode**, 115200 baud |
| Temperature updates seem irregular | Normal — resolution is 1°F (~0.56°C), updates only on threshold change |
| Commands don't work | Verify W610 is NOT in Modbus TCP↔RTU mode |

### License

MIT

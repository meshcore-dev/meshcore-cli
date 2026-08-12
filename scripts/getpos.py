#!/usr/bin/python
# queries geoclue for current position of a linux device and print coordinates

import gi
gi.require_version('Geoclue', '2.0')
from gi.repository import Geoclue

# Initialisation du client Geoclue simple
clue = Geoclue.Simple.new_sync('mon-app-id', Geoclue.AccuracyLevel.EXACT, None)

# Récupération de l'objet de localisation (proxy D-Bus)
loc = clue.get_location()

# Extraction des propriétés réelles de l'objet
latitude = loc.get_property('latitude')
longitude = loc.get_property('longitude')
altitude = loc.get_property('altitude')

# Affichage des coordonnées numériques
print(f"{latitude},{longitude}")

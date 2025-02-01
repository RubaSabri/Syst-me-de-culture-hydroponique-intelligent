#include <Wire.h>                  
#include <BH1750.h>                
#include <Adafruit_NeoPixel.h>     
#include <ESP8266WiFi.h>           
#include <ESP8266mDNS.h>           

#ifndef STASSID
#define STASSID "Focusing on my mentale"        
#define STAPSK "Rubaswifi2003"     
#endif

const char* ssid = STASSID;
const char* password = STAPSK;

// Configuration des LEDs et du capteur
#define LED_PIN D4
#define NUM_LEDS 7
BH1750 lightMeter;
Adafruit_NeoPixel strip(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);

// Serveur web à l'adresse IP locale, port 80
WiFiServer server(80);
uint32_t currentColor = 0;  // Couleur par défaut (éteint)

void setup() {
  Serial.begin(115200);
  
  // Initialisation des LEDs
  strip.begin();
  strip.fill(strip.Color(0, 0, 0));
  strip.show();

  // Initialisation du capteur de luminosité
  Wire.begin();
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("Erreur de communication avec le capteur BH1750.");
    while (1);
  }
  Serial.println("Capteur de luminosité prêt !");
  
  // Connexion au réseau Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.println("\nConnexion au Wi-Fi...");
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nConnecté !");
  Serial.print("Adresse IP : ");
  Serial.println(WiFi.localIP());  // Affichage de l'adresse IP sur le moniteur série
  
  // Configuration du mDNS
  if (!MDNS.begin("esp8266")) {
    Serial.println("Erreur lors de la configuration du mDNS.");
    while (1);
  }
  
  server.begin();
  Serial.println("Serveur web démarré.");
}

void loop() {
  // Mise à jour mDNS
  MDNS.update();

  // Lecture de la luminosité ambiante
  float lux = lightMeter.readLightLevel();
  Serial.print("Luminosité : ");
  Serial.print(lux);
  Serial.println(" lux");

  // Vérification des connexions clients
  WiFiClient client = server.available();
  if (client) {
    Serial.println("Nouvelle requête client");
    while (client.connected() && !client.available()) {
      delay(1);
    }

    // Lecture de la requête HTTP
    String req = client.readStringUntil('\r');
    Serial.print("Requête : ");
    Serial.println(req);
    client.flush();

    // Sélection de l'intensité lumineuse des LEDs selon la requête
    if (req.indexOf("/setColor/A") != -1) {
      currentColor = strip.Color(255, 0, 0);  // Intensité maximale
      Serial.println("Mode A : LED Rouge 255");
    } else if (req.indexOf("/setColor/B") != -1) {
      currentColor = strip.Color(155, 0, 0);  // Intensité moyenne
      Serial.println("Mode B : LED Rouge 155");
    } else if (req.indexOf("/setColor/C") != -1) {
      currentColor = strip.Color(55, 0, 0);   // Intensité faible
      Serial.println("Mode C : LED Rouge 55");
    }

    // Application de la couleur aux LEDs
    if (lux < 100) {
      strip.fill(currentColor);
    } else {
      strip.fill(strip.Color(0, 0, 0)); // Éteindre si la luminosité est suffisante
      Serial.println("Luminosité suffisante, LEDs éteintes.");
    }
    strip.show();

    // Construction et envoi de la réponse HTML
    String s = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n<!DOCTYPE HTML>\r\n<html>";
    s += "<h1>Contrôle des LEDs</h1>";
    s += "<p>Luminosité actuelle : " + String(lux) + " lux</p>";
    s += "<p><a href=\"/setColor/A\">Choisir A (ROUGE 255)</a></p>";
    s += "<p><a href=\"/setColor/B\">Choisir B (ROUGE 155)</a></p>";
    s += "<p><a href=\"/setColor/C\">Choisir C (ROUGE 55)</a></p>";
    s += "</html>\r\n\r\n";
    
    client.print(s);
    Serial.println("Réponse envoyée au client");
  }
  delay(1000);  // Temporisation pour éviter des requêtes trop fréquentes
}

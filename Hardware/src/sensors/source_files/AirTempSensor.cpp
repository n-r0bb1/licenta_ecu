#include "../headers/AirTempSensor.h"
#include "../../config.h"
#include <DHT.h>

static DHT dht(PIN_DHT11, DHT_TYPE);
static float _temp = 0.0f;
static float _humidity = 0.0f;

void airtemp_begin() {
    dht.begin();
}

void airtemp_update() {
    static uint32_t _lastRead = 0;
    uint32_t now = millis();
    if (now - _lastRead < 2000) return;
    _lastRead = now;

    float t = dht.readTemperature();
    float h = dht.readHumidity();
    if (!isnan(t)) _temp = t;
    if (!isnan(h)) _humidity = h;
}

float airtemp_getTemp()     { return _temp; }
float airtemp_getHumidity() { return _humidity; }

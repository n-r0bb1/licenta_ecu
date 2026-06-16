#include "../headers/FuelSensor.h"
#include "../../config.h"

static float _percent = 0.0f;

void fuel_begin() {
    pinMode(PIN_FUEL_LEVEL, INPUT);
}

void fuel_update() {
    uint16_t raw = analogRead(PIN_FUEL_LEVEL);
    _percent = (raw / (ADC_RESOLUTION - 1)) * 100.0f;
}

float fuel_getPercent() { return _percent; }

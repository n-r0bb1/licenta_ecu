// ThrottleSensor.cpp
#include "../headers/ThrottleSensor.h"
#include "../../config.h"

static uint16_t _raw = 0;
static float _percent = 0.0f;

void throttle_begin() {
    pinMode(PIN_THROTTLE, INPUT);
}

void throttle_update() {
    _raw = analogRead(PIN_THROTTLE);
    _percent = (_raw / (ADC_RESOLUTION - 1)) * 100.0f;
}

uint16_t throttle_getRaw() { return _raw; }
float throttle_getPercent() { return _percent; }
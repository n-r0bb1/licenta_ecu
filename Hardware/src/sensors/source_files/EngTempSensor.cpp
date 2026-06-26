#include "../../config.h"
#include "../headers/EngTempSensor.h"

void engtemp_begin()
{
    pinMode(A3, INPUT);
}

float engtemp_getTemp()
{
    analogRead(PIN_ENGTEMP);   // Dummy read
    delayMicroseconds(10);

    int adcValue = analogRead(PIN_ENGTEMP);

    return adcValue * (480.0f / 1023.0f);
}
#include "../../config.h"
#include "../headers/EngTempSensor.h"


int engtemp_value;
float engtemp_voltage;
float engtemp_temperature;

void engtemp_begin()
{
    pinMode(PIN_ENGTEMP, INPUT);
}

float engtemp_getTemp()
{
    engtemp_value = analogRead(PIN_ENGTEMP);
    engtemp_voltage = engtemp_value * (5.0 / 1023.0);
    engtemp_temperature = engtemp_voltage * 100;

    return engtemp_temperature;
};
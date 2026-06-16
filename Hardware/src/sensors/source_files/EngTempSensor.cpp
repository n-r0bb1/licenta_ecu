#include "../../config.h"
#include "../headers/EngTempSensor.h"

void engtemp_begin()
{
    pinMode(PIN_ENGTEMP, INPUT);
}

float engtemp_getTemp()
{
    long sum = 0;
    for (int i = 0; i < 10; i++)
    {
        sum += analogRead(PIN_ENGTEMP);
        delay(10);
    }
    return (sum / 10.0) * (488.0 / 1023.0);
}
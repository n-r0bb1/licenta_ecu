#ifndef PRES_SENSOR_H
#define PRES_SENSOR_H

#include <Arduino.h>

bool pres_begin();
void pres_update();
float pres_getPressure();

#endif

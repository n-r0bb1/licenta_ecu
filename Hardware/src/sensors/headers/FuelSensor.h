#ifndef FUEL_SENSOR_H
#define FUEL_SENSOR_H

#include <Arduino.h>

void fuel_begin();
void fuel_update();
float fuel_getPercent();

#endif

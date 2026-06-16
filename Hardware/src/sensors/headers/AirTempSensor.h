#ifndef AIRTEMP_SENSOR_H
#define AIRTEMP_SENSOR_H

#include <Arduino.h>

void airtemp_begin();
void airtemp_update();
float airtemp_getTemp();
float airtemp_getHumidity();

#endif

// ThrottleSensor.h
#ifndef THROTTLE_SENSOR_H
#define THROTTLE_SENSOR_H

#include <Arduino.h>

void throttle_begin();
void throttle_update();
uint16_t throttle_getRaw();
float throttle_getPercent();

#endif
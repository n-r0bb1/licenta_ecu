#ifndef PACKET_BUILDER_H
#define PACKET_BUILDER_H

#include <Arduino.h>

typedef struct {
    float throttle_pct;
    float fuel_pct;
    float eng_temp;
    float air_temp;
    float humidity;
} SensorPacket;

void packet_send(const SensorPacket& pkt);

#endif

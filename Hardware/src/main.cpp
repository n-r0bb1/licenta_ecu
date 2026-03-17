#include <Arduino.h>
#include "config.h"

#include "sensors/headers/ThrottleSensor.h"
#include "sensors/headers/FuelSensor.h"
#include "sensors/headers/EngTempSensor.h"
#include "sensors/headers/AirTempSensor.h"
#include "sensors/headers/PresSensor.h"
#include "serial/PacketBuilder.h"

static uint32_t _lastSample = 0;

void setup() {
    Serial.begin(BAUD_RATE);

    throttle_begin();
    // fuel_begin();
    engtemp_begin();
    // airtemp_begin();
    // pres_begin();

    Serial.println("ECU Online");
}

void loop() {
    uint32_t now = millis();

    if (now - _lastSample >= SAMPLE_INTERVAL) {
        _lastSample = now;

        throttle_update();
        // fuel_update();
        // engtemp_update();
        // airtemp_update();
        // pres_update();

        SensorPacket pkt;
        pkt.throttle_pct = throttle_getPercent();
        //pkt.fuel_pct     = fuel_getPercent();
        //pkt.eng_temp     = engtemp_getcelsius();
        pkt.air_temp      = engtemp_getTemp();
        //pkt.pressure     = pres_gethpa();

        packet_send(pkt);
    }
}
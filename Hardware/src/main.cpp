#include <Arduino.h>
#include "config.h"

#include "sensors/headers/ThrottleSensor.h"
#include "sensors/headers/FuelSensor.h"
#include "sensors/headers/EngTempSensor.h"
#include "sensors/headers/AirTempSensor.h"
#include "serial/PacketBuilder.h"

static uint32_t _lastSerial = 0;

void setup() {
    Serial.begin(BAUD_RATE);

    throttle_begin();
    fuel_begin();
    engtemp_begin();
    airtemp_begin();

    delay(2000);
    Serial.println("ECU Online");
}

void loop() {
    uint32_t now = millis();

    if (now - _lastSerial >= SAMPLE_INTERVAL) {
        _lastSerial = now;

        throttle_update();
        fuel_update();
        airtemp_update();

        SensorPacket pkt;
        pkt.throttle_pct = throttle_getPercent();
        pkt.fuel_pct     = fuel_getPercent();
        pkt.eng_temp     = engtemp_getTemp();
        pkt.air_temp     = airtemp_getTemp();
        pkt.humidity     = airtemp_getHumidity();

        packet_send(pkt);
    }
}

#include "PacketBuilder.h"

void packet_send(const SensorPacket& pkt) {
    Serial.print("THR:");   Serial.print(pkt.throttle_pct, 1);
    Serial.print(",FUEL:"); Serial.print(pkt.fuel_pct, 1);
    Serial.print(",ENGT:"); Serial.print(pkt.eng_temp, 1);
    Serial.print(",AIRT:"); Serial.print(pkt.air_temp, 1);
    Serial.print(",HUM:");  Serial.println(pkt.humidity, 1);
}

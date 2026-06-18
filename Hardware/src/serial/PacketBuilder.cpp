#include "PacketBuilder.h"

static char _buf[96];

static uint8_t xor_checksum(const char *s, uint8_t len) {
    uint8_t cs = 0;
    for (uint8_t i = 0; i < len; i++) cs ^= s[i];
    return cs;
}

void packet_send(const SensorPacket& pkt) {
    int n = snprintf(_buf, sizeof(_buf),
        "THR:%.1f,FUEL:%.1f,ENGT:%.1f,AIRT:%.1f,PRES:%.1f",
        (double)pkt.throttle_pct,
        (double)pkt.fuel_pct,
        (double)pkt.eng_temp,
        (double)pkt.air_temp,
        (double)pkt.pressure);

    uint8_t cs = xor_checksum(_buf, n);

    Serial.print('$');
    Serial.print(_buf);
    Serial.print('*');
    if (cs < 0x10) Serial.print('0');
    Serial.println(cs, HEX);
}

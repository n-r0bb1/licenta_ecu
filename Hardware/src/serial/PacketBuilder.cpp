#include "PacketBuilder.h"

static uint8_t xor_checksum(const char *s, uint8_t len) {
    uint8_t cs = 0;
    for (uint8_t i = 0; i < len; i++) cs ^= s[i];
    return cs;
}

static void appendFloat(char *buf, uint8_t &pos, uint8_t maxLen, float val) {
    int whole = (int)val;
    int frac  = (int)((val - whole) * 10 + 0.5f);
    if (frac >= 10) { whole++; frac = 0; }

    int n = snprintf(buf + pos, maxLen - pos, "%d.%d", whole, frac);
    if (n > 0) pos += n;
}

void packet_send(const SensorPacket& pkt) {
    char buf[96];
    uint8_t pos = 0;

    const char *keys[] = {"THR:", "FUEL:", "ENGT:", "AIRT:", "PRES:"};
    float vals[] = {
        pkt.throttle_pct, pkt.fuel_pct,
        pkt.eng_temp, pkt.air_temp, pkt.pressure
    };

    for (uint8_t i = 0; i < 5; i++) {
        if (i > 0) buf[pos++] = ',';
        uint8_t klen = strlen(keys[i]);
        memcpy(buf + pos, keys[i], klen);
        pos += klen;
        appendFloat(buf, pos, sizeof(buf), vals[i]);
    }
    buf[pos] = '\0';

    uint8_t cs = xor_checksum(buf, pos);

    Serial.print('$');
    Serial.print(buf);
    Serial.print('*');
    if (cs < 0x10) Serial.print('0');
    Serial.println(cs, HEX);
}

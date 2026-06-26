#include "../headers/PresSensor.h"
#include <Wire.h>
#include <Adafruit_BMP280.h>

static Adafruit_BMP280 bmp;
static float _pressure = 0.0f;
static bool _ready = false;

constexpr float PA_TO_BAR = 1.0f / 100000.0f;

bool pres_begin()
{
    _ready = bmp.begin(BMP280_ADDRESS_ALT);

    if (_ready)
    {
        bmp.setSampling(
            Adafruit_BMP280::MODE_NORMAL,
            Adafruit_BMP280::SAMPLING_X2,
            Adafruit_BMP280::SAMPLING_X16,
            Adafruit_BMP280::FILTER_X4,
            Adafruit_BMP280::STANDBY_MS_500);
    }

    return _ready;
}

void pres_update()
{
    if (!_ready)
        return;

    _pressure = bmp.readPressure() * PA_TO_BAR;
}

float pres_getPressure()
{
    return _pressure;
}
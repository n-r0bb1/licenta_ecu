#ifndef CONFIG_H
#define CONFIG_H

// Serial
#define BAUD_RATE        9600
#define SAMPLE_INTERVAL  100    

// Analog Pins
#define PIN_ENGTEMP      A0
#define PIN_FUEL_LEVEL   A1
#define PIN_THROTTLE     A2

// Digital Pins
#define PIN_DHT11        7
#define PIN_SW420        8

// DHT Type
#define DHT_TYPE         DHT11

// LM35 calibration
#define AREF_VOLTAGE     5.0
#define ADC_RESOLUTION   1024.0

#endif
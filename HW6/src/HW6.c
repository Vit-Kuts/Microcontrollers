#include "HW6.h"

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "main.h"
#include "usbd_cdc_if.h"


typedef struct {
  uint32_t adc_value;
  uint8_t ready_flag;
  uint8_t state;
} HW6;

HW6 HW6_Data;

#define HIGH_THRESHOLD 3447
#define LOW_THRESHOLD 2068
#define HYSTERESIS 100

void HW6_Init() {
  HW6_Data.adc_value = 0;
  HW6_Data.ready_flag = 0;
  HW6_Data.state = 0;
}

void HW6_Handler() {
  static uint8_t last_state = 0xFF;

  if (HW6_Data.ready_flag) {
    if (HW6_Data.adc_value > HIGH_THRESHOLD) {
      HW6_Data.state = 0;
      HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
    } else if (HW6_Data.adc_value < (LOW_THRESHOLD - HYSTERESIS)) {
      HW6_Data.state = 1;
      HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
    }

    if (last_state != HW6_Data.state) {
      char usb_tx_buffer[80];
      int len = snprintf(usb_tx_buffer, sizeof(usb_tx_buffer),
                         "adc_val = %u level = %s state = %s\n",
                         (unsigned int)HW6_Data.adc_value,
                         (HW6_Data.state == 1) ? "LOW" : "HIGH",
                         (HW6_Data.state == 1) ? "LED ON" : "LED OFF");
      if (len > 0) {
        CDC_Transmit_FS((uint8_t *)usb_tx_buffer, len);
      }
      last_state = HW6_Data.state;
    }

    HW6_Data.ready_flag = 0;
    HW6_Data.adc_value = 0;
  }
}

void HAL_ADC_LevelOutOfWindowCallback(ADC_HandleTypeDef *hadc) {
  if (hadc->Instance != ADC1) return;
  HW6_Data.adc_value = HAL_ADC_GetValue(hadc);
  HW6_Data.ready_flag = 1;
}
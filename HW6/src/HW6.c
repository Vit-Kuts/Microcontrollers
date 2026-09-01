#include <stdint.h>
#include "main.h"

uint32_t adc_value = 0;

#define HIGH_THRESHOLD 3447
#define LOW_THRESHOLD 2068

void HAL_ADC_LevelOutOfWindowCallback(ADC_HandleTypeDef *hadc) {
  if (hadc->Instance != ADC1) return;
  // HAL_ADC_Stop_IT(hadc);
  adc_value = HAL_ADC_GetValue(hadc);
  if (adc_value > HIGH_THRESHOLD) {
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
  } else if (adc_value < LOW_THRESHOLD) {
    HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
  }
}
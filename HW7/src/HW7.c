#include "HW7.h"

#include <string.h>

#include "main.h"
#include "usbd_cdc_if.h"

volatile uint32_t adc_value = 0;
extern TIM_HandleTypeDef htim4;
extern ADC_HandleTypeDef hadc1;

void HW7_Handler() {
  HAL_ADC_Start(&hadc1);

  if (HAL_ADC_PollForConversion(&hadc1, 100) == HAL_OK) {
    adc_value = HAL_ADC_GetValue(&hadc1);
  }

  uint32_t pwm_value = 0;
  if (adc_value <= 200) {
    pwm_value = 0;
  } else if (adc_value >= 250) {
    pwm_value = (adc_value * 1000) / 4096;
  }
  
  __HAL_TIM_SET_COMPARE(&htim4, TIM_CHANNEL_2, pwm_value);

  char rx_buff[80];
  int len = snprintf(rx_buff, sizeof(rx_buff), "ADC: %lu, PWM: %lu\n",
                     adc_value, pwm_value);
  CDC_Transmit_FS((uint8_t *)rx_buff, len);

  HAL_Delay(50);
}
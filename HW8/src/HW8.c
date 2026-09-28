#include "HW8.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

#include "fatfs.h"
#include "main.h"
#include "usb_device.h"


/* Внешние объекты из main.c / CubeMX */
extern TIM_HandleTypeDef htim4;
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim2;
extern DMA_HandleTypeDef hdma_adc1;
extern FATFS USERFatFS; /* Метаданные тома. CubeMX создаёт автоматический. Сюда
                        Добавил для налядности.*/
extern char USERPath[4]; /* Имя логического диска. CubeMX создаёт
                         автоматический. Сюда добавил для налядности. */
extern FIL USERFile; /* Дескриптор открытого файла. CubeMX создаёт
                     автоматический. Сюда добавил для налядности. В эту
                     структуру помещается файл для работы с ним функций
                     (f_open, f_read, f_close). при закрытии файла, структура
                     освобождается и доступна для открытия другого файла */

static uint16_t pwm_duty_buffer[BUFFER_SIZE];
static uint16_t hw8_adc_buf[HW8_SAMPLES];
static HW8_state hw8_state = DMA_BUSY;

/* -------------------- Вспомогательные -------------------- */

static uint32_t HW8_AdcToMv(uint16_t adc) {
  return ((uint32_t)adc * 3300U) / 4095U;
}

static void Fill_Sine_Buffer(void) {
  for (int i = 0; i < BUFFER_SIZE; i++) {
    float phase = 2.0f * (float)M_PI * (float)i / (float)BUFFER_SIZE;
    float value = (float)OFFSET + (float)AMPLITUDE * sinf(phase);

    if (value < 0.0f) value = 0.0f;
    if (value > 999.0f) value = 999.0f;

    pwm_duty_buffer[i] = (uint16_t)(value + 0.5f);
  }
}

static void PWM_Init(void) {
  Fill_Sine_Buffer();
  HAL_TIM_PWM_Start_DMA(&htim4, TIM_CHANNEL_2, (uint32_t *)pwm_duty_buffer,
                        BUFFER_SIZE);
}

/* -------------------- Инициализация -------------------- */

void HW8_Init(void) {
  FRESULT fr;
  BYTE work[_MAX_SS];

  PWM_Init();

  /* Монтирование диска */
  fr = f_mount(&USERFatFS, USERPath, 1);

  if (fr == FR_NO_FILESYSTEM) {
    /* Файловой системы нет — создаём */
    fr = f_mkfs(USERPath, FM_FAT, 0, work, sizeof(work));

    /* Перемонтируем, чтобы FatFs «увидел» новую файловую систему */
    f_mount(NULL, USERPath, 0);
    fr = f_mount(&USERFatFS, USERPath, 1);
  }

  /* Запуск сбора данных */
  HAL_TIM_Base_Start(&htim2);
  HAL_ADC_Start_DMA(&hadc1, (uint32_t *)hw8_adc_buf, HW8_SAMPLES);
}

/* -------------------- Основной обработчик -------------------- */

void HW8_Handler(void) {
  /* ждём, пока DMA соберёт HW8_SAMPLES измерений */
  if (hw8_state == DMA_BUSY) {
    /* HAL_ADC_ConvCpltCallback выставляет hw8_state = DMA_READY (см. ниже) */
    return;
  }

  /* данные собраны — останавливаем ADC и TIM, пишем CSV */
  if (hw8_state == DMA_READY) {
    HAL_ADC_Stop_DMA(&hadc1);
    HAL_TIM_Base_Stop(&htim2);

    FRESULT fr = f_open(&USERFile, "LOG.csv", FA_CREATE_ALWAYS | FA_WRITE);
    if (fr != FR_OK) {
      hw8_state = HW8_ERR;
      return;
    }

    UINT bytes_written;
    char line[32];

    /* Заголовок */
    f_write(&USERFile, "N;mV\r\n", 6, &bytes_written);
    for (int i = 0; i < HW8_SAMPLES; i++) {
      int len = snprintf(line, sizeof(line), "%d;%lu\r\n", i + 1,
                         (unsigned long)HW8_AdcToMv(hw8_adc_buf[i]));
      f_write(&USERFile, line, len, &bytes_written);
    }

    f_close(&USERFile);

    /* Перемонтируем, чтобы FatFs «увидел» все изменения */
    f_mount(NULL, USERPath, 0);
    f_mount(&USERFatFS, USERPath, 1);

    hw8_state = CSV_READY;
    return;
  }

  /* CSV записан — инициализируем USB MSC */
  if (hw8_state == CSV_READY) {
    MX_USB_DEVICE_Init();
    hw8_state = HW8_ERR;  // больше ничего не делаем
    return;
  }
}

/* -------------------- Колбэк DMA -------------------- */

// Этот колбэк вызывается HAL, когда DMA завершит передачу
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc) {
  if (hadc->Instance == ADC1) {
    if (hw8_state == DMA_BUSY) {
      hw8_state = DMA_READY;
    }
  }
}

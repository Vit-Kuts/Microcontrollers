#include "HW8.h"
#include "main.h"
#include "fatfs.h"
#include "usb_device.h"
#include "RAMDISK.h"
#include <stdio.h>
#include <string.h>

/* Внешние объекты из main.c / CubeMX */
extern ADC_HandleTypeDef hadc1;
extern TIM_HandleTypeDef htim2;
extern DMA_HandleTypeDef hdma_adc1;
extern FATFS USERFatFS;
extern char  USERPath[4];
extern FIL   USERFile;

/* Буфер для DMA-измерений */
static uint16_t hw8_adc_buf[HW8_SAMPLES];

/* Флаг: этап работы */
static uint8_t hw8_stage = 0;   // 0 = ожидание, 1 = данные собраны, 2 = CSV записан

/* -------------------- Вспомогательные -------------------- */

/* Перевод кода АЦП (12 бит) в милливольты при Vref = 3300 мВ */
static uint32_t HW8_AdcToMv(uint16_t adc)
{
    return ((uint32_t)adc * 3300U) / 4095U;
}

/* -------------------- Инициализация -------------------- */

void HW8_Init(void)
{
    FRESULT fr;
    BYTE work[_MAX_SS];

    /* ============================================================
     * ЭТАП 1: Монтирование диска
     * ============================================================ */
    fr = f_mount(&USERFatFS, USERPath, 1);

    if (fr == FR_OK) {
        /* Диск уже отформатирован — мигаем 2 раза и идём дальше */
        for (int i = 0; i < 2; i++) {
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
            HAL_Delay(100);
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
            HAL_Delay(100);
        }
    }
    else if (fr == FR_NO_FILESYSTEM) {
        /* ============================================================
         * ЭТАП 2: Файловой системы нет — создаём
         * ============================================================ */

        /* Пытаемся отформатировать. Пробуем FM_FAT (FAT16),
         * если не сработает — попробуем FM_FAT12 */
        fr = f_mkfs(USERPath, FM_FAT, 0, work, sizeof(work));

        if (fr != FR_OK) {
            /* Если FM_FAT не сработал — пробуем FM_FAT12 */
            fr = f_mkfs(USERPath, FM_FAT, 0, work, sizeof(work));
        }

        if (fr != FR_OK) {
            /* ============================================================
             * ОШИБКА ФОРМАТИРОВАНИЯ — мигаем кодом ошибки
             * ============================================================ */
            HAL_Delay(1000);
            for (int i = 0; i < fr; i++) {
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
                HAL_Delay(300);
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
                HAL_Delay(300);
            }
            HAL_Delay(2000);

            /* Останавливаемся — дальше работать нет смысла */
            while (1) {
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
                HAL_Delay(100);
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
                HAL_Delay(100);
            }
        }

        /* Форматирование успешно — мигаем 3 раза */
        for (int i = 0; i < 3; i++) {
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
            HAL_Delay(100);
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
            HAL_Delay(100);
        }

        /* Перемонтируем, чтобы FatFs «увидел» новую файловую систему */
        f_mount(NULL, USERPath, 0);
        fr = f_mount(&USERFatFS, USERPath, 1);

        if (fr != FR_OK) {
            /* Не удалось смонтировать после форматирования */
            for (int i = 0; i < 20; i++) {
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
                HAL_Delay(50);
                HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
                HAL_Delay(50);
            }
            while (1);
        }
    }
    else {
        /* ============================================================
         * ДРУГАЯ ОШИБКА МОНТИРОВАНИЯ — мигаем кодом
         * ============================================================ */
        HAL_Delay(1000);
        for (int i = 0; i < fr; i++) {
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_SET);
            HAL_Delay(300);
            HAL_GPIO_WritePin(GPIOD, GPIO_PIN_13, GPIO_PIN_RESET);
            HAL_Delay(300);
        }
        HAL_Delay(2000);
        while (1);
    }

    /* ============================================================
     * ЭТАП 3: Запуск сбора данных
     * ============================================================ */
    HAL_TIM_Base_Start(&htim2);
    HAL_ADC_Start_DMA(&hadc1, (uint32_t*)hw8_adc_buf, HW8_SAMPLES);
}

/* -------------------- Основной обработчик -------------------- */

void HW8_Handler(void)
{
    /* Этап 1: ждём, пока DMA соберёт 100 измерений */
    if (hw8_stage == 0) {
        /* HAL_ADC_ConvCpltCallback выставляет hw8_stage = 1 (см. ниже) */
        return;
    }

    /* Этап 2: данные собраны — останавливаем ADC и TIM, пишем CSV */
    if (hw8_stage == 1) {
        /* Останавливаем АЦП и таймер */
        HAL_ADC_Stop_DMA(&hadc1);
        HAL_TIM_Base_Stop(&htim2);

        /* Открываем / создаём CSV-файл */
        FRESULT fr = f_open(&USERFile, "LOG.csv", FA_CREATE_ALWAYS | FA_WRITE);
        if (fr != FR_OK) {
            hw8_stage = 3;   // ошибка
            return;
        }

        UINT bw;
        char line[32];

        /* Заголовок */
f_write(&USERFile, "N;ADC;mV\r\n", 10, &bw);
for (int i = 0; i < HW8_SAMPLES; i++) {
    int len = snprintf(line, sizeof(line), "%d;%u;%lu\r\n",
                       i + 1, (unsigned)hw8_adc_buf[i],
                       (unsigned long)HW8_AdcToMv(hw8_adc_buf[i]));
    f_write(&USERFile, line, len, &bw);
}


        f_close(&USERFile);

        /* Перемонтируем, чтобы FatFs «увидел» все изменения */
        f_mount(NULL, USERPath, 0);
        f_mount(&USERFatFS, USERPath, 1);

        hw8_stage = 2;
        return;
    }

    /* Этап 3: CSV записан — инициализируем USB MSC */
    if (hw8_stage == 2) {
        MX_USB_DEVICE_Init();
        hw8_stage = 3;   // больше ничего не делаем
        return;
    }

    /* hw8_stage == 3 — простаиваем */
}

/* -------------------- Колбэк DMA -------------------- */

/*
 * Этот колбэк вызывается HAL, когда DMA завершит передачу
 * HW8_SAMPLES значений из ADC в hw8_adc_buf.
 * Добавьте его в main.c (или в соответствующее место),
 * если он ещё не определён.
 */
void HAL_ADC_ConvCpltCallback(ADC_HandleTypeDef *hadc)
{
    if (hadc->Instance == ADC1) {
        if (hw8_stage == 0) {
            hw8_stage = 1;
        }
    }
}

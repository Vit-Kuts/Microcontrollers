#ifndef __HW8_H
#define __HW8_H

#include <stdint.h>
#include "ff.h"

/* Количество измерений */
#define HW8_SAMPLES 100

/* Функции */
void HW8_Init(void);        // Инициализация: монтирование FatFs
void HW8_Handler(void);     // Основной обработчик (вызывать в while)

#endif /* __HW8_H */
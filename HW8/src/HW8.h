#ifndef __HW8_H
#define __HW8_H

#include <stdint.h>
#include "ff.h"

  #define HW8_SAMPLES 3000
  #define BUFFER_SIZE 100
  #define ARR_VALUE   999
  #define AMPLITUDE   427   
  #define OFFSET      500
typedef enum {DMA_BUSY, DMA_READY, CSV_READY, HW8_ERR} HW8_state;

/* Функции */
void HW8_Init(void);        
void HW8_Handler(void);     

#endif /* __HW8_H */
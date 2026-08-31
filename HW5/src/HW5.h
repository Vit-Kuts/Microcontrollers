#ifndef __HW5_H
#define __HW5_H
#include <stdint.h>

#define RX_BUF_SIZE 2048
#define MAX_CMD_SIZE 8
#define MAX_ADDR_SIZE 12
#define MAX_WORD_SYMBOL_COUNT 4
#define MAX_WORD_COUNT 256

#define LIMIT_CMD     7
#define LIMIT_ADDR    11
#define LIMIT_SYMBOL_COUNT 3

#define STR_HELPER(x) #x
#define TO_STR(x) STR_HELPER(x)

typedef struct HW5_Struct
{
  uint8_t rx_flag;
  uint8_t busy_flag;
  uint8_t rx_buf[RX_BUF_SIZE];
  char command [MAX_CMD_SIZE];
  char addr [MAX_ADDR_SIZE];
  char word_count [MAX_WORD_SYMBOL_COUNT];
} HW5_Struct;

typedef enum {HW5_ERR, HW5_OK, HW5_BYSY} HW5_status;

HW5_status HW5_Init ();
HW5_Struct HW5_GetHW5_Data();
HW5_status HW5_IntelHexParse (uint8_t *buf, uint32_t len);
void HW5_Handler();

#endif /* __HW5_H */